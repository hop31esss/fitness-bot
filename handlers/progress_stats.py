from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import logging

from database.base import db

router = Router()
logger = logging.getLogger(__name__)

@router.callback_query(F.data == "progress_stats")
async def progress_stats_menu(callback: CallbackQuery):
    """Меню прогресса и статистики"""
    user_id = callback.from_user.id
    
    try:
        # Получаем общую статистику
        stats = await db.fetch_one(
            "SELECT * FROM user_stats WHERE user_id = ?",
            (user_id,)
        )
        
        # Получаем количество тренировок
        # Считаем тренировки из новой системы (сессии)
        total_sessions = await db.fetch_one(
            "SELECT COUNT(*) as count FROM workout_sessions WHERE user_id = ?",
            (user_id,)
        )
        total_workouts = total_sessions['count'] if total_sessions else 0
        
        if stats:
            text = (
                f"📈 *Ваш прогресс*\n\n"
                f"▫️ Всего тренировок: *{total_workouts['count'] if total_workouts else 0}*\n"
                f"▫️ Текущая серия: *{stats['current_streak']} дней* 🔥\n"
                f"▫️ Лучшая серия: *{stats['longest_streak']} дней* 🏆\n"
            )
            
            if stats['last_workout_date']:
                last = stats['last_workout_date'][:10]
                text += f"▫️ Последняя тренировка: *{last}*\n"
        else:
            text = "📈 *Ваш прогресс*\n\nПока нет данных. Начните тренироваться! 💪"
        
        # Клавиатура с кнопкой графиков
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats"),
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
        
    except Exception as e:
        logger.error(f"Ошибка в progress_stats: {e}")
        await callback.message.answer("❌ Ошибка загрузки статистики")
    
    await callback.answer()