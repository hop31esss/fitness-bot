# Fitness AI Bot

![CI](https://github.com/<user>/<repo>/actions/workflows/ci.yml/badge.svg)

Telegram-бот на `aiogram` для учёта тренировок, статистики, программ и сопутствующих функций.

## Установка

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
```

## Переменные окружения

Скопируйте `.env.example` в `.env` и заполните:

- `BOT_TOKEN`
- `ADMIN_ID`
- `OPENAI_API_KEY` / `AITUNNEL_API_KEY` (если используете AI)
- `YOOKASSA_*` (если используете оплату)
- `FATSECRET_*` (если используете калорийный трекер)

## Локальный запуск

```bash
python main.py
```

## Запуск в Docker

```bash
docker compose up -d --build
```

## Структура меню

- `/start`:
  - `🏋️ Начать тренировку`
  - `✍️ Записать`
  - `📊 Прогресс`
  - `📋 Открыть всё меню`
- Полное меню:
  - `📘 Журнал тренировок`
  - `📔 Дневник тренировок`
  - `📚 Мои программы`
  - `💪 Упражнения`
  - `🔙 Назад`

## Логирование

Централизованное логирование действий пользователей реализовано в `utils/logging.py`:

- `log_action(user_id, action, extra=None)`
- лог-файл: `bot.log`

## Тесты

```bash
pytest -q --cov=. --cov-report=term-missing
```

Тесты меню находятся в `tests/test_menu_navigation.py`.

## CI

Workflow: `.github/workflows/ci.yml`

Запускает:

- Ruff
- mypy
- pytest + coverage
- docker build

