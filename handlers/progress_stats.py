from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database.base import db

router = Router()

@router.callback_query(F.data == "progress_stats")
async def progress_stats_menu(callback: CallbackQuery):
    """Красивое меню прогресса"""
    user_id = callback.from_user.id
    
    # Получаем статистику
    stats = await db.fetch_one(
        "SELECT * FROM user_stats WHERE user_id = ?",
        (user_id,)
    )
    
    # Формируем текст
    if stats:
        text = (
            f"📈 *Ваш прогресс*\n\n"
            f"▫️ Всего тренировок: *{stats['total_workouts']}*\n"
            f"▫️ Текущая серия: *{stats['current_streak']} дней* 🔥\n"
            f"▫️ Лучшая серия: *{stats['longest_streak']} дней* 🏆\n"
            f"▫️ Уникальных упражнений: *{stats['total_exercises']}*\n"
        )
        
        if stats['last_workout_date']:
            last = stats['last_workout_date'][:10]
            text += f"▫️ Последняя тренировка: *{last}*\n"
    else:
        text = "📈 *Ваш прогресс*\n\nПока нет данных. Начните тренироваться! 💪"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 ДЕТАЛИ", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="📅 КАЛЕНДАРЬ", callback_data="calendar"),
        InlineKeyboardButton(text="🏆 ЛИДЕРЫ", callback_data="global_leaderboard")
    )
    builder.row(
        InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()