import aiosqlite
import logging
from typing import List, Tuple, Any, Optional
from config import DATABASE_URL

logger = logging.getLogger(__name__)

class Database:
    def __init__(self):
        self.db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Установка соединения с БД"""
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        logger.info("Database connection established")

    async def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")

    async def execute(self, query: str, params: Tuple = ()) -> aiosqlite.Cursor:
        """Выполнение запроса"""
        if not self.conn:
            await self.connect()
        cursor = await self.conn.execute(query, params)
        await self.conn.commit()
        return cursor

    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[dict]:
        """Получение одной записи"""
        cursor = await self.execute(query, params)
        result = await cursor.fetchone()
        await cursor.close()
        return dict(result) if result else None

    async def fetch_all(self, query: str, params: Tuple = ()) -> List[dict]:
        """Получение всех записей"""
        cursor = await self.execute(query, params)
        results = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in results]

    async def execute_many(self, query: str, params: List[Tuple]) -> None:
        """Массовое выполнение запросов"""
        if not self.conn:
            await self.connect()
        await self.conn.executemany(query, params)
        await self.conn.commit()

# Глобальный экземпляр БД
db = Database()

async def init_db():
    """Инициализация базы данных"""
    await db.connect()
    await create_tables()
    logger.info("База данных инициализирована")

async def close_db():
    """Закрытие соединения с БД"""
    await db.close()

async def create_tables():
    """Создание таблиц"""

# Таблица для сохранения активных тренировок
    await db.execute("""
        CREATE TABLE IF NOT EXISTS active_workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            session_data TEXT NOT NULL,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("✅ Таблица active_workout_sessions создана")

    # Таблица пользователей
    await db.execute("""
       CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_subscribed BOOLEAN DEFAULT FALSE,
            is_admin BOOLEAN DEFAULT FALSE,
            subscription_until TIMESTAMP
        )
    """,)
    logger.info("✅ Таблица users создана")
    
    # Таблица настроек пользователя
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
    
    # Таблица тренировок
    await db.execute("""
        CREATE TABLE IF NOT EXISTS workouts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            sets INTEGER NOT NULL,
            reps INTEGER NOT NULL,
            weight REAL,
            duration INTEGER,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    logger.info("✅ Таблица workouts создана")
    
    # Таблица упражнений
    await db.execute("""
        CREATE TABLE IF NOT EXISTS exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            alias TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    logger.info("✅ Таблица exercises создана")
    
    # Таблица достижений
    await db.execute("""
        CREATE TABLE IF NOT EXISTS achievements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            achievement_type TEXT NOT NULL,
            achievement_name TEXT NOT NULL,
            achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    logger.info("✅ Таблица achievements создана")
    
    # Таблица статистики пользователей
    await db.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            total_workouts INTEGER DEFAULT 0,
            total_exercises INTEGER DEFAULT 0,
            current_streak INTEGER DEFAULT 0,
            longest_streak INTEGER DEFAULT 0,
            last_workout_date TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    logger.info("✅ Таблица user_stats создана")
    
    # ТАБЛИЦА ДРУЗЕЙ 
    await db.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id),
            FOREIGN KEY (friend_id) REFERENCES users (user_id),
            UNIQUE(user_id, friend_id)
        )
    """)
    logger.info("✅ Таблица friends создана")
    
    # Таблица челленджей
    await db.execute("""
        CREATE TABLE IF NOT EXISTS challenges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            exercise TEXT,
            goal INTEGER NOT NULL,
            unit TEXT DEFAULT 'тренировок',
            user1_progress INTEGER DEFAULT 0,
            user2_progress INTEGER DEFAULT 0,
            winner_id INTEGER,
            status TEXT DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            end_date TIMESTAMP,
            FOREIGN KEY (user1_id) REFERENCES users (user_id),
            FOREIGN KEY (user2_id) REFERENCES users (user_id)
        )
    """)
    logger.info("✅ Таблица challenges создана")

    # Таблица для норм калорий
    await db.execute("""
        CREATE TABLE IF NOT EXISTS calorie_norms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            calories INTEGER NOT NULL,
            protein INTEGER NOT NULL,
            fat INTEGER NOT NULL,
            carbs INTEGER NOT NULL,
            bmr INTEGER,
            tdee INTEGER,
            goal TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """)
    logger.info("✅ Таблица calorie tracker создана")

# Таблица для записей еды
    await db.execute("""
        CREATE TABLE IF NOT EXISTS food_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            food_name TEXT NOT NULL,
            amount REAL NOT NULL,
            unit TEXT,
            calories INTEGER NOT NULL,
            protein REAL,
            fat REAL,
            carbs REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    """,)
    logger.info("✅ Таблица food создана")

     # Таблица шаблонов тренировок
    await db.execute("""
    CREATE TABLE IF NOT EXISTS workout_templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        exercises TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    logger.info("✅ Таблица workout_templates создана")
    
    # Индексы для оптимизации
    await db.execute("CREATE INDEX IF NOT EXISTS idx_workouts_user_date ON workouts(user_id, created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_achievements_user ON achievements(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_user_settings_user ON user_settings(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_friends_user ON friends(user_id, status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_friends_friend ON friends(friend_id, status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_challenges_users ON challenges(user1_id, user2_id, status)")
    
    logger.info("✅ Все индексы созданы")
    logger.info("🎉 База данных полностью инициализирована!")