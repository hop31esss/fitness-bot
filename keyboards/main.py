from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_main_keyboard(user_id: int | None = None) -> InlineKeyboardMarkup:
    """Главное меню: четыре стабильных тематических раздела."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ ТРЕНИРОВКИ", callback_data="menu_training"),
        InlineKeyboardButton(text="📊 ПРОГРЕСС", callback_data="menu_progress"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 AI-СОВЕТЫ", callback_data="menu_ai"),
        InlineKeyboardButton(text="👤 ПРОФИЛЬ", callback_data="menu_profile"),
    )
    return builder.as_markup()
