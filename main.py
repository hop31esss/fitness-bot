import asyncio
import logging
import sqlite3
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton
from config import BOT_TOKEN, ADMIN_IDS
from aiogram.types import Message
from database.base import init_db, close_db

# --- ИМПОРТЫ РОУТЕРОВ  ---
from handlers.start import router as start_router
from handlers.profile import router as profile_router
from handlers.leaderboard import router as leaderboard_router
from handlers.achievements import router as achievements_router
from handlers.timer import router as timer_router
from handlers.calendar import router as calendar_router
from handlers.settings import router as settings_router
from handlers.premium import router as premium_router
from handlers.common import router as common_router
from handlers.training import router as training_router
from handlers.progress_charts import router as charts_router
from handlers.one_rep_max import router as one_rep_max_router
from handlers.calorie_tracker import router as calorie_tracker_router
from handlers.friends import router as friends_router
from handlers.ai_advice import router as ai_advice_router
from handlers.workout_journal import router as journal_router
from handlers.payment import router as payment_router
from handlers.exercises import router as exercises_router
from handlers.recommendations import router as recommendations_router
from handlers.challenges import router as challenges_router
from handlers.feed import router as feed_router
from handlers.daily_routine import router as daily_routine_router
from handlers.workout_templates import router as templates_router
#from handlers.music import router as music_router
from handlers.workout_session import router as workout_session_router
from handlers.progress_stats import router as progress_stats_router
from handlers.admin_panel import router as admin_panel_router


# --- НАСТРОЙКА ЛОГИРОВАНИЯ ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ ТАБЛИЦЫ ШАБЛОНОВ ===
def create_templates_table():
    """Принудительное создание таблицы workout_templates"""
    try:
        import sqlite3
        import os
        
        db_path = 'fitness_bot.db'
        print(f"🔧 Создание таблицы workout_templates в {os.path.abspath(db_path)}")
        
        # Проверяем права на запись
        if os.path.exists(db_path):
            print(f"✅ Файл БД существует, права: {oct(os.stat(db_path).st_mode)[-3:]}")
        else:
            print(f"⚠️ Файл БД не существует, будет создан")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Включаем внешние ключи (на всякий случай)
        cursor.execute("PRAGMA foreign_keys = ON")
        
        # Создаём таблицу
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                exercises TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        # Проверяем
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workout_templates'")
        if cursor.fetchone():
            print("✅ Таблица workout_templates успешно создана")
        else:
            print("❌ Таблица НЕ создалась")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

# === ФУНКЦИЯ СОЗДАНИЯ ТАБЛИЦЫ ШАБЛОНОВ ===
def create_templates_table():
    """Принудительное создание таблицы workout_templates"""
    try:
        conn = sqlite3.connect('fitness_bot.db')
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                exercises TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
        logger.info("✅ Таблица workout_templates создана/проверена")
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблицы workout_templates: {e}")

async def main():
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация базы данных (создаст основные таблицы)
    await init_db()
    logger.info("База данных инициализирована")

    # ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ ТАБЛИЦЫ ШАБЛОНОВ
    create_templates_table()

    # --- РЕГИСТРАЦИЯ РОУТЕРОВ  ---
    routers = [
        (start_router, "Стартовые команды"),
        (profile_router, "Профиль"),
        (progress_stats_router, "Прогресс статистика"),
        (journal_router, "Дневник тренировок"),
        (templates_router, "Шаблоны тренировок"),
        (leaderboard_router, "Лидерборды"),
        (achievements_router, "Достижения"),
        (friends_router, "Друзья"),
        (timer_router, "Таймер"),
        (ai_advice_router, "AI-советы"),
        (calendar_router, "Календарь"),
        (settings_router, "Настройки"),
        (premium_router, "Премиум"),
        (training_router, "Тренировки"),
        (workout_session_router, "Тренировочные сессии"),
        (charts_router, "Графики прогресса"),
        (daily_routine_router, "Режим дня"),
        (payment_router, "Платежи"),
        (exercises_router, "Упражнения"),
        (recommendations_router, "Рекомендации"),
        (feed_router, "Лента активности"),
        (one_rep_max_router, "1ПМ"),
        (challenges_router, "Челленджи"),
        (admin_panel_router, "Админ-панель"),
        (calorie_tracker_router, "Калории"),
        (common_router, "Общие обработчики"),
    ]
    
    logger.info(f"charts_router: {charts_router}")
    if charts_router:
        logger.info("✅ charts_router успешно импортирован")
    else:
        logger.error("❌ charts_router = None")

    for router, name in routers:
        try:
            dp.include_router(router)
            logger.info(f"✅ Роутер '{name}' зарегистрирован")
        except Exception as e:
            logger.error(f"❌ Ошибка регистрации роутера '{name}': {e}")

    logger.info("✅ Базовые роутеры зарегистрированы, бот запускается...")

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