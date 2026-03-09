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
from handlers.referral import router as referral_router
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

async def main():
    # Инициализация бота
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализация базы данных (создаст основные таблицы)
    await init_db()
    logger.info("База данных инициализирована")


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
        (referral_router, "Реферальная система"),
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