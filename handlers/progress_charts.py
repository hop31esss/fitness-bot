from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.callback_query(F.data == "progress_charts")
async def charts_test(callback: CallbackQuery):
    """Тестовая функция"""
    await callback.message.edit_text(
        "📊 Графики временно отключены",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="◀️ НАЗАД", callback_data="progress_stats")
        ).as_markup()
    )
    await callback.answer()