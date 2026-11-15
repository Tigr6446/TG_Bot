from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_help_kb():
    builder = InlineKeyboardBuilder()
    
    # Кнопки для выгрузок
    builder.row(
        InlineKeyboardButton(text="📊 Выгрузить отзывы (CSV)", callback_data="admin_export_feedback"),
        InlineKeyboardButton(text="Выгрузить БД (ZIP)", callback_data="admin_export_db")
    )
    
    # Кнопки для заявок и статистики
    builder.row(
        InlineKeyboardButton(text="📋 Посмотреть заявки", callback_data="admin_show_apps"),
        InlineKeyboardButton(text="📈 Статистика", callback_data="admin_show_stats")
    )
    
    # КНОПКА ДЛЯ НЕОТВЕЧЕННЫХ ВОПРОСОВ
    builder.row(
        InlineKeyboardButton(text="❓ Неотвеченные вопросы", callback_data="admin_pending_questions")
    )

    builder.row(
        InlineKeyboardButton(text="📚 Управление контентом ЦУР", callback_data="admin_manage_sdg")
    )
    
    builder.row(
        InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_broadcast")
    )

    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки модулей", callback_data="admin_modules")
    )
    
    return builder.as_markup()

