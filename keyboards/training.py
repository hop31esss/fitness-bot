from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_training_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура журнала тренировок"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🏋️ НАЧАТЬ ТРЕНИРОВКУ", callback_data="start_workout"),
        InlineKeyboardButton(text="📋 ИСТОРИЯ", callback_data="workout_history")
    )
    builder.row(
        InlineKeyboardButton(text="💪 МОИ УПРАЖНЕНИЯ", callback_data="my_exercises"),
        InlineKeyboardButton(text="📝 ДОБАВИТЬ УПРАЖНЕНИЕ", callback_data="add_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_exercises_keyboard(exercises: list) -> InlineKeyboardMarkup:
    """Клавиатура со списком упражнений"""
    builder = InlineKeyboardBuilder()
    
    for ex in exercises:
        name = ex.get('alias') or ex.get('name')
        builder.row(
            InlineKeyboardButton(text=f"💪 {name}", callback_data=f"select_ex:{ex['name']}")
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ НОВОЕ", callback_data="new_exercise"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="training_journal")
    )
    
    return builder.as_markup()

def get_timer_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для таймера"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="⏱️ 30 сек", callback_data="timer:30"),
        InlineKeyboardButton(text="⏱️ 1 мин", callback_data="timer:60"),
        InlineKeyboardButton(text="⏱️ 2 мин", callback_data="timer:120")
    )
    builder.row(
        InlineKeyboardButton(text="⏱️ 5 мин", callback_data="timer:300"),
        InlineKeyboardButton(text="⏱️ 10 мин", callback_data="timer:600"),
        InlineKeyboardButton(text="⏱️ 15 мин", callback_data="timer:900")
    )
    builder.row(
        InlineKeyboardButton(text="🛑 Стоп", callback_data="timer_stop"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()
def get_exercises_keyboard(exercises: list, context: str = "workout") -> InlineKeyboardMarkup:
    """Клавиатура со списком упражнений"""
    builder = InlineKeyboardBuilder()
    
    for exercise in exercises:
        display_name = exercise.get('alias') or exercise.get('name')
        builder.row(
            InlineKeyboardButton(
                text=f"💪 {display_name}",
                callback_data=f"select_exercise_{context}:{exercise['name']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ НОВОЕ", callback_data=f"new_exercise_{context}"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_workout")
    )
    
    return builder.as_markup()