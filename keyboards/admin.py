from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="📊 Статистика бота", callback_data="admin_stats")
    )
    builder.row(
        InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users"),
        InlineKeyboardButton(text="⚙️ Настройки бота", callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ На главную", callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_admin_back_keyboard() -> InlineKeyboardMarkup:
    """Кнопка возврата в админ-панель"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="admin_panel"))
    return builder.as_markup()