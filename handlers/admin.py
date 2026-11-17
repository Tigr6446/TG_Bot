from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, BufferedInputFile, InlineKeyboardButton
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

from database import AsyncSessionLocal
from models import Question, User, GameResult, QuizResult, Feedback, AmbassadorApplication, UserActivity, BotSettings
from config import ADMIN_IDS
from sqlalchemy import select, func
from datetime import datetime, timedelta
from services.analytics import log_activity
from keyboards.admin_kb import get_admin_help_kb

import csv, io, zipfile, html, asyncio

router = Router()

def is_admin(message: Message) -> bool:
    return message.from_user.id in ADMIN_IDS

def is_admin_cb(callback: CallbackQuery) -> bool:
    return callback.from_user.id in ADMIN_IDS

# ---------- ОТВЕТ НА ВОПРОС ----------
@router.message(Command("reply"), F.func(is_admin))
async def reply_to_question(message: Message, command: CommandObject, bot: Bot):
    if not command.args:
        await message.reply("❌ Формат: /reply <ID_вопроса> <текст ответа>")
        return
    
    try:
        parts = command.args.split(' ', 1)
        question_id = int(parts[0])
        answer_text = parts[1] if len(parts) > 1 else ""
        if not answer_text:
            await message.reply("❌ Текст ответа не может быть пустым")
            return
    except ValueError:
        await message.reply("❌ Неверный формат ID вопроса")
        return
    
    async with AsyncSessionLocal() as session:
        stmt = select(Question).where(Question.id == question_id)
        result = await session.execute(stmt)
        question = result.scalar_one_or_none()
        
        if not question:
            await message.reply(f"❌ Вопрос #{question_id} не найден")
            return
        if question.status == 'answered':
            await message.reply(f"⚠️ На вопрос #{question_id} уже дан ответ")
            return
        
        try:
            await bot.send_message(
                question.user_id,
                f"📩 **На ваш вопрос эксперт ответил:**\n\n{answer_text}\n\nЕсли остались вопросы, задайте новый.",
                parse_mode="Markdown"
            )
            question.status = 'answered'
            question.answer = answer_text
            question.answered_at = datetime.utcnow()
            await session.commit()
            await message.reply(f"✅ Ответ отправлен пользователю {question.user_name}")
        except Exception as e:
            await message.reply(f"❌ Ошибка отправки: {str(e)}")

# ---------- ВЫГРУЗКА FEEDBACK ----------
@router.message(Command("export_feedback"))
async def export_feedback(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("❌ Недостаточно прав")
        return
    
    async with AsyncSessionLocal() as session:
        stmt = select(Feedback).order_by(Feedback.created_at.desc())
        result = await session.execute(stmt)
        feedbacks = result.scalars().all()
    
    if not feedbacks:
        await message.answer("📭 Нет данных для выгрузки")
        return
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["id", "user_id", "sdg_id", "usefulness", "interest", "clarity", "created_at"])
    for f in feedbacks:
        writer.writerow([f.id, f.user_id, f.sdg_id, f.usefulness, f.interest, f.clarity, f.created_at])
    
    file = BufferedInputFile(output.getvalue().encode('utf-8-sig'), filename="feedback.csv")
    await message.answer_document(file, caption="📊 Выгрузка обратной связи")

# ---------- ЗАЯВКИ ПОСЛАННИКОВ ----------
@router.message(Command("approve"), F.func(is_admin))
async def approve_ambassador(message: Message, command: CommandObject, bot: Bot):
    if not command.args:
        await message.reply("❌ Формат: /approve <ID_заявки>")
        return
    try:
        application_id = int(command.args.strip())
    except ValueError:
        await message.reply("❌ Неверный формат ID заявки")
        return
    
    async with AsyncSessionLocal() as session:
        stmt = select(AmbassadorApplication).where(AmbassadorApplication.id == application_id)
        result = await session.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            await message.reply(f"❌ Заявка #{application_id} не найдена")
            return
        if application.status != 'pending':
            await message.reply(f"⚠️ Заявка #{application_id} уже обработана")
            return
        
        application.status = 'approved'
        application.reviewed_at = datetime.utcnow()
        await session.commit()
        
        try:
            await bot.send_message(
                application.user_id,
                f"🎉 **Поздравляем! Ваша заявка на статус посланника ЦУР одобрена!**\n\n"
                f"Роль: *{application.role}*\n\nМы свяжемся с вами для дальнейших инструкций. 🌍",
                parse_mode="Markdown"
            )
            await message.reply(f"✅ Заявка #{application_id} одобрена. Пользователь уведомлён.")
        except Exception as e:
            await message.reply(f"⚠️ Заявка одобрена, но не удалось уведомить: {str(e)}")

@router.message(Command("reject"), F.func(is_admin))
async def reject_ambassador(message: Message, command: CommandObject, bot: Bot):
    if not command.args:
        await message.reply("❌ Формат: /reject <ID_заявки> [причина]")
        return
    parts = command.args.split(' ', 1)
    try:
        application_id = int(parts[0])
        reason = parts[1] if len(parts) > 1 else "Не указана"
    except ValueError:
        await message.reply("❌ Неверный формат ID заявки")
        return
    
    async with AsyncSessionLocal() as session:
        stmt = select(AmbassadorApplication).where(AmbassadorApplication.id == application_id)
        result = await session.execute(stmt)
        application = result.scalar_one_or_none()
        if not application:
            await message.reply(f"❌ Заявка #{application_id} не найдена")
            return
        if application.status != 'pending':
            await message.reply(f"⚠️ Заявка #{application_id} уже обработана")
            return
        
        application.status = 'rejected'
        application.reviewed_at = datetime.utcnow()
        await session.commit()
        
        try:
            await bot.send_message(
                application.user_id,
                f"📩 **Ваша заявка на статус посланника ЦУР отклонена.**\nПричина: *{reason}*\n\nВы можете попробовать снова позже.",
                parse_mode="Markdown"
            )
            await message.reply(f"✅ Заявка #{application_id} отклонена.")
        except Exception as e:
            await message.reply(f"⚠️ Заявка отклонена, но не удалось уведомить: {str(e)}")

@router.message(Command("applications"), F.func(is_admin))
async def list_applications(message: Message):
    async with AsyncSessionLocal() as session:
        stmt = select(AmbassadorApplication).order_by(AmbassadorApplication.created_at.desc()).limit(10)
        result = await session.execute(stmt)
        apps = result.scalars().all()
    
    if not apps:
        await message.answer("📭 Нет заявок.")
        return
    
    text = "📋 **Последние заявки посланников:**\n\n"
    for app in apps:
        status_emoji = "⏳" if app.status == "pending" else "✅" if app.status == "approved" else "❌"
        text += f"{status_emoji} **#{app.id}** | {app.full_name} | {app.role}\n   Статус: {app.status}\n\n"
    text += "Для одобрения: `/approve <ID>`\nДля отклонения: `/reject <ID> [причина]`"
    await message.answer(text, parse_mode="Markdown")

# ---------- СТАТИСТИКА АКТИВНОСТИ ----------
@router.message(Command("stats_activity"), F.func(is_admin))
async def stats_activity(message: Message):
    async with AsyncSessionLocal() as session:
        today = datetime.utcnow().date()
        stmt = select(func.count()).where(func.date(UserActivity.created_at) == today)
        today_activity = await session.scalar(stmt) or 0
        
        week_ago = datetime.utcnow() - timedelta(days=7)
        stmt = select(UserActivity.action, func.count()).where(
            UserActivity.created_at >= week_ago
        ).group_by(UserActivity.action)
        result = await session.execute(stmt)
        actions = result.all()
        
        translate = {
            'game': '🎮 Игры',
            'viewsdg': '📚 Просмотры ЦУР',
            'view_sdg': '📚 Просмотры ЦУР',
            'quiz': '📝 Квизы',
        }
        
        text = f"📊 **Активность за сегодня:** {today_activity}\n\n**За неделю:**\n"
        if actions:
            for action, count in actions:
                ru_action = translate.get(action, action)
                text += f"• {ru_action}: {count}\n"
        else:
            text += "Нет данных\n"
        
        await message.answer(text, parse_mode="Markdown")

# ---------- ПОПУЛЯРНОСТЬ ИГР ----------
@router.message(Command("stats_games_popular"), F.func(is_admin))
async def stats_games_popular(message: Message):
    async with AsyncSessionLocal() as session:
        stmt = select(UserActivity.details, func.count()).where(UserActivity.action == 'game').group_by(UserActivity.details).order_by(func.count().desc())
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            await message.answer("📭 Нет данных об играх.")
            return
        
        text = "🎮 **Популярность игр:**\n\n"
        for details, count in rows:
            text += f"• {details}: {count} запусков\n"
        
        await message.answer(text, parse_mode="Markdown")

# ---------- ПОПУЛЯРНЫЕ ЦУР ----------
@router.message(Command("stats_popular"), F.func(is_admin))
async def stats_popular(message: Message):
    async with AsyncSessionLocal() as session:
        stmt = select(UserActivity.target_id, func.count()).where(UserActivity.action == 'view_sdg').group_by(UserActivity.target_id).order_by(func.count().desc()).limit(5)
        result = await session.execute(stmt)
        rows = result.all()
        
        if not rows:
            await message.answer("📭 Нет данных о просмотрах ЦУР")
            return
        
        text = "🏆 **Топ-5 популярных ЦУР:**\n\n"
        for target_id, count in rows:
            text += f"ЦУР {target_id}: {count} просмотров\n"
        await message.answer(text, parse_mode="Markdown")

# ---------- ОБРАБОТЧИКИ КНОПОК ИЗ /help ----------
@router.callback_query(F.data == "admin_export_feedback", F.func(is_admin_cb))
async def cb_export_feedback(callback: CallbackQuery):
    await callback.message.edit_text("⏳ Готовлю файл отзывов...")
    async with AsyncSessionLocal() as session:
        stmt = select(Feedback).order_by(Feedback.created_at.desc())
        result = await session.execute(stmt)
        feedbacks = result.scalars().all()
    
    if not feedbacks:
        await callback.message.edit_text("📭 Нет данных для выгрузки", reply_markup=get_admin_help_kb())
        return
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';')
    writer.writerow(["id", "user_id", "sdg_id", "usefulness", "interest", "clarity", "comment", "created_at"])
    for f in feedbacks:
        writer.writerow([f.id, f.user_id, f.sdg_id, f.usefulness, f.interest, f.clarity, f.comment, f.created_at])
    
    file = BufferedInputFile(output.getvalue().encode('utf-8-sig'), filename="feedback.csv")
    await callback.message.answer_document(file, caption="📊 Выгрузка обратной связи готова!")
    await callback.message.edit_text("✅ Файл отправлен выше.", reply_markup=get_admin_help_kb())
    await callback.answer()

@router.callback_query(F.data == "admin_export_db", F.func(is_admin_cb))
async def cb_export_db(callback: CallbackQuery):
    await callback.message.edit_text("⏳ Собираю базу данных в ZIP-архив...")
    zip_buffer = io.BytesIO()
    tables = [(User, "users"), (Question, "questions"), (QuizResult, "quiz_results"), (GameResult, "game_results"), (AmbassadorApplication, "ambassadors"), (Feedback, "feedback"), (UserActivity, "user_activity")]
    
    async with AsyncSessionLocal() as session:
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for model, filename in tables:
                stmt = select(model)
                result = await session.execute(stmt)
                rows = result.scalars().all()
                if not rows: continue
                
                columns = [c.name for c in model.__table__.columns]
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer, delimiter=';')
                writer.writerow(columns)
                
                for row in rows:
                    row_data = [getattr(row, col) for col in columns]
                    writer.writerow(row_data)
                
                zip_file.writestr(f"{filename}.csv", csv_buffer.getvalue().encode('utf-8-sig'))
    
    zip_buffer.seek(0)
    file = BufferedInputFile(zip_buffer.read(), filename="database_export.zip")
    await callback.message.answer_document(file, caption="🗄 Полная выгрузка БД готова!")
    await callback.message.edit_text("✅ Архив отправлен выше.", reply_markup=get_admin_help_kb())
    await callback.answer()

@router.callback_query(F.data == "admin_show_apps", F.func(is_admin_cb))
async def cb_show_apps(callback: CallbackQuery):
    await list_applications(callback.message)
    await callback.answer()

@router.callback_query(F.data == "admin_show_stats", F.func(is_admin_cb))
async def cb_show_stats(callback: CallbackQuery):
    await stats_activity(callback.message)
    await callback.answer()

# ---------- СПИСОК НЕОТВЕЧЕННЫХ ВОПРОСОВ ----------
async def show_pending_questions_list(message: Message):
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(Question).where(Question.status == 'pending').order_by(Question.created_at.asc())
            result = await session.execute(stmt)
            questions = result.scalars().all()

        if not questions:
            await message.answer("✅ <b>Отлично! Неотвеченных вопросов нет.</b>", parse_mode="HTML")
            return

        text = f"📋 <b>Вопросы без ответа ({len(questions)}):</b>\n\n"
        for q in questions:
            safe_name = html.escape(str(q.user_name))
            short_text = q.text[:70] + "..." if len(q.text) > 70 else q.text
            safe_text = html.escape(str(short_text))
            
            block = (
                f"❓ <b>#{q.id}</b> | От: {safe_name}\n"
                f"📝 <i>{safe_text}</i>\n"
                f"👉 Ответ: <code>/reply {q.id} [текст]</code>\n"
                f"─────────────────\n"
            )
            
            if len(text) + len(block) > 4000:
                await message.answer(text, parse_mode="HTML")
                text = f"📋 <b>Продолжение списка ({len(questions)}):</b>\n\n"
            
            text += block

        if text.strip():
            await message.answer(text, parse_mode="HTML")

    except Exception as e:
        print(f"ОШИБКА ВЫВОДА ВОПРОСОВ: {e}")
        await message.answer("❌ Произошла ошибка при загрузке списка вопросов.")

@router.callback_query(F.data == "admin_pending_questions", F.func(is_admin_cb))
async def cb_pending_questions(callback: CallbackQuery):
    await callback.answer("Загружаю...")
    await show_pending_questions_list(callback.message)

# ---------- НАСТРОЙКИ МОДУЛЕЙ ----------
@router.callback_query(F.data == "admin_modules", F.func(is_admin_cb))
async def show_modules(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        settings = await session.scalar(select(BotSettings).where(BotSettings.id == 1))
        status = "🟢 ВКЛЮЧЕН" if settings.is_contest_active else "🔴 ВЫКЛЮЧЕН"
    
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"Конкурс видео: {status}", callback_data="toggle_contest"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back_to_help"))
    
    await callback.message.edit_text(
        "⚙️ <b>Настройки модулей</b>\n\nНажмите на модуль, чтобы включить или выключить его.",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "toggle_contest", F.func(is_admin_cb))
async def toggle_contest(callback: CallbackQuery):
    async with AsyncSessionLocal() as session:
        settings = await session.scalar(select(BotSettings).where(BotSettings.id == 1))
        settings.is_contest_active = not settings.is_contest_active
        await session.commit()
    await show_modules(callback)

# ---------- МАССОВАЯ РАССЫЛКА ----------
class BroadcastState(StatesGroup):
    waiting_for_message = State()

@router.callback_query(F.data == "admin_broadcast", F.func(is_admin_cb))
async def start_broadcast(callback: CallbackQuery, state: FSMContext):
    await state.set_state(BroadcastState.waiting_for_message)
    await callback.message.edit_text(
        "📢 <b>Режим рассылки</b>\n\n"
        "Отправьте мне сообщение (текст, фото, видео, файл), которое нужно разослать всем пользователям бота.\n\n"
        "Для отмены напишите /cancel",
        parse_mode="HTML",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="❌ Отмена", callback_data="admin_back_to_help")
        ).as_markup()
    )
    await callback.answer()

# 1. Отмена рассылки по команде /cancel
@router.message(BroadcastState.waiting_for_message, Command("cancel"), F.func(is_admin))
async def cancel_broadcast(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Рассылка отменена.",
        reply_markup=get_admin_help_kb()
    )

# 2. Обработка сообщения для рассылки (команды через / игнорируются)
@router.message(BroadcastState.waiting_for_message, ~F.text.startswith("/"), F.func(is_admin))
async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    await state.clear()

    async with AsyncSessionLocal() as session:
        stmt = select(User.id)
        result = await session.execute(stmt)
        user_ids = result.scalars().all()

    if not user_ids:
        await message.answer("📭 В базе нет пользователей.")
        return

    status_msg = await message.answer(f"⏳ Начинаю рассылку для {len(user_ids)} пользователей...")
    
    success = 0
    failed = 0

    for user_id in user_ids:
        try:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            success += 1
        except Exception as e:
            print(f"❌ Ошибка рассылки для {user_id}: {type(e).__name__} - {e}")
            failed += 1
        
        await asyncio.sleep(0.05)

    await status_msg.edit_text(
        f"✅ <b>Рассылка завершена!</b>\n\n"
        f"Успешно доставлено: {success}\n"
        f"Ошибок (заблокировали бота): {failed}\n\n"
        f"<i>(Если ошибок много, проверь консоль)</i>",
        parse_mode="HTML",
        reply_markup=get_admin_help_kb()
    )
