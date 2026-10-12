from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ParseMode
from keyboards.main_menu_kb import get_main_kb
from utils.constants import SDG_TITLES
from keyboards.sdg_keyboards import get_sdg_list_kb, get_sdg_detail_kb, get_sdg_back_kb
from services.analytics import log_activity

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

    await log_activity(
        user_id=callback.from_user.id,
        action="view_sdg",
        target_id=sdg_num,
        details=f"sdg_{sdg_num}"
    )

    title = SDG_TITLES.get(sdg_num)

    await callback.message.edit_text(
        f"{title}\n\n"
        f"Текст ЦУР для данной возрастной группы",
        reply_markup=get_sdg_detail_kb(sdg_num)
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

    title = SDG_TITLES.get(sdg_num)

    await callback.message.edit_text(
        f"🎯 **Цель {sdg_num}: {title}**\n\n"
        f"Текст для данной возрастной группы",
        reply_markup=get_sdg_detail_kb(sdg_num)
    )
    await callback.answer()