from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime
import json
import logging

from database.base import db

router = Router()
logger = logging.getLogger(__name__)

# Хранилище для IFTTT ключей пользователей
# В реальном проекте лучше сохранять в БД
user_webhooks = {}

@router.message(Command("health"))
async def health_command(message: Message):
    """Главное меню Apple Health"""
    user_id = message.from_user.id
    
    text = (
        "🍎 *Apple Health интеграция*\n\n"
        "Подключите свои тренировки к Apple Health двумя способами:\n\n"
        
        "**1️⃣ Через IFTTT (быстро и просто)**\n"
        "• Автоматическая синхронизация тренировок\n"
        "• Отслеживание веса и активности\n"
        "• Бесплатно\n\n"
        
        "**2️⃣ Наше iOS приложение (скоро)**\n"
        "• Полная двусторонняя синхронизация\n"
        "• Все метрики здоровья\n"
        "• Без задержек\n\n"
        
        "Выберите действие:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔧 НАСТРОИТЬ IFTTT", callback_data="ifttt_setup"),
        InlineKeyboardButton(text="📊 МОИ ДАННЫЕ", callback_data="health_data")
    )
    builder.row(
        InlineKeyboardButton(text="📖 ИНСТРУКЦИЯ", callback_data="health_instructions"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="settings")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "ifttt_setup")
async def ifttt_setup(callback: CallbackQuery):
    """Настройка IFTTT для пользователя"""
    user_id = callback.from_user.id
    
    # Генерируем уникальный ключ для пользователя
    import secrets
    webhook_key = secrets.token_urlsafe(16)
    user_webhooks[user_id] = webhook_key
    
    text = (
        "🔧 *Настройка IFTTT*\n\n"
        "**Шаг 1:** Установите приложение IFTTT из App Store\n\n"
        "**Шаг 2:** Создайте аккаунт или войдите\n\n"
        "**Шаг 3:** Создайте новый апплет\n\n"
        "**Шаг 4:** Выберите сервис *Apple Health*\n\n"
        "**Шаг 5:** Выберите триггер, например:\n"
        "• *New Workout logged* (новая тренировка)\n"
        "• *New Weight logged* (новый вес)\n"
        "• *New Sleep Analysis* (новый сон)\n\n"
        "**Шаг 6:** Выберите сервис *Webhooks*\n\n"
        "**Шаг 7:** Вставьте этот URL:\n"
        f"`https://your-bot-domain.com/webhook/{webhook_key}`\n\n"
        "**Шаг 8:** В поле Body отправьте:\n"
        "```json\n"
        "{\n"
        '  "type": "{{Type}}",\n'
        '  "date": "{{Date}}",\n'
        '  "calories": "{{Calories}}",\n'
        '  "duration": "{{Duration}}",\n'
        '  "user_id": "' + str(user_id) + '"\n'
        "}\n"
        "```\n\n"
        "**Шаг 9:** Сохраните апплет!\n\n"
        "✅ Всё! Теперь тренировки будут приходить в бот."
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ", callback_data="health_check"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="health_command")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "health_data")
async def health_data(callback: CallbackQuery):
    """Просмотр синхронизированных данных"""
    user_id = callback.from_user.id
    
    # Получаем данные из БД
    health_entries = await db.fetch_all("""
        SELECT * FROM health_data 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 10
    """, (user_id,))
    
    if not health_entries:
        text = (
            "📊 *Мои данные Apple Health*\n\n"
            "Пока нет синхронизированных данных.\n\n"
            "Настройте IFTTT по инструкции выше!"
        )
    else:
        text = "📊 *Последние синхронизации*\n\n"
        for entry in health_entries:
            if entry['data_type'] == 'workout':
                text += f"🏋️ Тренировка: {entry['value']}\n"
            elif entry['data_type'] == 'weight':
                text += f"⚖️ Вес: {entry['value']} кг\n"
            elif entry['data_type'] == 'steps':
                text += f"👣 Шаги: {entry['value']}\n"
            elif entry['data_type'] == 'sleep':
                text += f"😴 Сон: {entry['value']} ч\n"
            text += f"   📅 {entry['created_at'][:16]}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="health_command")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "health_instructions")
async def health_instructions(callback: CallbackQuery):
    """Подробная инструкция"""
    text = (
        "📖 *Инструкция по IFTTT*\n\n"
        
        "**🎯 Для тренировок:**\n"
        "1. Триггер: Apple Health → New Workout\n"
        "2. Действие: Webhooks → Make a web request\n"
        "3. URL: ваш персональный ключ\n"
        "4. Method: POST\n"
        "5. Content Type: application/json\n"
        "6. Body: используйте шаблон выше\n\n"
        
        "**⚖️ Для веса:**\n"
        "Используйте триггер *New Weight*\n\n"
        
        "**👣 Для шагов:**\n"
        "Используйте триггер *New Step Count*\n\n"
        
        "**😴 Для сна:**\n"
        "Используйте триггер *New Sleep Analysis*\n\n"
        
        "💡 *Совет:* Создайте отдельный апплет для каждого типа данных!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="ifttt_setup")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "health_check")
async def health_check(callback: CallbackQuery):
    """Проверка подключения"""
    user_id = callback.from_user.id
    
    if user_id in user_webhooks:
        text = (
            "✅ *Подключение активно!*\n\n"
            f"Ваш ключ: `{user_webhooks[user_id]}`\n\n"
            "Если данные не приходят, проверьте:\n"
            "• Правильно ли вставлен URL\n"
            "• Разрешён ли доступ Apple Health в IFTTT\n"
            "• Есть ли новые данные в Health"
        )
    else:
        text = (
            "❌ *Подключение не настроено*\n\n"
            "Пройдите шаги настройки IFTTT сначала."
        )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="health_command")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ========== WEBHOOK ДЛЯ ПРИЁМА ДАННЫХ ==========

@router.message(Command("webhook_test"))
async def webhook_test(message: Message):
    """Тестовый вебхук (для отладки)"""
    await message.answer("📡 Вебхук работает! Отправьте POST запрос на /webhook/ваш_ключ")

# В реальном проекте это должен быть Flask/FastAPI эндпоинт
# Но для простоты покажем как обрабатывать через бота