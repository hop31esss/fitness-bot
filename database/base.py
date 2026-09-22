import os
import json
import logging
from typing import List, Tuple, Optional

import aiosqlite

from config import DATABASE_URL
from database.exercise_catalog import EXERCISE_MUSCLE_CATALOG

logger = logging.getLogger(__name__)

MUSCLE_CATALOG = (
    ("chest", "Грудь", ("грудные", "грудь", "chest", "pecs", "pectorals")),
    ("back", "Спина", ("спина", "широчайшие", "трапеции", "back", "lats", "traps")),
    ("shoulders", "Плечи", ("плечи", "дельты", "дельтовидные", "shoulders", "delts")),
    ("biceps", "Бицепс", ("бицепс", "biceps", "bicep")),
    ("triceps", "Трицепс", ("трицепс", "triceps", "tricep")),
    ("forearms", "Предплечья", ("предплечья", "предплечье", "forearms", "forearm")),
    ("quadriceps", "Квадрицепс", ("квадрицепс", "квадрицепсы", "quadriceps", "quads")),
    ("hamstrings", "Бицепс бедра", ("бицепс бедра", "задняя поверхность бедра", "hamstrings")),
    ("glutes", "Ягодицы", ("ягодицы", "ягодичные", "glutes", "gluteus")),
    ("calves", "Икры", ("икры", "икроножные", "calves", "calf")),
    ("core", "Кор", ("кор", "пресс", "мышцы кора", "core", "abs", "abdominals")),
    ("undefined", "Не определено", ("не определено", "другое", "unknown", "undefined", "other")),
)


def canonical_muscle_slug(value: str) -> str:
    """Resolve common Russian/English muscle aliases to a stable slug."""
    normalized = " ".join((value or "").strip().casefold().replace("ё", "е").split())
    for slug, name, aliases in MUSCLE_CATALOG:
        candidates = (slug, name, *aliases)
        if normalized in {
            " ".join(candidate.casefold().replace("ё", "е").split())
            for candidate in candidates
        }:
            return slug
    return "undefined"


def sqlite_path_from_url(url: str) -> str:
    """Extract a filesystem path from a sqlite / aiosqlite URL."""
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            return url[len(prefix):]
    return url


class Database:
    def __init__(self):
        self.db_path = sqlite_path_from_url(DATABASE_URL)
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self):
        """Установка соединения с БД"""
        parent = os.path.dirname(self.db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        self.conn = await aiosqlite.connect(self.db_path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")
        await self.conn.execute("PRAGMA journal_mode = WAL")
        logger.info("Database connection established")

    async def close(self):
        """Закрытие соединения с БД"""
        if self.conn:
            await self.conn.close()
            logger.info("Database connection closed")

    async def execute(self, query: str, params: Tuple = (), *, commit: bool = True) -> aiosqlite.Cursor:
        """Выполнение запроса. SELECT должен вызывать с commit=False."""
        if not self.conn:
            await self.connect()
        cursor = await self.conn.execute(query, params)
        if commit:
            await self.conn.commit()
        return cursor

    async def fetch_one(self, query: str, params: Tuple = ()) -> Optional[dict]:
        """Получение одной записи"""
        cursor = await self.execute(query, params, commit=False)
        result = await cursor.fetchone()
        await cursor.close()
        return dict(result) if result else None

    async def fetch_all(self, query: str, params: Tuple = ()) -> List[dict]:
        """Получение всех записей"""
        cursor = await self.execute(query, params, commit=False)
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
            last_reminder_date TEXT,
            last_weekly_stats_date TEXT,
            weekly_workout_goal INTEGER NOT NULL DEFAULT 3,
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

    # Таблица реферальных кодов
    await db.execute("""
        CREATE TABLE IF NOT EXISTS referral_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("✅ Таблица referral_codes создана")

    # Таблицы сессий тренировок (факт выполнения и planned/actual)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            start_time TEXT,
            end_time TEXT,
            notes TEXT,
            template_id INTEGER,
            source_table TEXT,
            source_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS workout_exercises (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            exercise_name TEXT NOT NULL,
            exercise_type TEXT DEFAULT 'strength',
            sets INTEGER,
            reps INTEGER,
            weight REAL,
            planned_sets INTEGER,
            planned_reps INTEGER,
            planned_weight REAL,
            duration INTEGER,
            distance REAL,
            notes TEXT,
            order_num INTEGER,
            completed BOOLEAN DEFAULT FALSE,
            source_table TEXT,
            source_id TEXT,
            FOREIGN KEY (session_id) REFERENCES workout_sessions (id) ON DELETE CASCADE
        )
    """)
    logger.info("✅ Таблицы workout_sessions/workout_exercises созданы")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS workout_sets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workout_exercise_id INTEGER NOT NULL,
            set_number INTEGER NOT NULL,
            reps INTEGER NOT NULL DEFAULT 0,
            weight REAL NOT NULL DEFAULT 0,
            completed BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (workout_exercise_id)
                REFERENCES workout_exercises (id) ON DELETE CASCADE,
            UNIQUE(workout_exercise_id, set_number)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS muscles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL UNIQUE,
            aliases TEXT NOT NULL DEFAULT '[]',
            is_fallback BOOLEAN NOT NULL DEFAULT FALSE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS exercise_muscles (
            exercise_name TEXT NOT NULL COLLATE NOCASE,
            muscle_id INTEGER NOT NULL,
            contribution REAL NOT NULL DEFAULT 1.0,
            source TEXT NOT NULL DEFAULT 'user',
            PRIMARY KEY (exercise_name, muscle_id),
            FOREIGN KEY (muscle_id) REFERENCES muscles (id) ON DELETE CASCADE
        )
    """)
    for slug, name, aliases in MUSCLE_CATALOG:
        await db.execute(
            """
            INSERT INTO muscles (slug, name, aliases, is_fallback)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name = excluded.name,
                aliases = excluded.aliases,
                is_fallback = excluded.is_fallback
            """,
            (slug, name, json.dumps(aliases, ensure_ascii=False), slug == "undefined"),
        )
    await seed_exercise_muscle_catalog()

    await db.execute("""
        CREATE TABLE IF NOT EXISTS referrals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            referrer_id INTEGER NOT NULL,
            referred_id INTEGER UNIQUE NOT NULL,
            code TEXT NOT NULL,
            reward_granted_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("✅ Таблица referrals создана")

    await db.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            provider_payment_id TEXT NOT NULL UNIQUE,
            amount INTEGER,
            currency TEXT,
            status TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    logger.info("✅ Таблица payments создана")

    # Идемпотентные миграции колонок (после CREATE всех таблиц)
    migration_queries = [
        "ALTER TABLE workout_sessions ADD COLUMN template_id INTEGER",
        "ALTER TABLE workout_exercises ADD COLUMN completed BOOLEAN DEFAULT FALSE",
        "ALTER TABLE workout_exercises ADD COLUMN planned_sets INTEGER",
        "ALTER TABLE workout_exercises ADD COLUMN planned_reps INTEGER",
        "ALTER TABLE workout_exercises ADD COLUMN planned_weight REAL",
        "ALTER TABLE workout_sessions ADD COLUMN source_table TEXT",
        "ALTER TABLE workout_sessions ADD COLUMN source_id TEXT",
        "ALTER TABLE workout_exercises ADD COLUMN source_table TEXT",
        "ALTER TABLE workout_exercises ADD COLUMN source_id TEXT",
        "ALTER TABLE user_settings ADD COLUMN weekly_workout_goal INTEGER NOT NULL DEFAULT 3",
        "ALTER TABLE user_settings ADD COLUMN last_reminder_date TEXT",
        "ALTER TABLE user_settings ADD COLUMN last_weekly_stats_date TEXT",
        "ALTER TABLE users ADD COLUMN pro_banner_shown_after_progress INTEGER DEFAULT 0",
        "ALTER TABLE users ADD COLUMN pro_workout_milestone_prompt_shown INTEGER DEFAULT 0",
        "ALTER TABLE referrals ADD COLUMN reward_granted_at TIMESTAMP",
    ]
    for query in migration_queries:
        try:
            await db.execute(query)
        except Exception as exc:
            text = str(exc).lower()
            if (
                "duplicate column name" not in text
                and "already exists" not in text
                and "no such table" not in text
            ):
                raise
    
    # Индексы для оптимизации
    await db.execute("CREATE INDEX IF NOT EXISTS idx_workouts_user_date ON workouts(user_id, created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(created_at)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_achievements_user ON achievements(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_user_settings_user ON user_settings(user_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_friends_user ON friends(user_id, status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_friends_friend ON friends(friend_id, status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_challenges_users ON challenges(user1_id, user2_id, status)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_workout_sessions_user_date ON workout_sessions(user_id, date)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_workout_exercises_session ON workout_exercises(session_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_workout_sets_exercise ON workout_sets(workout_exercise_id)")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_exercise_muscles_muscle ON exercise_muscles(muscle_id)")
    await db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_workout_sessions_source
        ON workout_sessions(source_table, source_id)
        WHERE source_table IS NOT NULL AND source_id IS NOT NULL
        """
    )
    await db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_workout_exercises_source
        ON workout_exercises(source_table, source_id)
        WHERE source_table IS NOT NULL AND source_id IS NOT NULL
        """
    )

    await migrate_legacy_workouts()
    await db.execute(
        """
        DELETE FROM workout_sessions
        WHERE id NOT IN (SELECT DISTINCT session_id FROM workout_exercises)
          AND id NOT IN (
            SELECT CAST(json_extract(session_data, '$.session_id') AS INTEGER)
            FROM active_workout_sessions
            WHERE json_extract(session_data, '$.session_id') IS NOT NULL
          )
        """
    )
    try:
        await db.execute(
            """
            UPDATE workout_exercises
            SET reps = CAST(ROUND(reps) AS INTEGER)
            WHERE reps IS NOT NULL
            """
        )
    except Exception:
        logger.debug("Could not normalize workout_exercises.reps")
    
    logger.info("✅ Все индексы созданы")
    logger.info("🎉 База данных полностью инициализирована!")


async def migrate_legacy_workouts() -> None:
    """Copy each legacy workout once, preserving its source identity."""
    if not db.conn:
        await db.connect()
    conn = db.conn
    await conn.execute("BEGIN IMMEDIATE")
    try:
        cursor = await conn.execute(
            """
            SELECT id, user_id, exercise_name, sets, reps, weight, duration,
                   notes, created_at
            FROM workouts
            ORDER BY id
            """
        )
        rows = await cursor.fetchall()
        await cursor.close()
        for row in rows:
            source_id = str(row["id"])
            cursor = await conn.execute(
                """
                INSERT OR IGNORE INTO workout_sessions
                    (user_id, date, start_time, end_time, notes,
                     source_table, source_id, created_at)
                VALUES (?, COALESCE(date(?), date('now')), time(?), time(?), ?,
                        'workouts', ?, COALESCE(?, CURRENT_TIMESTAMP))
                """,
                (
                    row["user_id"], row["created_at"], row["created_at"],
                    row["created_at"], row["notes"], source_id, row["created_at"],
                ),
            )
            if cursor.rowcount:
                session_id = cursor.lastrowid
            else:
                existing = await conn.execute(
                    """
                    SELECT id FROM workout_sessions
                    WHERE source_table = 'workouts' AND source_id = ?
                    """,
                    (source_id,),
                )
                found = await existing.fetchone()
                await existing.close()
                session_id = found["id"]

            sets = max(0, int(row["sets"] or 0))
            reps = max(0, int(row["reps"] or 0))
            weight = max(0.0, float(row["weight"] or 0))
            await conn.execute(
                """
                INSERT OR IGNORE INTO workout_exercises
                    (session_id, exercise_name, exercise_type, sets, reps,
                     weight, duration, notes, order_num, completed,
                     source_table, source_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, TRUE, 'workouts', ?)
                """,
                (
                    session_id, row["exercise_name"],
                    "cardio" if row["duration"] and not sets else "strength",
                    sets, reps, weight, row["duration"], row["notes"], source_id,
                ),
            )
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise


async def seed_exercise_muscle_catalog() -> None:
    """Idempotently attach catalog aliases to muscle rows."""
    muscles = await db.fetch_all("SELECT id, slug FROM muscles")
    slug_to_id = {row["slug"]: row["id"] for row in muscles}
    fallback_id = slug_to_id.get("undefined")
    for aliases, parts in EXERCISE_MUSCLE_CATALOG:
        for alias in aliases:
            name = " ".join(alias.strip().split())
            if not name:
                continue
            for slug, contribution in parts:
                muscle_id = slug_to_id.get(slug) or fallback_id
                if muscle_id is None:
                    continue
                await db.execute(
                    """
                    INSERT INTO exercise_muscles
                        (exercise_name, muscle_id, contribution, source)
                    VALUES (?, ?, ?, 'catalog')
                    ON CONFLICT(exercise_name, muscle_id) DO UPDATE SET
                        contribution = excluded.contribution
                    WHERE exercise_muscles.source = 'catalog'
                    """,
                    (name, muscle_id, contribution),
                )
