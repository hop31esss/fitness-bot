import csv
import logging
import os
from datetime import datetime
from typing import List, Dict
from database.base import db
from config import EXPORT_PATH

logger = logging.getLogger(__name__)

async def export_user_data(user_id: int) -> str:
    """Экспорт данных пользователя"""
    try:
        # Создаем директорию если нужно
        os.makedirs(EXPORT_PATH, exist_ok=True)
        logger.info(f"📁 Папка экспорта: {os.path.abspath(EXPORT_PATH)}")
        
        # Получаем данные пользователя
        workouts = await db.fetch_all("""
            SELECT ws.date, ws.start_time, we.exercise_name, we.sets, we.reps, we.weight
            FROM workout_sessions ws
            JOIN workout_exercises we ON ws.id = we.session_id
            WHERE ws.user_id = ?
            ORDER BY ws.date DESC, ws.start_time DESC
        """, (user_id,))
        
        logger.info(f"📊 Найдено тренировок: {len(workouts)}")
        
        exercises = await db.fetch_all(
            "SELECT * FROM exercises WHERE user_id = ?",
            (user_id,)
        )
        logger.info(f"📊 Найдено упражнений: {len(exercises)}")
        
        achievements = await db.fetch_all(
            "SELECT * FROM achievements WHERE user_id = ?",
            (user_id,)
        )
        logger.info(f"📊 Найдено достижений: {len(achievements)}")
        
        # Формируем имя файла
        filename = f"{EXPORT_PATH}/user_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        logger.info(f"📁 Создаем файл: {filename}")
        
        # Экспортируем в CSV
        await _export_to_csv(user_id, workouts, exercises, achievements, filename)
        
        # Проверяем, что файл создан
        if os.path.exists(filename):
            size = os.path.getsize(filename)
            logger.info(f"✅ Файл создан успешно! Размер: {size} байт")
        else:
            logger.error(f"❌ Файл НЕ создан: {filename}")
        
        return filename
    except Exception as e:
        logger.error(f"❌ Ошибка экспорта: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return ""

async def _export_to_csv(user_id: int, workouts: List[Dict], exercises: List[Dict], 
                        achievements: List[Dict], filename: str):
    """Экспорт в CSV"""
    with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
        writer = csv.writer(file)
        
        # Заголовок
        writer.writerow(['Экспорт данных FitnessBot'])
        writer.writerow([f'Пользователь ID: {user_id}'])
        writer.writerow([f'Дата экспорта: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}'])
        writer.writerow([])
        
        # Записываем тренировки
        writer.writerow(['=== ТРЕНИРОВКИ ==='])
        if workouts and 'date' in workouts[0]:  # Новая структура
            writer.writerow(['Дата', 'Время', 'Упражнение', 'Подходы', 'Повторения', 'Вес (кг)'])
            for workout in workouts:
                writer.writerow([
                    workout['date'],
                    workout['start_time'] or '',
                    workout['exercise_name'],
                    workout['sets'] or '',
                    workout['reps'] or '',
                    workout['weight'] or ''
                ])
        else:  # Старая структура
            writer.writerow(['Дата', 'Упражнение', 'Подходы', 'Повторения', 'Вес (кг)', 'Заметки'])
            for workout in workouts:
                writer.writerow([
                    workout['created_at'][:16] if workout.get('created_at') else '',
                    workout['exercise_name'],
                    workout['sets'],
                    workout['reps'],
                    workout['weight'] or '',
                    workout['notes'] or ''
                ])
        
        writer.writerow([])
        
        # Записываем упражнения
        writer.writerow(['=== УПРАЖНЕНИЯ ==='])
        writer.writerow(['Название', 'Алиас'])
        for exercise in exercises:
            writer.writerow([
                exercise['name'],
                exercise['alias'] or ''
            ])
        
        writer.writerow([])
        
        # Записываем ачивки
        writer.writerow(['=== ДОСТИЖЕНИЯ ==='])
        writer.writerow(['Тип', 'Название', 'Дата получения'])
        for achievement in achievements:
            writer.writerow([
                achievement['achievement_type'],
                achievement['achievement_name'],
                achievement['achieved_at'][:10] if achievement.get('achieved_at') else ''
            ])
    
    logger.info(f"✅ Экспорт завершен: {filename}")