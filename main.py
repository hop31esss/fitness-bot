import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
from database.base import init_db, close_db

# Импорт ВСЕХ роутеров
from handlers.start import router as start_router
from handlers.training import router as training_router
from handlers.profile import router as profile_router
from handlers.leaderboard import router as leaderboard_router
from handlers.achievements import router as achievements_router
from handlers.timer import router as timer_router
from handlers.stats import router as stats_router
from handlers.calendar import router as calendar_router
from handlers.exercises import router as exercises_router
from handlers.settings import router as settings_router
from handlers.recommendations import router as recommendations_router
from handlers.challenges import router as challenges_router
from handlers.features import router as features_router
from handlers.feed import router as feed_router
from handlers.daily_routine import router as daily_routine_router
from handlers.music import router as music_router
from handlers.friends import router as friends_router
from handlers.one_rep_max import router as one_rep_max_router
from handlers.calorie_tracker import router as calorie_tracker_router
from handlers.premium import router as premium_router
from handlers.admin_panel import router as admin_panel_router
from handlers.common import router as common_router
from handlers.payment import router as payment_router
from handlers.ai_advice import router as ai_advice_router
#from handlers.workout_session import router as workout_session_router

# Временно отключаем все мидлвари
# from middlewares.auth import AdminMiddleware
# from middlewares.subscription import SubscriptionMiddleware
# from middlewares.premium_check import PremiumCheckMiddleware

import sqlite3
import logging

# Синхронное создание таблиц (гарантированно работает)
def create_tables_sync():
    """Создание таблиц синхронно при старте"""
    conn = sqlite3.connect('fitness_bot.db')
    cursor = conn.cursor()
    
    # Таблица тренировок
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date DATE NOT NULL,
            start_time TIME,
            end_time TIME,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
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
            order_num INTEGER
        )
    """)
    
    conn.commit()
    conn.close()
    logging.info("✅ Таблицы созданы синхронно")

# Вызываем ДО инициализации бота
create_tables_sync()


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Инициализация базы данных
    await init_db()
    logger.info("База данных инициализирована")
    
    # Создаем недостающие таблицы
    from database.create_tables import create_missing_tables
    await asyncio.to_thread(create_missing_tables)
    logger.info("✅ Недостающие таблицы проверены")
    # Регистрация middleware (ВРЕМЕННО ОТКЛЮЧАЕМ)
    # if ADMIN_IDS:
    #     dp.message.middleware(AdminMiddleware(ADMIN_IDS))
    #     dp.callback_query.middleware(AdminMiddleware(ADMIN_IDS))
    
    # dp.message.middleware(SubscriptionMiddleware())
    # dp.callback_query.middleware(SubscriptionMiddleware())
    
    # dp.message.middleware(PremiumCheckMiddleware())
    # dp.callback_query.middleware(PremiumCheckMiddleware())
    
    # Регистрация ВСЕХ роутеров
    routers = [
        (start_router, "Стартовые команды"),
        (training_router, "Тренировки"),
        (profile_router, "Профиль"),
        (leaderboard_router, "Лидерборды"),
        (achievements_router, "Достижения"),
        (timer_router, "Таймер"),
        (stats_router, "Статистика"),
        (calendar_router, "Календарь"),
        (exercises_router, "Упражнения"),
        (settings_router, "Настройки"),
        (recommendations_router, "Рекомендации"),
        (challenges_router, "Челленджи"),
        (features_router, "Что умеет бот"),
        (feed_router, "Лента"),
        (daily_routine_router, "Режим дня"),
        (music_router, "Музыка"),
        (friends_router, "Друзья"),
        (one_rep_max_router, "1ПМ"),
        (calorie_tracker_router, "Калории"),
        (premium_router, "Премиум"),
        (admin_panel_router, "Админ-панель"),
        (payment_router, "Платежи"),
        (ai_advice_router, "AI-советы"),
        #(workout_session_router, "Тренировочные сессии"),
        (common_router, "Общие обработчики"),
    ]
    
    for router, name in routers:
        try:
            dp.include_router(router)
            logger.info(f"✅ Роутер '{name}' зарегистрирован")
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации роутера '{name}': {e}")
    
    logger.info("✅ Все роутеры зарегистрированы, бот запускается...")
    
    # Запуск бота
    try:
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")
    finally:
        await close_db()
        await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == "__main__":
    asyncio.run(main())