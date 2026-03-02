import logging
import asyncio
from datetime import datetime, timedelta
from typing import List
from aiogram import Bot

from database.base import db

logger = logging.getLogger(__name__)

async def send_broadcast_message(bot: Bot, message_text: str) -> int:
    """Отправка сообщения всем пользователям"""
    try:
        # Получаем всех пользователей
        users = await db.fetch_all("SELECT user_id FROM users")
        
        success_count = 0
        failed_count = 0
        
        for user in users:
            try:
                await bot.send_message(user['user_id'], message_text)
                success_count += 1
                
                # Небольшая задержка чтобы не спамить
                await asyncio.sleep(0.05)
                
            except Exception as e:
                failed_count += 1
                logger.debug(f"Не удалось отправить пользователю {user['user_id']}: {e}")
        
        logger.info(f"Рассылка: успешно {success_count}, неудачно {failed_count}")
        return success_count
        
    except Exception as e:
        logger.error(f"Ошибка рассылки: {e}")
        return 0

async def send_daily_reminders(bot: Bot):
    """Отправка ежедневных напоминаний"""
    try:
        # Получаем пользователей с включенными уведомлениями
        users = await db.fetch_all("""
            SELECT u.user_id, us.notification_time 
            FROM user_settings us
            JOIN users u ON us.user_id = u.user_id
            WHERE us.notifications_enabled = TRUE
        """)
        
        current_time = datetime.now().strftime('%H:%M')
        success_count = 0
        
        for user in users:
            try:
                # Проверяем время уведомления
                notification_time = user.get('notification_time', '18:00')
                
                # Если текущее время соответствует времени уведомления пользователя
                if notification_time and current_time.startswith(notification_time[:5]):
                    
                    # Проверяем когда была последняя тренировка
                    last_workout = await db.fetch_one("""
                        SELECT created_at FROM workouts 
                        WHERE user_id = ? 
                        ORDER BY created_at DESC LIMIT 1
                    """, (user['user_id'],))
                    
                    message = "💪 *Напоминание о тренировке!*\n\n"
                    
                    if last_workout:
                        last_date = datetime.strptime(last_workout['created_at'][:10], '%Y-%m-%d')
                        days_ago = (datetime.now() - last_date).days
                        
                        if days_ago == 0:
                            message += "Вы уже тренировались сегодня! Отличная работа! 🎉\n"
                            message += "Не забывайте про восстановление."
                        elif days_ago == 1:
                            message += "Прошло уже 1 день с последней тренировки.\n"
                            message += "Самое время для новой тренировки!"
                        else:
                            message += f"Прошло уже {days_ago} дней с последней тренировки.\n"
                            message += "Пора возвращаться в ритм! 💪"
                    else:
                        message += "Вы еще не начинали тренироваться!\n"
                        message += "Начните сегодня и отслеживайте свой прогресс! 🚀"
                    
                    message += "\n\nДля добавления тренировки нажмите ➕ в меню."
                    
                    await bot.send_message(user['user_id'], message)
                    success_count += 1
                    
                    # Задержка
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.debug(f"Не удалось отправить напоминание {user['user_id']}: {e}")
        
        if success_count > 0:
            logger.info(f"Отправлено {success_count} ежедневных напоминаний")
            
    except Exception as e:
        logger.error(f"Ошибка отправки напоминаний: {e}")

async def notify_achievement(bot: Bot, user_id: int, achievement_name: str):
    """Уведомление о получении ачивки"""
    try:
        # Проверяем включены ли уведомления у пользователя
        settings = await db.fetch_one(
            "SELECT notifications_enabled FROM user_settings WHERE user_id = ?",
            (user_id,)
        )
        
        if not settings or not settings['notifications_enabled']:
            return
        
        message = (
            f"🎉 *Новая ачивка!*\n\n"
            f"Вы получили: *{achievement_name}*\n\n"
            f"Продолжайте в том же духе! 💪"
        )
        
        await bot.send_message(user_id, message)
        
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление об ачивке {user_id}: {e}")

async def send_weekly_stats(bot: Bot):
    """Отправка еженедельной статистики"""
    try:
        # Получаем пользователей с уведомлениями
        users = await db.fetch_all("""
            SELECT u.user_id FROM user_settings us
            JOIN users u ON us.user_id = u.user_id
            WHERE us.notifications_enabled = TRUE
        """)
        
        # Только по воскресеньям
        if datetime.now().weekday() != 6:  # 6 = воскресенье
            return
        
        for user in users:
            try:
                user_id = user['user_id']
                
                # Статистика за неделю
                week_ago = datetime.now() - timedelta(days=7)
                
                stats = await db.fetch_one("""
                    SELECT 
                        COUNT(*) as workout_count,
                        SUM(sets * reps * COALESCE(weight, 1)) as total_volume
                    FROM workouts 
                    WHERE user_id = ? AND created_at > ?
                """, (user_id, week_ago))
                
                if stats and stats['workout_count']:
                    message = (
                        f"📊 *Ваша недельная статистика*\n\n"
                        f"🏋️ Тренировок за неделю: {stats['workout_count']}\n"
                        f"⚖️ Общий объем: {int(stats['total_volume'] or 0):,} кг\n\n"
                    )
                    
                    # Сравнение с предыдущей неделей
                    two_weeks_ago = datetime.now() - timedelta(days=14)
                    prev_stats = await db.fetch_one("""
                        SELECT COUNT(*) as prev_count 
                        FROM workouts 
                        WHERE user_id = ? AND created_at BETWEEN ? AND ?
                    """, (user_id, two_weeks_ago, week_ago))
                    
                    if prev_stats and prev_stats['prev_count']:
                        diff = stats['workout_count'] - prev_stats['prev_count']
                        if diff > 0:
                            message += f"📈 На {diff} тренировок больше чем на прошлой неделе! 🎉\n"
                        elif diff < 0:
                            message += f"📉 На {abs(diff)} тренировок меньше чем на прошлой неделе.\n"
                        else:
                            message += "📊 Такое же количество тренировок как на прошлой неделе.\n"
                    
                    message += "\nОтличная работа! Продолжайте в том же духе! 💪"
                    
                    await bot.send_message(user_id, message)
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.debug(f"Не удалось отправить недельную статистику {user['user_id']}: {e}")
                
    except Exception as e:
        logger.error(f"Ошибка отправки недельной статистики: {e}")