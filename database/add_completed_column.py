import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_completed_column():
    """Добавляет колонку completed в таблицу workout_exercises"""
    try:
        conn = sqlite3.connect('fitness_bot.db')
        cursor = conn.cursor()
        
        # Проверяем, есть ли уже такая колонка
        cursor.execute("PRAGMA table_info(workout_exercises)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'completed' not in columns:
            # Добавляем колонку
            cursor.execute("ALTER TABLE workout_exercises ADD COLUMN completed BOOLEAN DEFAULT FALSE")
            logger.info("✅ Колонка 'completed' добавлена в таблицу workout_exercises")
        else:
            logger.info("ℹ️ Колонка 'completed' уже существует")
        
        conn.commit()
        conn.close()
        
        # Проверяем результат
        conn = sqlite3.connect('fitness_bot.db')
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(workout_exercises)")
        columns = cursor.fetchall()
        logger.info("📊 Структура таблицы workout_exercises:")
        for col in columns:
            logger.info(f"   {col[1]} - {col[2]}")
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    add_completed_column()