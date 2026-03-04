from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_keyboard(user_id: int = None, is_premium: bool = False) -> InlineKeyboardMarkup:
    """Красивое главное меню"""
    builder = InlineKeyboardBuilder()
    
    # ========== ОСНОВНЫЕ ФУНКЦИИ ==========
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
        builder.row(
            InlineKeyboardButton(text="👑 ПРЕМИУМ (299₽/мес)", callback_data="show_premium_info")
        )
    
    # ========== ДНЕВНИК И ЛЕНТА ==========
    builder.row(
        InlineKeyboardButton(text="📔 ДНЕВНИК ТРЕНИРОВОК", callback_data="workout_journal"),
        InlineKeyboardButton(text="📰 ЛЕНТА АКТИВНОСТИ", callback_data="feed")
    )
    
    # ========== РЕЖИМ ДНЯ ==========
    builder.row(
        InlineKeyboardButton(text="📅 РЕЖИМ ДНЯ", callback_data="daily_routine")
    )
    
    # ========== УПРАЖНЕНИЯ И РЕКОМЕНДАЦИИ ==========
    builder.row(
        InlineKeyboardButton(text="💪 УПРАЖНЕНИЯ", callback_data="exercises"),
        InlineKeyboardButton(text="💡 РЕКОМЕНДАЦИИ", callback_data="recommendations")
    )
    
    # ========== ИНСТРУМЕНТЫ ==========
    builder.row(
        InlineKeyboardButton(text="⏱️ ТАЙМЕР", callback_data="timer"),
        InlineKeyboardButton(text="📅 КАЛЕНДАРЬ", callback_data="calendar")
    )
    
    # ========== СОЦИАЛЬНОЕ ==========
    builder.row(
        InlineKeyboardButton(text="🏆 ЛИДЕРБОРД", callback_data="global_leaderboard"),
        InlineKeyboardButton(text="🏅 АЧИВКИ", callback_data="achievements")
    )
    
    # ========== ПЛАТЕЖИ И НАСТРОЙКИ ==========
    builder.row(
        InlineKeyboardButton(text="💳 ПЛАТЕЖИ", callback_data="payment"),
        InlineKeyboardButton(text="⚙️ НАСТРОЙКИ", callback_data="settings")
    )
    
    return builder.as_markup()