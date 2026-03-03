from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import logging

from database.base import db
from config import ADMIN_ID

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "progress_stats")
async def progress_stats_menu(callback: CallbackQuery):
    """Меню прогресса и статистики"""
    user_id = callback.from_user.id
    
    # Получаем общую статистику
    stats = await db.fetch_one(
        "SELECT * FROM user_stats WHERE user_id = ?",
        (user_id,)
    )
    
    # Получаем данные за последние 30 дней
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    workouts = await db.fetch_all("""
        SELECT date(created_at) as date, 
               COUNT(*) as count,
               SUM(sets * reps * COALESCE(weight, 1)) as volume
        FROM workouts 
        WHERE user_id = ? AND created_at BETWEEN ? AND ?
        GROUP BY date(created_at)
        ORDER BY date
    """, (user_id, start_date, end_date))
    
    # Текстовая статистика
    if stats:
        total_workouts = stats['total_workouts']
        current_streak = stats['current_streak']
        longest_streak = stats['longest_streak']
        total_exercises = stats['total_exercises']
        
        if stats['last_workout_date']:
            last = stats['last_workout_date'][:10]
            last_text = f"▫️ Последняя тренировка: *{last}*\n"
        else:
            last_text = ""
        
        text = (
            f"📈 *Ваш прогресс*\n\n"
            f"▫️ Всего тренировок: *{total_workouts}*\n"
            f"▫️ Текущая серия: *{current_streak} дней* 🔥\n"
            f"▫️ Лучшая серия: *{longest_streak} дней* 🏆\n"
            f"▫️ Уникальных упражнений: *{total_exercises}*\n"
            f"{last_text}"
        )
        
        # Добавляем данные за 30 дней
        if workouts:
            total_volume = sum(w['volume'] or 0 for w in workouts)
            avg_volume = total_volume / len(workouts) if workouts else 0
            text += f"\n📊 *За последние 30 дней:*\n"
            text += f"▫️ Тренировок: *{len(workouts)}*\n"
            text += f"▫️ Общий объем: *{total_volume:,.0f} кг*\n"
            text += f"▫️ Средний объем: *{avg_volume:,.0f} кг/день*\n"
    else:
        text = "📈 *Ваш прогресс*\n\nПока нет данных. Начните тренироваться! 💪"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 ДЕТАЛЬНАЯ СТАТИСТИКА", callback_data="stats"),
        InlineKeyboardButton(text="📊 ГРАФИКИ", callback_data="progress_charts")
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