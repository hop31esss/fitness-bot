import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_missing_tables():
    """Создание недостающих таблиц в базе данных"""
    conn = sqlite3.connect('fitness_bot.db')
    cursor = conn.cursor()
    
    # Таблица тренировок (сессий)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            start_time TIME,
            end_time TIME,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    logger.info("✅ Таблица workout_sessions создана или уже существует")
    
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
            pace TEXT,
            speed REAL,
            notes TEXT,
            order_num INTEGER,
            FOREIGN KEY (session_id) REFERENCES workout_sessions (id)
        )
    """)
    logger.info("✅ Таблица workout_exercises создана или уже существует")
    
    # Таблица платежей
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            currency TEXT NOT NULL,
            payload TEXT,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    logger.info("✅ Таблица payments создана или уже существует")
    
    conn.commit()
    conn.close()
    logger.info("🎉 Все недостающие таблицы созданы!")

if __name__ == "__main__":
    create_missing_tables()