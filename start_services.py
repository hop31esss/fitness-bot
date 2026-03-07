import subprocess
import threading
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_bot():
    """Запуск основного бота"""
    import main
    main.main()

def run_backup_service():
    """Запуск сервиса бэкапов"""
    import backup
    backup.create_backup()  # Первый бэкап
    # backup.schedule.run_pending() будет в цикле

def run_web_admin():
    """Запуск веб-админки"""
    import web_admin
    web_admin.app.run(host='0.0.0.0', port=5000, debug=False)

def run_webhook_server():
    """Запуск вебхук-сервера для Apple Health"""
    try:
        import webhook_server
        logger.info("📡 Запуск вебхук-сервера на порту 5001...")
        webhook_server.app.run(host='0.0.0.0', port=5001, debug=False)
    except Exception as e:
        logger.error(f"❌ Ошибка запуска вебхук-сервера: {e}")

if __name__ == "__main__":
    logger.info("🚀 Запуск всех сервисов...")
    
    # Запускаем в отдельных потоках
    threads = [
        threading.Thread(target=run_bot, daemon=True),
        threading.Thread(target=run_backup_service, daemon=True),
        threading.Thread(target=run_web_admin, daemon=True),
        threading.Thread(target=run_webhook_server, daemon=True)  # Новый поток
    ]
    
    for t in threads:
        t.start()
        time.sleep(2)  # Пауза между запусками
    
    logger.info("✅ Все сервисы запущены!")
    logger.info("📡 Вебхук-сервер доступен на порту 5001")
    
    # Держим главный поток
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("🛑 Остановка сервисов...")