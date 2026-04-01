from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_main_keyboard(user_id: int = None) -> InlineKeyboardMarkup:
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
    
    # ========== ПРЕМИУМ (одна кнопка для всех; детали — внутри разделов) ==========
    builder.row(
        InlineKeyboardButton(text="👑 ПРЕМИУМ", callback_data="show_premium_info")
    )

    # ========== СОЦИАЛЬНОЕ (ДРУЗЬЯ СКРЫТЫ ИЗ МЕНЮ) ==========
    builder.row(
        InlineKeyboardButton(text="🤝 РЕФЕРАЛЫ", callback_data="referral")
    )
    
    return builder.as_markup()