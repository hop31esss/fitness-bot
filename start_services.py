import asyncio
import threading
import time
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_bot():
    """Запуск основного бота"""
    import main
    asyncio.run(main.main())


def run_backup_service():
    """Запуск сервиса бэкапов"""
    import backup
    backup.create_backup()


def run_web_admin():
    """Запуск веб-админки на localhost по умолчанию."""
    import web_admin
    if web_admin.ADMIN_PASSWORD in web_admin._UNSAFE_PASSWORDS:
        logger.error("Веб-админка не запущена: задайте ADMIN_PASSWORD")
        return
    host = os.getenv("WEB_ADMIN_HOST", "127.0.0.1")
    port = int(os.getenv("WEB_ADMIN_PORT", "5000"))
    web_admin.app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    logger.info("Запуск сервисов (бот + бэкап + веб-админка). Apple Health отключён.")

    threads = [
        threading.Thread(target=run_bot, daemon=True),
        threading.Thread(target=run_backup_service, daemon=True),
        threading.Thread(target=run_web_admin, daemon=True),
    ]

    for t in threads:
        t.start()
        time.sleep(2)

    logger.info("Сервисы запущены. Apple Health webhook не стартует (APPLE_HEALTH отложен).")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Остановка сервисов...")
