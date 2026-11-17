import asyncio
from aiogram import Bot, Dispatcher, BaseMiddleware
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatType
from config import BOT_TOKEN, ADMIN_CHAT_ID
from database import create_table

# Импорт всех роутеров
from handlers.main_menu import router as main_menu_router
from handlers.sdg import router as sdg_router
from handlers.start import router as start_router
from handlers.settings import router as settings_router
from handlers.questions import router as questions_router
from handlers.admin import router as admin_router
from handlers.quizzes import router as quiz_router
from handlers.games import games_router
from handlers.ambassador import router as ambassador_router
from handlers.feedback import router as feedback_router
from handlers.contest import router as contest_router
from handlers.admin_content import router as admin_content_router

from aiogram.types import BotCommand 

# --- MIDDLEWARE ДЛЯ БЛОКИРОВКИ БОТА В АДМИН-ЧАТЕ ---
class AdminChatBlocker(BaseMiddleware):
    async def __call__(self, handler, event, data):
        # Определяем ID чата
        chat_id = None
        if isinstance(event, Message):
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery):
            chat_id = event.message.chat.id

        # Если сообщение пришло из АДМИН-ЧАТА
        if chat_id == ADMIN_CHAT_ID:
            # 1. ПРОПУСКАЕМ, ЕСЛИ АДМИН ВВОДИТ ТЕКСТ ДЛЯ ЦУР ИЛИ РАССЫЛКИ (FSM)
            state = data.get('state')
            if state:
                current_state = await state.get_state()
                if current_state and (
                    current_state.startswith("ContentForm") or 
                    current_state.startswith("BroadcastState")
                ):
                    return await handler(event, data)

            # 2. РАЗРЕШАЕМ ВСЕ ТЕКСТОВЫЕ КОМАНДЫ
            if isinstance(event, Message) and event.text:
                if event.text.startswith("/"):
                    return await handler(event, data)
                # Если это просто болтовня (не команда) — игнорируем
                return

            # 3. РАЗРЕШАЕМ НУЖНЫЕ КНОПКИ (CALLBACKS)
            if isinstance(event, CallbackQuery):
                allowed_callbacks = (
                    "contest_approve_", "contest_reject_", 
                    "admin_", 
                    "toggle_",
                    "edit_sdg_", "edit_age_", "edit_text_", "edit_video_", "edit_clear_"
                )
                if any(event.data.startswith(prefix) for prefix in allowed_callbacks):
                    return await handler(event, data)

            # Всё остальное (не команды и не разрешенные кнопки) игнорируем
            return

        # Если это не админ-чат (например, личка с обычным юзером), пропускаем дальше
        return await handler(event, data)
    

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Подключаем блокировщик
dp.message.outer_middleware(AdminChatBlocker())
dp.callback_query.outer_middleware(AdminChatBlocker())

async def main():
    # 1. Создаём таблицы в БД
    await create_table()
    print("✅ Таблицы созданы/проверены")
    
    # 2. Устанавливаем команды для меню бота
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню"),
        BotCommand(command="help", description="Список команд и панель админа")
    ])
    
    # 3. Подключаем все обработчики (роутеры)
    dp.include_router(sdg_router)
    dp.include_router(contest_router)
    dp.include_router(main_menu_router)
    dp.include_router(start_router)
    dp.include_router(settings_router)
    dp.include_router(questions_router)
    dp.include_router(admin_router)
    dp.include_router(quiz_router)
    dp.include_router(games_router)
    dp.include_router(ambassador_router)
    dp.include_router(feedback_router)
    dp.include_router(admin_content_router)

    # 4. Запускаем бота
    print("🤖 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())