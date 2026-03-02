import os
import shutil
import schedule
import time
from datetime import datetime
import logging
import gzip

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация
ADMIN_ID = 385450652  # Ваш ID
BACKUP_HOUR = 3  # Час бэкапа (3:00 ночи)

def create_backup():
    """Создание резервной копии базы данных"""
    try:
        # Создаем папку для бэкапов
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        # Проверяем, существует ли база данных
        if not os.path.exists("fitness_bot.db"):
            logger.warning("❌ База данных не найдена")
            return
        
        # Имя файла с датой
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/fitness_bot_{timestamp}.db"
        
        # Копируем базу данных
        shutil.copy2("fitness_bot.db", backup_file)
        
        # Сжимаем
        with open(backup_file, 'rb') as f_in:
            with gzip.open(f"{backup_file}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Удаляем несжатый файл
        os.remove(backup_file)
        
        # Удаляем старые бэкапы (оставляем последние 30)
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.gz')])
        if len(backups) > 30:
            for old_file in backups[:-30]:
                os.remove(os.path.join(backup_dir, old_file))
        
        logger.info(f"✅ Бэкап создан: {backup_file}.gz")
        
        # Размер файла
        file_size = os.path.getsize(f"{backup_file}.gz") / 1024 / 1024
        
        logger.info(f"📊 Размер бэкапа: {file_size:.2f} MB")
        
    except Exception as e:
        logger.error(f"❌ Ошибка бэкапа: {e}")

def run_backup_scheduler():
    """Запуск планировщика бэкапов"""
    # Запускаем первый бэкап сразу
    create_backup()
    
    # Планируем ежедневные бэкапы
    schedule.every().day.at(f"{BACKUP_HOUR:02d}:00").do(create_backup)
    
    logger.info(f"⏰ Планировщик бэкапов запущен (ежедневно в {BACKUP_HOUR:02d}:00)")
    
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    run_backup_scheduler()