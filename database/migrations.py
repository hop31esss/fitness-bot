import logging
from database.base import db

logger = logging.getLogger(__name__)

async def migrate_database():
    """Миграция базы данных - добавление недостающих таблиц"""
    try:
        # Проверяем существование таблицы user_settings
        check = await db.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_settings'"
        )
        
        if not check:
            # Создаем таблицу user_settings
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    units TEXT DEFAULT 'kg',
                    notifications_enabled BOOLEAN DEFAULT FALSE,
                    notification_time TEXT DEFAULT '18:00',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (user_id)
                )
            """)
            logger.info("✅ Таблица user_settings создана")
            
        # Проверяем другие таблицы
        tables_to_check = ['users', 'workouts', 'exercises', 'achievements', 'user_stats']
        
        for table in tables_to_check:
            exists = await db.fetch_one(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            if not exists:
                logger.warning(f"⚠️ Таблица {table} не существует")
                
        logger.info("✅ Миграция базы данных завершена")
        
    except Exception as e:
        logger.error(f"❌ Ошибка миграции базы данных: {e}")