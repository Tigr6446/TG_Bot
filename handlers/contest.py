from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode
from sqlalchemy import select

from database import AsyncSessionLocal
from models import VideoContest, BotSettings
from keyboards.contest_kb import get_contest_start_kb, get_contest_admin_kb
from keyboards.main_menu_kb import get_main_kb
from config import ADMIN_CHAT_ID, ADMIN_IDS

router = Router()

class ContestForm(StatesGroup):
    waiting_video = State()
    waiting_description = State()

# ЕДИНСТВЕННЫЙ ОБРАБОТЧИК КНОПКИ КОНКУРСА
@router.callback_query(F.data == "menu_contest")
async def start_contest(callback: CallbackQuery, state: FSMContext):
    # Проверяем настройки модуля
    async with AsyncSessionLocal() as session:
        settings = await session.scalar(select(BotSettings).where(BotSettings.id == 1))
        if not settings.is_contest_active:
            await callback.message.answer(
                "🎥 <b>Конкурс «Я есть ЦУР»</b>\n\n"
                "😔 К сожалению, прием работ на конкурс уже завершен.\n"
                "Следите за новостями, мы обязательно объявим о новом этапе!",
                parse_mode=ParseMode.HTML
            )
            await callback.answer()
            return
    
    # Если конкурс включен — запускаем FSM
    await state.set_state(ContestForm.waiting_video)
    await callback.message.answer(
        "🎥 <b>Конкурс «Я есть ЦУР»</b>\n\n"
        "Пришлите ваше видео (или файл) сюда. Оно должно быть посвящено одной из ЦУР.",
        reply_markup=get_contest_start_kb(),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()

# Ловим старое сообщение с кнопкой загрузки (чтобы не висело)
@router.callback_query(F.data == "contest_upload")
async def handle_old_upload_button(callback: CallbackQuery):
    await callback.answer(
        "Просто отправьте видео следующим сообщением в чат (скрепка -> Видео/Файл).", 
        show_alert=True
    )

@router.message(ContestForm.waiting_video, F.video | F.document)
async def process_video(message: Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    await state.update_data(video_file_id=file_id)
    await state.set_state(ContestForm.waiting_description)
    await message.answer(
        "✅ Видео получено!\n\n"
        "Теперь напишите небольшой комментарий к вашему ролику."
    )

@router.message(ContestForm.waiting_video)
async def wrong_video_format(message: Message):
    await message.answer("❌ Пожалуйста, отправьте именно видео или файл.")

@router.message(ContestForm.waiting_description)
async def process_description(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    video_file_id = data.get("video_file_id")
    
    async with AsyncSessionLocal() as session:
        contest_entry = VideoContest(
            user_id=message.from_user.id,
            username=message.from_user.username or message.from_user.first_name,
            video_file_id=video_file_id,
            description=message.text
        )
        session.add(contest_entry)
        await session.flush()
        
        admin_text = (
            f"🎬 <b>Новая заявка на конкурс!</b>\n\n"
            f"<b>ID заявки:</b> {contest_entry.id}\n"
            f"<b>От:</b> @{contest_entry.username} (ID: {message.from_user.id})\n"
            f"<b>Комментарий:</b> {message.text}\n"
        )
        
        try:
            await bot.send_video(
                chat_id=ADMIN_CHAT_ID,
                video=video_file_id,
                caption=admin_text,
                reply_markup=get_contest_admin_kb(contest_entry.id),
                parse_mode=ParseMode.HTML
            )
        except Exception:
            await bot.send_document(
                chat_id=ADMIN_CHAT_ID,
                document=video_file_id,
                caption=admin_text,
                reply_markup=get_contest_admin_kb(contest_entry.id),
                parse_mode=ParseMode.HTML
            )
            
        await session.commit()
    
    await message.answer(
        "🎉 <b>Спасибо! Ваша заявка отправлена на рассмотрение жюри.</b>",
        reply_markup=get_main_kb(),
        parse_mode=ParseMode.HTML
    )
    await state.clear()

# --- ОБРАБОТЧИКИ ДЛЯ АДМИНОВ ---

def is_admin_cb(callback: CallbackQuery) -> bool:
    return callback.from_user.id in ADMIN_IDS

@router.callback_query(F.data.startswith("contest_approve_"), F.func(is_admin_cb))
async def approve_contest(callback: CallbackQuery, bot: Bot):
    contest_id = int(callback.data.split("_")[2])
    
    async with AsyncSessionLocal() as session:
        stmt = select(VideoContest).where(VideoContest.id == contest_id)
        result = await session.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            entry.status = "approved"
            await session.commit()
            
            old_caption = callback.message.caption or ""
            await callback.message.edit_caption(
                caption=old_caption + "\n\n✅ <b>СТАТУС: ПРИНЯТО</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=None 
            )
            try:
                await bot.send_message(
                    entry.user_id, 
                    "🎉 Поздравляем! Ваше видео прошло модерацию и отправлено в финал конкурса!"
                )
            except:
                pass
    await callback.answer("Видео принято!")

@router.callback_query(F.data.startswith("contest_reject_"), F.func(is_admin_cb))
async def reject_contest(callback: CallbackQuery):
    contest_id = int(callback.data.split("_")[2])
    
    async with AsyncSessionLocal() as session:
        stmt = select(VideoContest).where(VideoContest.id == contest_id)
        result = await session.execute(stmt)
        entry = result.scalar_one_or_none()
        if entry:
            entry.status = "rejected"
            await session.commit()
            
            old_caption = callback.message.caption or ""
            await callback.message.edit_caption(
                caption=old_caption + "\n\n❌ <b>СТАТУС: ОТКЛОНЕНО</b>",
                parse_mode=ParseMode.HTML,
                reply_markup=None
            )
    await callback.answer("Видео отклонено")