import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_database():
    """Принудительное создание всех недостающих таблиц"""
    conn = sqlite3.connect('fitness_bot.db')
    cursor = conn.cursor()
    
    # Таблица тренировок (сессий)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("✅ Таблица workout_sessions создана/проверена")
    
    # Таблица упражнений в тренировке
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            exercise_type TEXT DEFAULT 'strength',
            sets INTEGER,
            reps INTEGER,
            weight REAL,
            duration INTEGER,
            distance REAL,
            notes TEXT,
            order_num INTEGER
        )
    """)
    logger.info("✅ Таблица workout_exercises создана/проверена")
    
    # Проверяем существование таблиц
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    logger.info(f"📊 Таблицы в базе: {[t[0] for t in tables]}")
    
    conn.commit()
    conn.close()
    logger.info("🎉 База данных готова!")

if __name__ == "__main__":
    fix_database()