from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode
from urllib.parse import urlparse

from database import AsyncSessionLocal
from models import SDGContent
from config import ADMIN_IDS
from utils.constants import SHORT_SDG_TITLES
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

router = Router()

class ContentForm(StatesGroup):
    waiting_text = State()
    waiting_video = State()

def is_admin_cb(callback: CallbackQuery) -> bool:
    return callback.from_user.id in ADMIN_IDS

# 1. Начало управления контентом
@router.callback_query(F.data == "admin_manage_sdg", F.func(is_admin_cb))
async def start_manage_sdg(callback: CallbackQuery):
    builder = InlineKeyboardBuilder()
    for i in range(1, 18):
        builder.button(text=SHORT_SDG_TITLES[i], callback_data=f"edit_sdg_{i}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ Назад в админку", callback_data="admin_back_to_help"))
    
    await callback.message.edit_text("Выберите ЦУР для редактирования:", reply_markup=builder.as_markup())
    await callback.answer()

# 2. Выбор возраста
@router.callback_query(F.data.startswith("edit_sdg_"), F.func(is_admin_cb))
async def choose_age(callback: CallbackQuery):
    sdg_id = int(callback.data.split("_")[2])
    builder = InlineKeyboardBuilder()
    builder.button(text="1-4 класс", callback_data=f"edit_age_{sdg_id}_1-4")
    builder.button(text="5-8 класс", callback_data=f"edit_age_{sdg_id}_5-8")
    builder.button(text="9-11 класс", callback_data=f"edit_age_{sdg_id}_9-11")
    builder.button(text="Для всех", callback_data=f"edit_age_{sdg_id}_all")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="◀️ Назад к списку ЦУР", callback_data="admin_manage_sdg"))
    
    await callback.message.edit_text(f"Выберите возрастную группу для ЦУР {sdg_id}:", reply_markup=builder.as_markup())
    await callback.answer()

# 3. Меню редактирования (Показывает текущий контент и кнопки действий)
async def show_content_menu(message_or_callback, sdg_id: int, age_group: str, edit_message=True):
    async with AsyncSessionLocal() as session:
        stmt = select(SDGContent).where(
            (SDGContent.sdg_id == sdg_id) & 
            (SDGContent.age_group == age_group)
        )
        content = await session.scalar(stmt)

    text_desc = content.description if content and content.description else "❌ Текст не задан"
    video_url = content.video_url if content and content.video_url else "❌ Видео не задано"

    text = (
        f"⚙️ <b>Редактирование ЦУР {sdg_id}</b> (Возраст: {age_group})\n\n"
        f"<b>Текущий текст:</b>\n<i>{text_desc}</i>\n\n"
        f"<b>Текущее видео:</b> {video_url}"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ Изменить текст", callback_data=f"edit_text_{sdg_id}_{age_group}"),
        InlineKeyboardButton(text="🎥 Изменить видео", callback_data=f"edit_video_{sdg_id}_{age_group}")
    )
    builder.row(InlineKeyboardButton(text="🗑 Очистить контент", callback_data=f"edit_clear_{sdg_id}_{age_group}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад к выбору возраста", callback_data=f"edit_sdg_{sdg_id}"))

    if edit_message and hasattr(message_or_callback, 'message'):
        await message_or_callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)
    else:
        await message_or_callback.answer(text, reply_markup=builder.as_markup(), parse_mode=ParseMode.HTML)

@router.callback_query(F.data.startswith("edit_age_"), F.func(is_admin_cb))
async def open_content_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()  # Сбрасываем состояние, если нажали "Отмена" при вводе текста/видео
    parts = callback.data.split("_")
    sdg_id = int(parts[2])
    age = parts[3]
    await show_content_menu(callback, sdg_id, age)
    await callback.answer()

# 4. Редактирование ТЕКСТА
@router.callback_query(F.data.startswith("edit_text_"), F.func(is_admin_cb))
async def start_edit_text(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    sdg_id = int(parts[2])
    age = parts[3]
    
    await state.update_data(sdg_id=sdg_id, age_group=age, action="text")
    await state.set_state(ContentForm.waiting_text)
    
    await callback.message.edit_text(
        f"✏️ Введите новый текст описания для ЦУР {sdg_id} (возраст: {age}).\n\n"
        f"Отправьте текст одним сообщением.",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_age_{sdg_id}_{age}")
        ).as_markup()
    )
    await callback.answer()

# 5. Редактирование ВИДЕО
@router.callback_query(F.data.startswith("edit_video_"), F.func(is_admin_cb))
async def start_edit_video(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    sdg_id = int(parts[2])
    age = parts[3]
    
    await state.update_data(sdg_id=sdg_id, age_group=age, action="video")
    await state.set_state(ContentForm.waiting_video)
    
    await callback.message.edit_text(
        f"🎥 Отправьте ссылку на видео (YouTube/Rutube) для ЦУР {sdg_id} (возраст: {age}).\n\n"
        f"Ссылка должна начинаться строго с <b>https://</b>",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="❌ Отмена", callback_data=f"edit_age_{sdg_id}_{age}")
        ).as_markup(),
        parse_mode="HTML"
    )
    await callback.answer()

# Прием текста
@router.message(ContentForm.waiting_text, F.func(lambda msg: msg.from_user.id in ADMIN_IDS))
async def save_text(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовое сообщение.")
        return

    data = await state.get_data()
    sdg_id, age = data['sdg_id'], data['age_group']
    new_text = message.text

    async with AsyncSessionLocal() as session:
        stmt = insert(SDGContent).values(
            sdg_id=sdg_id, age_group=age, description=new_text, video_url=None
        )
        stmt = stmt.on_conflict_do_update(
            constraint='uq_sdg_age',
            set_=dict(description=new_text)
        )
        await session.execute(stmt)
        await session.commit()

    await state.clear()
    await message.answer("✅ Текст успешно сохранен!")
    await show_content_menu(message, sdg_id, age, edit_message=False)

# Прием видео
@router.message(ContentForm.waiting_video, F.func(lambda msg: msg.from_user.id in ADMIN_IDS))
async def save_video(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пожалуйста, отправьте текстовую ссылку.")
        return

    data = await state.get_data()
    sdg_id, age = data['sdg_id'], data['age_group']
    url = message.text.strip()

    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.netloc or "." not in parsed.netloc:
        await message.answer(
            "❌ Небезопасная или некорректная ссылка.\n"
            "Ссылка должна начинаться строго с <b>https://</b> и вести на реальный сайт.\n"
            "Попробуйте еще раз:",
            parse_mode="HTML"
        )
        return

    # Восстановленный блок сохранения в БД:
    async with AsyncSessionLocal() as session:
        stmt = insert(SDGContent).values(
            sdg_id=sdg_id, age_group=age, description="Текст будет добавлен позже.", video_url=url
        )
        stmt = stmt.on_conflict_do_update(
            constraint='uq_sdg_age',
            set_=dict(video_url=url)
        )
        await session.execute(stmt)
        await session.commit()

    await state.clear()
    await message.answer("✅ Ссылка на видео сохранена!")
    await show_content_menu(message, sdg_id, age, edit_message=False)

# Очистка контента
@router.callback_query(F.data.startswith("edit_clear_"), F.func(is_admin_cb))
async def clear_content(callback: CallbackQuery):
    parts = callback.data.split("_")
    sdg_id = int(parts[2])
    age = parts[3]
    
    async with AsyncSessionLocal() as session:
        stmt = select(SDGContent).where((SDGContent.sdg_id == sdg_id) & (SDGContent.age_group == age))
        content = await session.scalar(stmt)
        if content:
            await session.delete(content)
            await session.commit()
            
    await callback.answer("🗑 Контент удален!", show_alert=True)
    await show_content_menu(callback, sdg_id, age)

# Обработчик возврата в админку
@router.callback_query(F.data == "admin_back_to_help", F.func(is_admin_cb))
async def back_to_help(callback: CallbackQuery, state: FSMContext):
    await state.clear()  # Сбрасываем состояние рассылки или редактирования
    from keyboards.admin_kb import get_admin_help_kb
    await callback.message.edit_text(
        "👑 <b>Панель администратора:</b>\nВыберите действие на кнопках ниже.",
        reply_markup=get_admin_help_kb(),
        parse_mode="HTML"
    )
    await callback.answer()
