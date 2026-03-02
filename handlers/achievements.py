from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db
from services.analytics import get_user_achievements, get_current_streak

router = Router()

@router.callback_query(F.data == "achievements")
async def achievements_menu(callback: CallbackQuery):
    """Меню ачивок и серий"""
    user_id = callback.from_user.id
    
    # Получаем ачивки пользователя
    achievements = await get_user_achievements(user_id)
    current_streak = await get_current_streak(user_id)
    
    text = f"🏅 Ваши достижения\n\n"
    text += f"🔥 Текущая серия: {current_streak} дней\n\n"
    
    if achievements:
        text += "Ваши ачивки:\n"
        for ach in achievements:
            text += f"• {ach['achievement_name']}\n"
    else:
        text += "У вас пока нет ачивок. Продолжайте тренироваться!"
    
    keyboard = get_achievements_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "streaks")
async def show_streaks(callback: CallbackQuery):
    """Показать серии тренировок"""
    user_id = callback.from_user.id
    
    stats = await db.fetch_one(
        "SELECT current_streak, longest_streak FROM user_stats WHERE user_id = ?",
        (user_id,)
    )
    
    if stats:
        text = (
            f"🔥 *Ваши серии тренировок:*\n\n"
            f"📅 Текущая серия: {stats['current_streak']} дней\n"
            f"🏆 Самая длинная серия: {stats['longest_streak']} дней\n\n"
            f"Продолжайте в том же духе! 💪"
        )
    else:
        text = "У вас пока нет данных о сериях тренировок."
    
    await callback.message.edit_text(text, reply_markup=get_back_to_achievements_keyboard())
    await callback.answer()

def get_achievements_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура достижений"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🔥 Серии", callback_data="streaks"),
        InlineKeyboardButton(text="🏆 Ачивки", callback_data="achievements_list")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_back_to_achievements_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата к достижениям"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data="achievements"))
    return builder.as_markup()