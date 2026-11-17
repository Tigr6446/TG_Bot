from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from database import AsyncSessionLocal
from models import User
from sqlalchemy import select
from keyboards.age_kb import get_age_kb
from keyboards.main_menu_kb import get_main_kb
from keyboards.admin_kb import get_admin_help_kb
from config import ADMIN_IDS, ADMIN_CHAT_ID

router = Router()

@router.message(Command("start"))
async def command_start(message: Message):
    if message.chat.id == ADMIN_CHAT_ID:
        await message.answer(
            "👑 <b>Панель администратора:</b>\nВыберите действие на кнопках ниже.",
            reply_markup=get_admin_help_kb(),
            parse_mode="HTML"
        )
        return
    
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            await message.answer(
                "👋 Привет! Для начала выбери свою возрастную группу:",
                reply_markup=get_age_kb()
            )
        elif not user.age_group:
            await message.answer(
                "📊 Выбери свою возрастную группу:",
                reply_markup=get_age_kb()
            )
        else:
            await message.answer(
                f"✅ Добро пожаловать, {message.from_user.first_name or 'пользователь'}!\n\n"
                "Выберите раздел:",
                reply_markup=get_main_kb()
            )

@router.message(Command("help"))
async def command_help(message: Message):
    is_admin = message.from_user.id in ADMIN_IDS
    
    help_text = (
        "🤖 <b>Доступные команды:</b>\n\n"
        "🔹 /start — Перезапустить бота\n"
        "🔹 /help — Показать это сообщение\n"
        "🔹 /cancel — Отменить действие\n"
    )
    
    if is_admin:
        help_text += "\n👑 <b>Панель администратора:</b>\nВыберите действие на кнопках ниже или используйте команды: /reply, /approve, /reject."
        # Отправляем с кнопками для админа
        await message.answer(help_text, reply_markup=get_admin_help_kb(), parse_mode="HTML")
    else:
        # Отправляем без кнопок для обычных юзеров
        await message.answer(help_text, parse_mode="HTML")

@router.callback_query(F.data.startswith("age_"))
async def set_age_inline(callback: CallbackQuery):
    age_map = {
        "age_1_4": "1-4",
        "age_5_8": "5-8",
        "age_9_11": "9-11",
    }
    
    age_group = age_map.get(callback.data)
    if not age_group:
        await callback.answer("Ошибка выбора возраста")
        return
    
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.id == callback.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(
                id=callback.from_user.id,
                username=callback.from_user.username or callback.from_user.first_name,
                age_group=age_group
            )
            session.add(user)
        else:
            user.age_group = age_group
        
        await session.commit()
    
    try:
        await callback.message.delete()
    except:
        pass
    
    await callback.message.answer(
        f"✅ Возрастная группа сохранена!\n\n"
        "Теперь выберите раздел:",
        reply_markup=get_main_kb()
    )
    await callback.answer()