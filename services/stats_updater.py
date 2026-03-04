from datetime import datetime
import logging
from database.base import db

logger = logging.getLogger(__name__)

async def update_user_stats(user_id: int):
    """Обновляет статистику пользователя после тренировки"""
    try:
        # Получаем все тренировки пользователя
        sessions = await db.fetch_all(
            "SELECT COUNT(*) as session_count FROM workout_sessions WHERE user_id = ?",
            (user_id,)
        )
        total_workouts = sessions[0]['session_count'] if sessions else 0
        
        # Получаем уникальные упражнения
        exercises = await db.fetch_one(
            "SELECT COUNT(DISTINCT exercise_name) as count FROM workout_exercises we "
            "JOIN workout_sessions ws ON we.session_id = ws.id "
            "WHERE ws.user_id = ?",
            (user_id,)
        )
        total_exercises = exercises['count'] if exercises else 0
        
        # Получаем последнюю тренировку
        last = await db.fetch_one(
            "SELECT date FROM workout_sessions WHERE user_id = ? ORDER BY date DESC LIMIT 1",
            (user_id,)
        )
        last_date = last['date'] if last else None
        
        # Рассчитываем серию (упрощенно)
        current_streak = 1 if last_date else 0
        longest_streak = 1 if last_date else 0
        
        # Сохраняем или обновляем статистику
        await db.execute("""
            INSERT OR REPLACE INTO user_stats 
            (user_id, total_workouts, total_exercises, current_streak, longest_streak, last_workout_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, total_workouts, total_exercises, current_streak, longest_streak, last_date))
        
        logger.info(f"✅ Статистика обновлена для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка обновления статистики: {e}")