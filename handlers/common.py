from aiogram import Router
from aiogram.types import Message, CallbackQuery
from keyboards.main import get_main_keyboard

router = Router()


@router.message()
async def unknown_message(message: Message):
    """Обработка неизвестных сообщений вне FSM."""
    await message.answer(
        "👋 Привет! Используй меню ниже или команду /start",
        reply_markup=get_main_keyboard(),
    )


@router.callback_query()
async def handle_all_callbacks(callback: CallbackQuery):
    """Обработчик callback-ов, которые не нашли другие обработчики"""
    await callback.answer()