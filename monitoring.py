import logging
import traceback
from datetime import datetime, timedelta
from aiogram.types import Update
import sys

class ErrorMonitor:
    def __init__(self, bot, admin_id):
        self.bot = bot
        self.admin_id = admin_id
        self.error_log = []
        
    async def handle_error(self, update: Update, error: Exception):
        """Обработка ошибки"""
        # Логируем ошибку
        error_trace = traceback.format_exc()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        log_entry = {
            'time': timestamp,
            'error': str(error),
            'trace': error_trace,
            'update': str(update) if update else 'No update'
        }
        
        self.error_log.append(log_entry)
        
        # Сохраняем в файл
        with open('errors.log', 'a', encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Время: {timestamp}\n")
            f.write(f"Ошибка: {error}\n")
            f.write(f"Traceback:\n{error_trace}\n")
            f.write(f"Update: {update}\n")
        
        # Отправляем админу
        try:
            error_text = (
                f"❌ *Ошибка в боте*\n\n"
                f"Время: {timestamp}\n"
                f"Ошибка: `{str(error)[:200]}`\n"
                f"Подробности в errors.log"
            )
            await self.bot.send_message(self.admin_id, error_text)
        except:
            pass
        
        # Логируем в консоль
        logging.error(f"Ошибка: {error}\n{error_trace}")
    
    def get_stats(self):
        """Статистика ошибок"""
        total = len(self.error_log)
        last_24h = sum(1 for e in self.error_log 
                      if datetime.now() - datetime.strptime(e['time'], "%Y-%m-%d %H:%M:%S") < timedelta(hours=24))
        
        return {
            'total': total,
            'last_24h': last_24h,
            'last_error': self.error_log[-1] if self.error_log else None
        }