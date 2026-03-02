import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, ADMIN_IDS
from database.base import init_db, close_db

# --- ИМПОРТЫ РОУТЕРОВ (только базовые) ---
from handlers.start import router as start_router
from handlers.profile import router as profile_router
from handlers.leaderboard import router as leaderboard_router
from handlers.achievements import router as achievements_router
from handlers.timer import router as timer_router
from handlers.calendar import router as calendar_router
from handlers.settings import router as settings_router
from handlers.premium import router as premium_router
from handlers.admin_panel import router as admin_panel_router
from handlers.common import router as common_router

# --- ИМПОРТЫ, КОТОРЫЕ МОГУТ ВЫЗЫВАТЬ ПРОБЛЕМЫ (ЗАКОММЕНТИРОВАНЫ) ---
from handlers.training import router as training_router
# from handlers.one_rep_max import router as one_rep_max_router
# from handlers.calorie_tracker import router as calorie_tracker_router
# from handlers.friends import router as friends_router
# from handlers.ai_advice import router as ai_advice_router
# from handlers.payment import router as payment_router
# from handlers.stats import router as stats_router
# from handlers.exercises import router as exercises_router
# from handlers.recommendations import router as recommendations_router
# from handlers.challenges import router as challenges_router
# from handlers.features import router as features_router
# from handlers.feed import router as feed_router
# from handlers.daily_routine import router as daily_routine_router
# from handlers.music import router as music_router
# from handlers.workout_session import router as workout_session_router

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

    # Инициализация базы данных (создаст ТОЛЬКО основные таблицы)
    await init_db()
    logger.info("База данных инициализирована")

    # --- РЕГИСТРАЦИЯ РОУТЕРОВ (только базовые) ---
    routers = [
        (start_router, "Стартовые команды"),
        (profile_router, "Профиль"),
        (leaderboard_router, "Лидерборды"),
        (achievements_router, "Достижения"),
        (timer_router, "Таймер"),
        (calendar_router, "Календарь"),
        (settings_router, "Настройки"),
        (premium_router, "Премиум"),
        (admin_panel_router, "Админ-панель"),
        (training_router, "Тренировки"),
        (common_router, "Общие обработчики"),
    ]

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