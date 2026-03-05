import pytz
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Часовой пояс сервера (укажите ваш, например 'Europe/Moscow')
SERVER_TIMEZONE = pytz.timezone('Europe/Moscow')
UTC = pytz.UTC

def get_server_time():
    """Получить текущее время на сервере с учётом часового пояса"""
    return datetime.now(SERVER_TIMEZONE)

def get_utc_time():
    """Получить текущее время в UTC"""
    return datetime.now(UTC)

def to_server_time(utc_dt):
    """Конвертировать UTC время в время сервера"""
    if utc_dt.tzinfo is None:
        # Если время наивное (без таймзоны), считаем что это UTC
        utc_dt = UTC.localize(utc_dt)
    return utc_dt.astimezone(SERVER_TIMEZONE)

def to_utc(local_dt):
    """Конвертировать локальное время в UTC"""
    if local_dt.tzinfo is None:
        # Если время наивное, считаем что это время сервера
        local_dt = SERVER_TIMEZONE.localize(local_dt)
    return local_dt.astimezone(UTC)

def format_datetime(dt, format="%d.%m.%Y %H:%M", tz=None):
    """Форматировать дату с учётом часового пояса"""
    if dt.tzinfo is None:
        # Если время наивное, считаем что это UTC
        dt = UTC.localize(dt)
    
    if tz:
        dt = dt.astimezone(tz)
    else:
        dt = dt.astimezone(SERVER_TIMEZONE)
    
    return dt.strftime(format)

def get_user_timezone(user_id):
    """
    Получить часовой пояс пользователя (заглушка)
    В будущем можно сохранять в БД предпочтения пользователя
    """
    # Пока возвращаем часовой пояс сервера
    # Позже можно добавить возможность пользователям выбирать свой часовой пояс
    return SERVER_TIMEZONE