import sqlite3
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_subscription_field():
    """Добавление поля subscription_until в таблицу users"""
    conn = sqlite3.connect('fitness_bot.db')
    cursor = conn.cursor()
    
    try:
        # Проверяем, есть ли уже такое поле
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'subscription_until' not in columns:
            # Добавляем поле
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_until TIMESTAMP")
            logger.info("✅ Поле subscription_until добавлено в таблицу users")
        else:
            logger.info("ℹ️ Поле subscription_until уже существует")
        
        conn.commit()
        
        # Показываем обновленную структуру
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        print("\n📊 Обновленная структура таблицы users:")
        for col in columns:
            print(f"   {col[1]} - {col[2]}")
            
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_subscription_field()