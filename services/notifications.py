import logging
import asyncio
from datetime import date, timedelta
from aiogram import Bot

from database.base import db
from services.progress_analytics import EXERCISE_VOLUME_SQL, format_kg
from utils.clock import now, now_hm, today_iso, normalize_hhmm, same_hhmm

logger = logging.getLogger(__name__)


async def send_broadcast_message(bot: Bot, message_text: str) -> int:
    """Отправка сообщения всем пользователям"""
    try:
        users = await db.fetch_all("SELECT user_id FROM users")
        success_count = 0
        failed_count = 0
        for user in users:
            try:
                await bot.send_message(user["user_id"], message_text)
                success_count += 1
                await asyncio.sleep(0.05)
            except Exception as e:
                failed_count += 1
                logger.debug(f"Не удалось отправить пользователю {user['user_id']}: {e}")
        logger.info(f"Рассылка: успешно {success_count}, неудачно {failed_count}")
        return success_count
    except Exception as e:
        logger.error(f"Ошибка рассылки: {e}")
        return 0


async def _last_session_date(user_id: int) -> str | None:
    row = await db.fetch_one(
        """
        SELECT ws.date
        FROM workout_sessions ws
        JOIN workout_exercises we ON we.session_id = ws.id
        WHERE ws.user_id = ?
        GROUP BY ws.id
        ORDER BY ws.date DESC, ws.id DESC
        LIMIT 1
        """,
        (user_id,),
    )
    if not row:
        return None
    return str(row["date"])[:10]


async def send_daily_reminders(bot: Bot):
    """Отправка ежедневных напоминаний по времени сервера."""
    try:
        users = await db.fetch_all(
            """
            SELECT u.user_id, us.notification_time, us.last_reminder_date
            FROM user_settings us
            JOIN users u ON us.user_id = u.user_id
            WHERE COALESCE(us.notifications_enabled, 0) != 0
            """
        )
        current_time = now_hm()
        today = today_iso()
        success_count = 0

        for user in users:
            try:
                if str(user.get("last_reminder_date") or "")[:10] == today:
                    continue
                notification_time = normalize_hhmm(user.get("notification_time"))
                if not same_hhmm(notification_time, current_time):
                    continue

                last_date = await _last_session_date(user["user_id"])
                message = "💪 *Напоминание о тренировке!*\n\n"
                if last_date:
                    days_ago = (now().date() - date.fromisoformat(last_date)).days
                    if days_ago == 0:
                        message += "Вы уже тренировались сегодня! Отличная работа! 🎉\n"
                        message += "Не забывайте про восстановление."
                    elif days_ago == 1:
                        message += "Прошёл уже 1 день с последней тренировки.\n"
                        message += "Самое время для новой тренировки!"
                    else:
                        message += f"Прошло уже {days_ago} дней с последней тренировки.\n"
                        message += "Пора возвращаться в ритм! 💪"
                else:
                    message += "Вы ещё не начинали тренироваться!\n"
                    message += "Начните сегодня и отслеживайте свой прогресс! 🚀"
                message += "\n\nОткройте 🏋️ Тренировки, чтобы начать."

                await bot.send_message(user["user_id"], message, parse_mode="Markdown")
                await db.execute(
                    """
                    UPDATE user_settings
                    SET last_reminder_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (today, user["user_id"]),
                )
                success_count += 1
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
        settings = await db.fetch_one(
            "SELECT notifications_enabled FROM user_settings WHERE user_id = ?",
            (user_id,),
        )
        if not settings or not settings["notifications_enabled"]:
            return
        message = (
            f"🎉 *Новая ачивка!*\n\n"
            f"Вы получили: *{achievement_name}*\n\n"
            f"Продолжайте в том же духе! 💪"
        )
        await bot.send_message(user_id, message, parse_mode="Markdown")


async def send_weekly_stats(bot: Bot):
    """Отправка еженедельной статистики"""
    try:
        current = now()
        if current.weekday() != 6:
            return
        today = today_iso()
        users = await db.fetch_all(
            """
            SELECT u.user_id, us.last_weekly_stats_date
            FROM user_settings us
            JOIN users u ON us.user_id = u.user_id
            WHERE COALESCE(us.notifications_enabled, 0) != 0
            """
        )
        week_start = (current.date() - timedelta(days=6)).isoformat()
        prev_start = (current.date() - timedelta(days=13)).isoformat()
        prev_end = (current.date() - timedelta(days=7)).isoformat()

        for user in users:
            try:
                if str(user.get("last_weekly_stats_date") or "")[:10] == today:
                    continue
                user_id = user["user_id"]
                stats = await db.fetch_one(
                    f"""
                    SELECT COUNT(DISTINCT ws.id) as workout_count,
                           COALESCE(SUM({EXERCISE_VOLUME_SQL}), 0) as total_volume
                    FROM workout_sessions ws
                    JOIN workout_exercises we ON we.session_id = ws.id
                    WHERE ws.user_id = ? AND date(ws.date) BETWEEN date(?) AND date(?)
                    """,
                    (user_id, week_start, today),
                )
                if not stats or not stats["workout_count"]:
                    continue
                message = (
                    f"📊 *Ваша недельная статистика*\n\n"
                    f"🏋️ Тренировок за неделю: {stats['workout_count']}\n"
                    f"⚖️ Общий объём: {format_kg(stats['total_volume'] or 0)} кг\n\n"
                )
                prev_stats = await db.fetch_one(
                    """
                    SELECT COUNT(DISTINCT ws.id) as prev_count
                    FROM workout_sessions ws
                    JOIN workout_exercises we ON we.session_id = ws.id
                    WHERE ws.user_id = ? AND date(ws.date) BETWEEN date(?) AND date(?)
                    """,
                    (user_id, prev_start, prev_end),
                )
                if prev_stats and prev_stats["prev_count"]:
                    diff = stats["workout_count"] - prev_stats["prev_count"]
                    if diff > 0:
                        message += f"📈 На {diff} тренировок больше, чем на прошлой неделе! 🎉\n"
                    elif diff < 0:
                        message += f"📉 На {abs(diff)} тренировок меньше, чем на прошлой неделе.\n"
                    else:
                        message += "📊 Такое же количество тренировок, как на прошлой неделе.\n"
                message += "\nОтличная работа! Продолжайте в том же духе! 💪"
                await bot.send_message(user_id, message, parse_mode="Markdown")
                await db.execute(
                    """
                    UPDATE user_settings
                    SET last_weekly_stats_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                    """,
                    (today, user_id),
                )
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.debug(f"Не удалось отправить недельную статистику {user['user_id']}: {e}")
    except Exception as e:
        logger.error(f"Ошибка отправки недельной статистики: {e}")


async def run_notification_scheduler(bot: Bot):
    """Check reminder time about twice a minute using the server timezone."""
    logger.info("Планировщик уведомлений запущен")
    while True:
        try:
            await send_daily_reminders(bot)
            await send_weekly_stats(bot)
        except Exception:
            logger.exception("Ошибка цикла уведомлений")
        await asyncio.sleep(25)
