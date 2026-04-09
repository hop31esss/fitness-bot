from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database.base import db

router = Router()

@router.callback_query(F.data == "feed")
async def show_feed(callback: CallbackQuery):
    """Лента активности - показывает последние тренировки пользователей"""
    
    # Получаем последние 20 тренировок из новой системы workout_sessions
    activities = await db.fetch_all("""
        SELECT 
            u.first_name,
            u.username,
            ws.date,
            ws.start_time,
            COUNT(we.id) as exercises_count,
            SUM(we.sets * we.reps * COALESCE(we.weight, 1)) as total_volume
        FROM workout_sessions ws
        JOIN users u ON ws.user_id = u.user_id
        LEFT JOIN workout_exercises we ON ws.id = we.session_id
        GROUP BY ws.id
        ORDER BY ws.date DESC, ws.start_time DESC
        LIMIT 20
    """)
    
    if activities:
        text = "📰 *Лента активности*\n\n"
        text += "*Последние тренировки:*\n\n"
        
        for activity in activities:
            # Имя пользователя
            name = activity['first_name'] or activity['username'] or 'Пользователь'
            
            # Дата и время
            date_obj = datetime.strptime(activity['date'], '%Y-%m-%d')
            date_str = date_obj.strftime('%d.%m')
            time_str = activity['start_time'] or '??:??'
            
            # Статистика тренировки
            exercises = activity['exercises_count'] or 0
            volume = int(activity['total_volume'] or 0)
            
            text += f"👤 *{name}*\n"
            text += f"📅 {date_str} в {time_str} | {exercises} упр | {volume:,} кг\n\n"
    else:
        text = "📰 *Лента активности*\n\nПока нет активностей. Будьте первыми! 💪"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 ОБНОВИТЬ", callback_data="feed"),
        InlineKeyboardButton(text="➕ ДОБАВИТЬ ТРЕНИРОВКУ", callback_data="start_workout")
    )
    builder.row(
        InlineKeyboardButton(text="🏆 ЛИДЕРБОРД", callback_data="global_leaderboard"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()