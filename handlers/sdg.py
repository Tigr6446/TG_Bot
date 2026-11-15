from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from keyboards.main_menu_kb import get_main_kb
from utils.constants import SDG_TITLES
from keyboards.sdg_keyboards import get_sdg_list_kb, get_sdg_detail_kb, get_sdg_back_kb
from services.analytics import log_activity
from sqlalchemy import select # <--- ДОБАВЛЕНО
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ДОБАВЛЕНО:
from database import AsyncSessionLocal
from models import User, SDGContent

router = Router()


@router.message(F.text == "📚 Цели устойчивого развития")
@router.callback_query(F.data == "menu_sdg")
async def show_sdg_list(update: Message | CallbackQuery):
    if isinstance(update, CallbackQuery):
        message = update.message
        await update.answer()
        try:
            await message.delete()
        except:
            pass
    else:
        message = update

    await message.answer(
        "🌍 <b>Цели устойчивого развития</b>\n\n"
        "Выберите цель, чтобы узнать подробнее:",
        reply_markup=get_sdg_list_kb(),
        parse_mode=ParseMode.HTML
    )


@router.callback_query(F.data.startswith("sdg_"))
async def show_sdg_detail(callback: CallbackQuery):
    sdg_num = int(callback.data.split("_")[1])

    # Получаем возраст пользователя
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.id == callback.from_user.id))
        age_group = user.age_group if user else "all"
        
        # Ищем контент для этого возраста (или для всех)
        stmt = select(SDGContent).where(
            (SDGContent.sdg_id == sdg_num) & 
            (SDGContent.age_group.in_([age_group, "all"]))
        ).order_by(SDGContent.age_group.desc()) # Сначала ищем конкретный возраст, потом "all"
        
        content = await session.scalar(stmt)

    await log_activity(
        user_id=callback.from_user.id,
        action="view_sdg",
        target_id=sdg_num,
        details=f"sdg_{sdg_num}"
    )

    title = SDG_TITLES.get(sdg_num)

    if content:
        # Если текст есть в базе
        text = f"<b>{title}</b>\n\n{content.description}"
    else:
        # Если админ еще не загрузил текст
        text = f"<b>{title}</b>\n\n📝 <i>Подробный текст для этой возрастной группы скоро появится!</i>"

    await callback.message.edit_text(
        text,
        reply_markup=get_sdg_detail_kb(sdg_num),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_sdg_list")
async def back_to_sdg_list_handler(callback: CallbackQuery):
    await show_sdg_list(callback)
    await callback.answer()


@router.callback_query(F.data == "back_to_main_menu")
async def back_to_main_menu_handler(callback: CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass

    await callback.message.answer(
        "Главное меню:",
        reply_markup=get_main_kb()
    )
    await callback.answer()


@router.callback_query(F.data.startswith("back_to_sdg_"))
async def back_to_lecture(callback: CallbackQuery):
    """Возврат к лекции с полным меню"""
    sdg_num = int(callback.data.split("_")[3])
    
    # Тут тоже нужно подтянуть контент, чтобы не потерять текст при возврате
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.id == callback.from_user.id))
        age_group = user.age_group if user else "all"
        stmt = select(SDGContent).where(
            (SDGContent.sdg_id == sdg_num) & 
            (SDGContent.age_group.in_([age_group, "all"]))
        ).order_by(SDGContent.age_group.desc())
        content = await session.scalar(stmt)

    title = SDG_TITLES.get(sdg_num)
    
    if content:
        text = f"<b>{title}</b>\n\n{content.description}"
    else:
        text = f"<b>{title}</b>\n\n📝 <i>Подробный текст для этой возрастной группы скоро появится!</i>"

    await callback.message.edit_text(
        text,
        reply_markup=get_sdg_detail_kb(sdg_num),
        parse_mode=ParseMode.HTML
    )
    await callback.answer()


@router.callback_query(F.data.startswith("video_"))
async def show_sdg_video(callback: CallbackQuery):
    """Обработчик кнопки 'Видео'"""
    sdg_num = int(callback.data.split("_")[1])
    
    # Ищем ссылку на видео в базе данных
    async with AsyncSessionLocal() as session:
        user = await session.scalar(select(User).where(User.id == callback.from_user.id))
        age_group = user.age_group if user else "all"
        
        stmt = select(SDGContent).where(
            (SDGContent.sdg_id == sdg_num) & 
            (SDGContent.age_group.in_([age_group, "all"]))
        ).order_by(SDGContent.age_group.desc())
        
        content = await session.scalar(stmt)

    # Если админ добавил ссылку — показываем кнопку
    if content and content.video_url:
        builder = InlineKeyboardBuilder()
        builder.row(InlineKeyboardButton(text="▶️ Смотреть видео", url=content.video_url))
        
        await callback.message.answer(
            f"🎥 <b>Видео по ЦУР {sdg_num}</b>\n\nНажмите на кнопку ниже, чтобы открыть ролик.",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.HTML
        )
    else:
        # Если ссылки нет — показываем всплывающее окно (alert)
        await callback.answer("🎥 Видео для этой ЦУР пока не добавлено администратором.", show_alert=True)


@router.callback_query(F.data.startswith("more_"))
async def show_sdg_more(callback: CallbackQuery):
    """Обработчик кнопки 'Подробнее'"""
    sdg_num = int(callback.data.split("_")[1])
    
    # Берем официальный длинный текст из constants.py
    title = SDG_TITLES.get(sdg_num, f"ЦУР {sdg_num}")
    
    # Отправляем новым сообщением, чтобы не ломать текущую карточку
    await callback.message.answer(
        f"📖 <b>Подробнее о Цели {sdg_num}</b>\n\n"
        f"{title}\n\n"
        f"<i>Эта цель направлена на решение глобальных проблем. Подробную информацию и адаптированный под ваш возраст текст можно прочитать в базе знаний ООН или в лекции.</i>",
        parse_mode=ParseMode.HTML
    )
    await callback.answer()