from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_contest_start_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="◀️ В главное меню", callback_data="back_to_main_menu"))
    return builder.as_markup()

def get_contest_admin_kb(contest_id: int):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Принять", callback_data=f"contest_approve_{contest_id}"),
        InlineKeyboardButton(text="❌ Отклонить", callback_data=f"contest_reject_{contest_id}")
    )
    return builder.as_markup()