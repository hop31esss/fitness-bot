import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_payments_table():
    """Добавление таблицы для хранения платежей"""
    conn = sqlite3.connect('fitness_bot.db')
    cursor = conn.cursor()
    
    try:
        # Создаем таблицу payments
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
        
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_payments_table()