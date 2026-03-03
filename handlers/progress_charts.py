from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.callback_query(F.data == "progress_charts")
async def show_charts_menu(callback: CallbackQuery):
    """Меню графиков прогресса"""
    await callback.message.edit_text(
        "📊 *Графики прогресса*\n\nФункция в разработке",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="progress_stats")
        ).as_markup()
    )
    await callback.answer()