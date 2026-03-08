import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_sessions_table():
    conn = sqlite3.connect('fitness_bot.db')
    cursor = conn.cursor()
    
    # Таблица для сохранения состояния тренировки
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS active_workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            session_data TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("✅ Таблица active_workout_sessions создана")

if __name__ == "__main__":
    add_sessions_table()