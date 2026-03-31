from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_keyboard(user_id: int = None, is_premium: bool = False) -> InlineKeyboardMarkup:
    """Компактное главное меню"""
    builder = InlineKeyboardBuilder()
    
    # ========== ОСНОВНЫЕ ФУНКЦИИ ==========
    builder.row(
        InlineKeyboardButton(text="📋 ЖУРНАЛ ТРЕНИРОВОК", callback_data="training_journal"),
        InlineKeyboardButton(text="📊 ПРОГРЕСС И СТАТИСТИКА", callback_data="progress_stats")
    )
    
    # ========== ДНЕВНИК ==========
    builder.row(
        InlineKeyboardButton(text="📔 ДНЕВНИК ТРЕНИРОВОК", callback_data="workout_journal"),
        InlineKeyboardButton(text="📚 МОИ ПРОГРАММЫ", callback_data="templates")
    )
    
    
    # ========== РЕЖИМ ДНЯ И УПРАЖНЕНИЯ ==========
    builder.row(
        InlineKeyboardButton(text="⏰ РЕЖИМ ДНЯ", callback_data="daily_routine"),
        InlineKeyboardButton(text="💪 УПРАЖНЕНИЯ", callback_data="exercises"),
        InlineKeyboardButton(text="📅 КАЛЕНДАРЬ", callback_data="calendar")
    )
    
    # ========== РЕКОМЕНДАЦИИ И AI-СОВЕТЫ ==========
    builder.row(
        InlineKeyboardButton(text="💡 РЕКОМЕНДАЦИИ", callback_data="recommendations"),
        InlineKeyboardButton(text="🤖 AI-СОВЕТЫ", callback_data="ai_advice")
    )
    
    # ========== ИНСТРУМЕНТЫ (ТАЙМЕР СКРЫТ ИЗ МЕНЮ) ==========
    builder.row(
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
    
     # ========== ПРЕМИУМ БЛОК ==========
    if is_premium:
        # Для премиум - показываем все премиум-функции
        builder.row(
            InlineKeyboardButton(text="🏋️ 1ПМ КАЛЬКУЛЯТОР", callback_data="one_rep_max")
        )
        builder.row(
            InlineKeyboardButton(text="🔥 ТРЕКЕР КАЛОРИЙ", callback_data="calorie_tracker")
        )
        builder.row(
            InlineKeyboardButton(text="🏆 ЧЕЛЛЕНДЖИ", callback_data="challenges_menu")
        )
    else:
        # Для обычных - только кнопка покупки
        builder.row(
            InlineKeyboardButton(text="👑 ПРЕМИУМ (150₽/мес)", callback_data="show_premium_info")
        )

    # ========== СОЦИАЛЬНОЕ (ДРУЗЬЯ СКРЫТЫ ИЗ МЕНЮ) ==========
    builder.row(
        InlineKeyboardButton(text="🤝 РЕФЕРАЛЫ", callback_data="referral")
    )
    
    return builder.as_markup()