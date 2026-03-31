import os
import re
from typing import List
from dotenv import load_dotenv

# Загружаем переменные окружения
# override=False: по умолчанию предпочитаем уже заданные env.
# Но если BOT_TOKEN выглядит неверным (например, placeholder), ниже сделаем fallback на .env с override=True.
load_dotenv()

# Токен бота
BOT_TOKEN_RAW = os.getenv("BOT_TOKEN")
if not BOT_TOKEN_RAW:
    raise ValueError("BOT_TOKEN не найден в переменных окружения!")

# Docker/Compose и .env иногда передают токен с пробелами/кавычками/CRLF.
BOT_TOKEN = BOT_TOKEN_RAW.strip()
if BOT_TOKEN and BOT_TOKEN[0] == BOT_TOKEN[-1] and BOT_TOKEN[0] in ("'", '"'):
    BOT_TOKEN = BOT_TOKEN[1:-1].strip()

_token_re = re.compile(r"^\d+:[A-Za-z0-9_-]{35}$")

def _validate_or_none(token: str) -> bool:
    return bool(token) and bool(_token_re.match(token))

if not _validate_or_none(BOT_TOKEN):
    # Fallback: если compose присвоил placeholder в env, но .env внутри контейнера корректный,
    # перезагрузим .env с override=True и попробуем ещё раз.
    load_dotenv(override=True)
    BOT_TOKEN_RAW = os.getenv("BOT_TOKEN")
    BOT_TOKEN = BOT_TOKEN_RAW.strip() if BOT_TOKEN_RAW else ""
    if BOT_TOKEN and BOT_TOKEN[0] == BOT_TOKEN[-1] and BOT_TOKEN[0] in ("'", '"'):
        BOT_TOKEN = BOT_TOKEN[1:-1].strip()

    if not _validate_or_none(BOT_TOKEN):
        safe_prefix = BOT_TOKEN[:5] if BOT_TOKEN else ""
        safe_len = len(BOT_TOKEN) if BOT_TOKEN else 0
        raise ValueError(
            f"BOT_TOKEN имеет неверный формат. len={safe_len}, prefix={safe_prefix!r}. "
            "Проверьте переменную окружения/ .env (без кавычек и пробелов)."
        )

# ID администратора (ВАШ ID)
ADMIN_ID = int(os.getenv("ADMIN_ID", "385450652"))

# FatSecret API
FATSECRET_CLIENT_ID = os.getenv("FATSECRET_CLIENT_ID")
FATSECRET_CLIENT_SECRET = os.getenv("FATSECRET_CLIENT_SECRET")
USE_FATSECRET = os.getenv("USE_FATSECRET", "false").lower() == "true"

# Список администраторов (для совместимости)
ADMIN_IDS = [ADMIN_ID]

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
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY")
YOOKASSA_PROVIDER_TOKEN = os.getenv("YOOKASSA_PROVIDER_TOKEN")

# Настройки базы данных
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///fitness_bot.db")

# OpenAI API ключ
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_ENABLED = os.getenv("OPENAI_ENABLED", "false").lower() == "true"
# Настройки экспорта
EXPORT_PATH = os.getenv("EXPORT_PATH", "exports")

# Создание директорий если нужно
os.makedirs(EXPORT_PATH, exist_ok=True)
os.makedirs("backups", exist_ok=True)

# AITunnel API (для работы в РФ)
AITUNNEL_API_KEY = os.getenv("AITUNNEL_API_KEY")

# GigaChat API (Российский аналог OpenAI)
GIGACHAT_CREDENTIALS = os.getenv("GIGACHAT_CREDENTIALS")
GIGACHAT_ENABLED = bool(GIGACHAT_CREDENTIALS)