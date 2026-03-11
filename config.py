import os
from typing import List

# Токен бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "8391767389:AAFjf5bQDvi12-DbE3pbATzmYdjjki0Jq0A")

# ID администратора (ВАШ ID)
ADMIN_ID = 385450652

# FatSecret API
FATSECRET_CLIENT_ID = os.getenv("FATSECRET_CLIENT_ID", "063f6d1df26c4b97a67bc164faea20a5")
FATSECRET_CLIENT_SECRET = os.getenv("FATSECRET_CLIENT_SECRET", "40780f6509c14cdb95e7915d29920a6c")
FATSECRET_ENABLED = bool(FATSECRET_CLIENT_ID)

# Список администраторов (для совместимости)
ADMIN_IDS = [385450652]

# Часовой пояс сервера (например 'Europe/Moscow', 'Asia/Yekaterinburg', 'UTC')
SERVER_TIMEZONE = os.getenv("SERVER_TIMEZONE", "Europe/Moscow")

# Список друзей с премиум-доступом
PREMIUM_FRIENDS = [
    # Добавляйте сюда ID друзей
    # 123456789,
]

# НАСТРОЙКИ ОПЛАТЫ ЧЕРЕЗ STARS
STARS_PRICE = 20  # Цена в Telegram Stars (минимально 1 Star)
SUBSCRIPTION_DAYS = 30  # Дней действует подписка

# Настройки ЮKassa
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "1283021")  # из личного кабинета ЮKassa
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "live_Ih5mldGYVTSFw0rbi1ASoxjP7DqY9HryMTSq6WbR5yA")  # из личного кабинета
YOOKASSA_PROVIDER_TOKEN = os.getenv("YOOKASSA_PROVIDER_TOKEN", "390540012:LIVE:90312")  # от @BotFather

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///fitness_bot.db")

# OpenAI API ключ (получите на platform.openai.com)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "sk-aitunnel-dAut1vwt4gXAHGjwqXJ621cvxLpJ1kJP")  # ВСТАВЬТЕ СВОЙ КЛЮЧ!
OPENAI_ENABLED = True  # Включаем OpenAI
# Настройки экспорта
EXPORT_PATH = os.getenv("EXPORT_PATH", "exports")

# Создание директорий если нужно
os.makedirs(EXPORT_PATH, exist_ok=True)
os.makedirs("backups", exist_ok=True)

# GigaChat API (Российский аналог OpenAI)
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS", "")  # Client ID:Client Secret
GIGACHAT_ENABLED = bool(GIGACHAT_CREDENTIALS)