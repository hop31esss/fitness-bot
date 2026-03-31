# 🚀 Настройка окружения для фитнес-бота

## ⚠️ Важно: Безопасность

Все секретные данные (токены, API ключи) должны храниться в файле `.env`, который **НЕ** загружается в Git.

## 📋 Шаги настройки

### 1. Создайте файл `.env`
Скопируйте `.env.example` в `.env`:
```bash
cp .env.example .env
```

### 2. Заполните `.env` файл
Откройте `.env` и замените `YOUR_..._HERE` на реальные значения:

```bash
# Токен Telegram бота (от @BotFather)
BOT_TOKEN=YOUR_BOT_TOKEN_HERE

# ID администратора
ADMIN_ID=YOUR_ADMIN_ID_HERE
ADMIN_PASSWORD=YOUR_STRONG_ADMIN_PASSWORD
SESSION_COOKIE_SECURE=true

# Защита входа в web_admin (анти-брутфорс)
ADMIN_MAX_LOGIN_ATTEMPTS=5
ADMIN_LOGIN_WINDOW_SECONDS=900
ADMIN_LOCKOUT_SECONDS=900

# FatSecret API (для трекинга калорий)
FATSECRET_CLIENT_ID=YOUR_FATSECRET_CLIENT_ID
FATSECRET_CLIENT_SECRET=YOUR_FATSECRET_CLIENT_SECRET
USE_FATSECRET=true

# ЮKassa платежи
YOOKASSA_SHOP_ID=YOUR_YOOKASSA_SHOP_ID
YOOKASSA_SECRET_KEY=YOUR_YOOKASSA_SECRET_KEY
YOOKASSA_PROVIDER_TOKEN=YOUR_YOOKASSA_PROVIDER_TOKEN

# OpenAI API (для AI-советов)
OPENAI_API_KEY=YOUR_OPENAI_API_KEY
OPENAI_ENABLED=true

# AITunnel API (автоматически из OpenAI)
AITUNNEL_API_KEY=YOUR_AITUNNEL_API_KEY

# GigaChat API (опционально)
GIGACHAT_CREDENTIALS=YOUR_GIGACHAT_CREDENTIALS

# База данных
DATABASE_URL=sqlite+aiosqlite:///fitness_bot.db

# Часовой пояс
SERVER_TIMEZONE=Europe/Moscow

# Настройки подписки
STARS_PRICE=20
SUBSCRIPTION_DAYS=30
```

## 🔑 Где взять ключи

### Telegram Bot Token
1. Найдите @BotFather в Telegram
2. Отправьте `/newbot`
3. Следуйте инструкциям
4. Скопируйте полученный токен

### FatSecret API
1. Зарегистрируйтесь на [fatsecret.com](https://fatsecret.com)
2. Создайте приложение
3. Получите Client ID и Client Secret

### ЮKassa
1. Зарегистрируйтесь на [yookassa.ru](https://yookassa.ru)
2. Получите Shop ID и API ключ
3. Создайте Provider Token в @BotFather

### OpenAI API
1. Зарегистрируйтесь на [openai.com](https://openai.com)
2. Получите API ключ
3. Для работы в РФ используйте [aitunnel.ru](https://aitunnel.ru)

## ✅ Проверка

После настройки проверьте токен:
```bash
python check_token.py
```

## 🚀 Запуск

```bash
python main.py
```

### Запуск web-админки

```bash
python web_admin.py
```

По умолчанию админка поднимается на `http://<host>:5000/login`.

## ⚠️ Никогда не делитесь `.env` файлом!

Файл `.env` содержит все ваши секретные ключи. Не загружайте его в Git, не отправляйте никому.

## 🔐 Как безопасно хранить ключи на сервере (BotHost)

- Храните реальные ключи только в `.env` на сервере или в секретах окружения BotHost.
- В репозиторий коммитьте только `.env.example` (без реальных значений).
- Для production включайте `SESSION_COOKIE_SECURE=true` (если сайт работает по HTTPS).
- После любой утечки ключа сразу ротируйте его у провайдера (Telegram, YooKassa, OpenAI и т.д.).

## 🧭 Как применить изменения через GitHub (ваш обычный процесс)

1. Локально внесите изменения и проверьте, что `.env` не попал в коммит.
2. Закоммитьте изменения в коде и документации.
3. Запушьте в GitHub.
4. На BotHost обновите код до последнего коммита (или redeploy из GitHub).
5. На сервере заполните `.env` реальными значениями (если еще не заполнен).
6. Перезапустите сервисы.

Пример команд:

```bash
git status
git add web_admin.py webhook_server.py SETUP.md .env.example
git commit -m "Harden admin auth and improve secret setup docs"
git push origin main
```

После деплоя проверьте:
- `/login` в админке открывается;
- после 5 неверных попыток вход блокируется на 15 минут;
- бот отвечает в Telegram, а платежи/AI работают с ключами из `.env`.