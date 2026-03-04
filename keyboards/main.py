from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_keyboard(user_id: int = None, is_premium: bool = False) -> InlineKeyboardMarkup:
    """Красивое главное меню"""
    builder = InlineKeyboardBuilder()
    
    # ========== ОСНОВНЫЕ ФУНКЦИИ (для всех) ==========
    builder.row(
        InlineKeyboardButton(text="📋 ЖУРНАЛ ТРЕНИРОВОК", callback_data="training_journal")
    )
    
    builder.row(
        InlineKeyboardButton(text="📈 ПРОГРЕСС И СТАТИСТИКА", callback_data="progress_stats")
    )
    builder.row(
            InlineKeyboardButton(text="🤖 AI-СОВЕТЫ", callback_data="ai_advice")
    )
    
    # ========== ПРЕМИУМ БЛОК ==========
    if is_premium:
    # Для премиум - показываем сразу премиум-функции
        builder.row(
            InlineKeyboardButton(text="🏋️ 1ПМ КАЛЬКУЛЯТОР", callback_data="one_rep_max")
        )
        builder.row(
            InlineKeyboardButton(text="🔥 ТРЕКЕР КАЛОРИЙ", callback_data="calorie_tracker")
        )
        builder.row(
            InlineKeyboardButton(text="👥 ДРУЗЬЯ", callback_data="friends_menu"),
            InlineKeyboardButton(text="🏆 ЧЕЛЛЕНДЖИ", callback_data="challenges_menu")
        )
    else:
    # Для обычных - кнопка покупки премиум
        builder.row(
            InlineKeyboardButton(text="👑 ПРЕМИУМ (299₽/мес)", callback_data="show_premium_info")
        )
    
    # ========== ОБЩИЕ ИНСТРУМЕНТЫ ==========
    tools_row = []
    tools_row.append(InlineKeyboardButton(text="⏱️ ТАЙМЕР", callback_data="timer"))
    tools_row.append(InlineKeyboardButton(text="📅 КАЛЕНДАРЬ", callback_data="calendar"))
    builder.row(*tools_row)
    
    # ========== СОЦИАЛЬНОЕ ==========
    social_row = []
    social_row.append(InlineKeyboardButton(text="🏆 ЛИДЕРБОРД", callback_data="global_leaderboard"))
    social_row.append(InlineKeyboardButton(text="🏅 АЧИВКИ", callback_data="achievements"))
    builder.row(*social_row)
    
    # ========== ИНФОРМАЦИЯ ==========
    builder.row(
        InlineKeyboardButton(text="⚙️ НАСТРОЙКИ", callback_data="settings")
    )

    # ========== АДМИНКА УБРАНА ==========
    # Доступ только через команду /admin

    return builder.as_markup()