import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from database.base import db

logger = logging.getLogger(__name__)

async def update_user_stats(user_id: int) -> None:
    """Обновление статистики пользователя"""
    try:
        # Считаем общее количество тренировок
        total_workouts = await db.fetch_one(
            "SELECT COUNT(*) as count FROM workouts WHERE user_id = ?",
            (user_id,)
        )
        
        # Считаем общее количество упражнений
        total_exercises = await db.fetch_one(
            "SELECT COUNT(DISTINCT exercise_name) as count FROM workouts WHERE user_id = ?",
            (user_id,)
        )
        
        # Получаем дату последней тренировки
        last_workout = await db.fetch_one(
            "SELECT created_at FROM workouts WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        
        # Вычисляем текущую серию (дни подряд)
        current_streak = await calculate_current_streak(user_id)
        
        # Получаем самую длинную серию
        longest_streak_record = await db.fetch_one(
            "SELECT longest_streak FROM user_stats WHERE user_id = ?",
            (user_id,)
        )
        longest_streak_value = longest_streak_record['longest_streak'] if longest_streak_record else 0
        
        # Обновляем самую длинную серию, если текущая больше
        if current_streak > longest_streak_value:
            longest_streak_value = current_streak
        
        # Обновляем или вставляем статистику
        await db.execute(
            """INSERT OR REPLACE INTO user_stats 
            (user_id, total_workouts, total_exercises, current_streak, longest_streak, last_workout_date) 
            VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, total_workouts['count'], total_exercises['count'], 
             current_streak, longest_streak_value, 
             last_workout['created_at'] if last_workout else None)
        )
        
    except Exception as e:
        logger.error(f"Error updating user stats for {user_id}: {e}")

async def calculate_current_streak(user_id: int) -> int:
    """Вычисление текущей серии тренировок (дней подряд)"""
    try:
        # Получаем даты тренировок за последние 30 дней
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=30)
        
        workouts = await db.fetch_all(
            """SELECT DISTINCT date(created_at) as workout_date 
            FROM workouts 
            WHERE user_id = ? AND date(created_at) BETWEEN ? AND ?
            ORDER BY workout_date DESC""",
            (user_id, start_date.isoformat(), end_date.isoformat())
        )
        
        if not workouts:
            return 0
        
        # Преобразуем в даты
        workout_dates = [datetime.strptime(w['workout_date'], '%Y-%m-%d').date() for w in workouts]
        
        # Проверяем последовательность дней
        streak = 0
        current_date = end_date
        
        for i in range(30):
            if current_date in workout_dates:
                streak += 1
                current_date -= timedelta(days=1)
            else:
                break
        
        return streak
    except Exception as e:
        logger.error(f"Error calculating streak for {user_id}: {e}")
        return 0

async def get_user_stats(user_id: int) -> Optional[Dict]:
    """Получение статистики пользователя"""
    return await db.fetch_one(
        "SELECT * FROM user_stats WHERE user_id = ?",
        (user_id,)
    )

async def get_workout_history(user_id: int, start_date: datetime, end_date: datetime) -> List[Dict]:
    """Получение истории тренировок за период"""
    return await db.fetch_all(
        """SELECT date(created_at) as date, COUNT(*) as workout_count, 
        SUM(sets * reps * COALESCE(weight, 1)) as total_volume
        FROM workouts 
        WHERE user_id = ? AND created_at BETWEEN ? AND ?
        GROUP BY date(created_at)
        ORDER BY date""",
        (user_id, start_date, end_date)
    )
async def get_user_achievements(user_id: int) -> List[Dict]:
    """Получение ачивок пользователя"""
    return await db.fetch_all(
        "SELECT * FROM achievements WHERE user_id = ? ORDER BY achieved_at DESC",
        (user_id,)
    )

async def check_achievements(user_id: int) -> None:
    """Проверка и выдача ачивок"""
    try:
        stats = await get_user_stats(user_id)
        if not stats:
            return
        
        achievements_to_check = [
            (1, "first_workout", "Первая тренировка"),
            (5, "five_workouts", "5 тренировок"),
            (10, "ten_workouts", "10 тренировок"),
            (30, "month_streak", "Серия из 30 дней"),
            (100, "hundred_workouts", "100 тренировок")
        ]
        
        for threshold, ach_type, ach_name in achievements_to_check:
            # Проверяем, есть ли уже такая ачивка
            existing = await db.fetch_one(
                "SELECT id FROM achievements WHERE user_id = ? AND achievement_type = ?",
                (user_id, ach_type)
            )
            
            if not existing:
                if ach_type == "first_workout" and stats['total_workouts'] >= 1:
                    await grant_achievement(user_id, ach_type, ach_name)
                elif ach_type == "five_workouts" and stats['total_workouts'] >= 5:
                    await grant_achievement(user_id, ach_type, ach_name)
                elif ach_type == "ten_workouts" and stats['total_workouts'] >= 10:
                    await grant_achievement(user_id, ach_type, ach_name)
                elif ach_type == "month_streak" and stats['longest_streak'] >= 30:
                    await grant_achievement(user_id, ach_type, ach_name)
                elif ach_type == "hundred_workouts" and stats['total_workouts'] >= 100:
                    await grant_achievement(user_id, ach_type, ach_name)
    except Exception as e:
        logger.error(f"Error checking achievements for {user_id}: {e}")

async def grant_achievement(user_id: int, achievement_type: str, achievement_name: str) -> None:
    """Выдача ачивки пользователю"""
    try:
        await db.execute(
            "INSERT INTO achievements (user_id, achievement_type, achievement_name) VALUES (?, ?, ?)",
            (user_id, achievement_type, achievement_name)
        )
        logger.info(f"Achievement granted: {user_id} - {achievement_name}")
    except Exception as e:
        logger.error(f"Error granting achievement: {e}")

async def get_current_streak(user_id: int) -> int:
    """Получение текущей серии тренировок"""
    stats = await get_user_stats(user_id)
    return stats['current_streak'] if stats else 0