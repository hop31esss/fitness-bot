import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_completed_column():
    """Принудительное добавление колонки completed"""
    try:
        conn = sqlite3.connect('fitness_bot.db')
        cursor = conn.cursor()
        
        # Проверяем существование колонки
        cursor.execute("PRAGMA table_info(workout_exercises)")
        columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"Текущие колонки: {columns}")
        
        if 'completed' not in columns:
            # Добавляем колонку
            cursor.execute("ALTER TABLE workout_exercises ADD COLUMN completed BOOLEAN DEFAULT FALSE")
            conn.commit()
            logger.info("✅ Колонка 'completed' добавлена")
        else:
            logger.info("✅ Колонка 'completed' уже существует")
        
        # Проверяем результат
        cursor.execute("PRAGMA table_info(workout_exercises)")
        new_columns = [col[1] for col in cursor.fetchall()]
        logger.info(f"Новые колонки: {new_columns}")
        
        conn.close()
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    fix_completed_column()