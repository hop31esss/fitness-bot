from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import asyncio
import logging
import os

from database.base import db
from config import ADMIN_ID

logger = logging.getLogger(__name__)
router = Router()

class NotificationStates(StatesGroup):
    waiting_notification_time = State()

@router.callback_query(F.data == "settings")
async def settings_menu(callback: CallbackQuery):
    """Меню настроек"""
    user_id = callback.from_user.id
    
    # Получаем текущие настройки пользователя
    user_settings = await db.fetch_one(
        """SELECT units, notifications_enabled, notification_time 
        FROM user_settings WHERE user_id = ?""",
        (user_id,)
    )
    
    if not user_settings:
        # Создаем дефолтные настройки
        await db.execute(
            """INSERT INTO user_settings (user_id, units, notifications_enabled) 
            VALUES (?, ?, ?)""",
            (user_id, 'kg', False)
        )
        user_settings = {'units': 'kg', 'notifications_enabled': False, 'notification_time': '18:00'}
    
    text = "⚙️ *Настройки*\n\n"
    text += f"📏 Единицы измерения: {'кг' if user_settings['units'] == 'kg' else 'фунты'}\n"
    text += f"🔔 Уведомления: {'ВКЛ' if user_settings['notifications_enabled'] else 'ВЫКЛ'}\n"
    if user_settings['notifications_enabled']:
        text += f"⏰ Время уведомлений: {user_settings['notification_time'] or '18:00'}\n"
    
    text += "\nВыберите настройку для изменения:"
    
    builder = InlineKeyboardBuilder()
    builder.row(
    InlineKeyboardButton(text="📏 Единицы измерения", callback_data="settings_units"),
    InlineKeyboardButton(text="🔔 Уведомления", callback_data="settings_notifications")
)
    builder.row(
        InlineKeyboardButton(text="📤 Экспорт данных", callback_data="settings_export"),
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Сброс данных", callback_data="settings_reset"),
        InlineKeyboardButton(text="ℹ️ О боте", callback_data="settings_about")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "settings_units")
async def settings_units(callback: CallbackQuery):
    """Настройка единиц измерения"""
    user_id = callback.from_user.id
    
    current_units = await db.fetch_one(
        "SELECT units FROM user_settings WHERE user_id = ?",
        (user_id,)
    )
    
    current = current_units['units'] if current_units else 'kg'
    
    text = f"📏 *Единицы измерения*\n\n"
    text += f"Текущие: {'Килограммы (кг)' if current == 'kg' else 'Фунты (lbs)'}\n\n"
    text += "Выберите систему измерений:"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Килограммы (кг)", 
            callback_data="set_units:kg"
        ),
        InlineKeyboardButton(
            text="⚖️ Фунты (lbs)", 
            callback_data="set_units:lbs"
        )
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="settings")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("set_units:"))
async def set_units(callback: CallbackQuery):
    """Установка единиц измерения"""
    user_id = callback.from_user.id
    units = callback.data.split(":")[1]
    
    # Обновляем настройки
    await db.execute(
        """INSERT OR REPLACE INTO user_settings (user_id, units) 
        VALUES (?, ?)""",
        (user_id, units)
    )
    
    units_text = "килограммы (кг)" if units == 'kg' else "фунты (lbs)"
    await callback.answer(f"Установлены {units_text}!")
    await settings_menu(callback)

@router.callback_query(F.data == "settings_notifications")
async def settings_notifications(callback: CallbackQuery):
    """Настройка уведомлений"""
    user_id = callback.from_user.id
    
    settings = await db.fetch_one(
        """SELECT notifications_enabled, notification_time 
        FROM user_settings WHERE user_id = ?""",
        (user_id,)
    )
    
    enabled = settings['notifications_enabled'] if settings else False
    time = settings['notification_time'] if settings and settings['notification_time'] else '18:00'
    
    text = "🔔 *Настройка уведомлений*\n\n"
    text += f"Статус: {'✅ ВКЛЮЧЕНЫ' if enabled else '❌ ВЫКЛЮЧЕНЫ'}\n"
    if enabled:
        text += f"Время: {time}\n\n"
    
    text += "Бот может отправлять вам:\n"
    text += "• Напоминания о тренировках\n"
    text += "• Уведомления о новых ачивках\n"
    text += "• Еженедельную статистику\n\n"
    text += "Выберите действие:"
    
    builder = InlineKeyboardBuilder()
    
    if enabled:
        builder.row(
            InlineKeyboardButton(text="❌ Выключить", callback_data="toggle_notifications:off"),
            InlineKeyboardButton(text="⏰ Изменить время", callback_data="change_notification_time")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="✅ Включить", callback_data="toggle_notifications:on"),
        )
    
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="settings")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("toggle_notifications:"))
async def toggle_notifications(callback: CallbackQuery):
    """Включение/выключение уведомлений"""
    user_id = callback.from_user.id
    action = callback.data.split(":")[1]
    
    enabled = True if action == 'on' else False
    
    await db.execute(
        """INSERT OR REPLACE INTO user_settings 
        (user_id, notifications_enabled) VALUES (?, ?)""",
        (user_id, enabled)
    )
    
    status = "включены" if enabled else "выключены"
    await callback.answer(f"Уведомления {status}!")
    await settings_notifications(callback)

@router.callback_query(F.data == "change_notification_time")
async def change_notification_time(callback: CallbackQuery, state: FSMContext):
    """Изменение времени уведомлений"""
    await callback.message.answer(
        "⏰ *Установите время для уведомлений*\n\n"
        "Введите время в формате ЧЧ:ММ (например, 18:00 или 09:30):"
    )
    
    await state.set_state(NotificationStates.waiting_notification_time)
    await callback.answer()

@router.message(NotificationStates.waiting_notification_time)
async def process_notification_time(message: Message, state: FSMContext):
    """Обработка времени уведомлений"""
    time_text = message.text.strip()
    
    # Простая валидация времени
    import re
    time_pattern = re.compile(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$')
    
    if not time_pattern.match(time_text):
        await message.answer(
            "❌ Неверный формат времени.\n"
            "Пожалуйста, введите время в формате ЧЧ:ММ (например, 18:00):"
        )
        return
    
    user_id = message.from_user.id
    
    # Сохраняем время
    await db.execute(
        """INSERT OR REPLACE INTO user_settings 
        (user_id, notifications_enabled, notification_time) 
        VALUES (?, ?, ?)""",
        (user_id, True, time_text)
    )
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔔 Настройки уведомлений", callback_data="settings_notifications"),
        InlineKeyboardButton(text="⚙️ Все настройки", callback_data="settings")
    )
    
    await message.answer(
        f"✅ Время уведомлений установлено на {time_text}\n\n"
        f"Теперь вы будете получать уведомления в это время.",
        reply_markup=builder.as_markup()
    )
    
    await state.clear()

@router.callback_query(F.data == "settings_export")
async def settings_export(callback: CallbackQuery):
    """Экспорт данных"""
    from services.export import export_user_data
    import os
    
    await callback.message.edit_text("⏳ Начинаем экспорт ваших данных...")
    
    user_id = callback.from_user.id
    file_path = await export_user_data(user_id)
    
    if file_path and os.path.exists(file_path):
        # Используем FSInputFile для отправки файла
        document = FSInputFile(file_path)
        
        await callback.message.answer_document(
            document=document,
            caption="✅ Ваши данные экспортированы в CSV файл.\n\n"
                   "Файл содержит:\n"
                   "• Все ваши тренировки\n"
                   "• Упражнения\n"
                   "• Достижения"
        )
        
        # Удаляем файл после отправки
        os.remove(file_path)
        logger.info(f"Файл {file_path} удален после отправки")
    else:
        await callback.message.answer(
            "❌ Не удалось экспортировать данные. Попробуйте позже.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="↩️ НАЗАД", callback_data="settings")
            ).as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data == "settings_reset")
async def settings_reset(callback: CallbackQuery):
    """Сброс данных"""
    text = (
        "🔄 *Сброс данных*\n\n"
        "⚠️ *ВНИМАНИЕ!* Это действие необратимо.\n\n"
        "При сбросе будут удалены:\n"
        "• Все ваши тренировки\n"
        "• Упражнения и алиасы\n"
        "• Статистика\n"
        "• Достижения\n\n"
        "Настройки профиля останутся.\n\n"
        "Вы уверены что хотите продолжить?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Нет, отмена", callback_data="settings"),
        InlineKeyboardButton(text="✅ Да, сбросить все", callback_data="confirm_reset_all")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Только тренировки", callback_data="confirm_reset_workouts")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "settings_about")
async def settings_about(callback: CallbackQuery):
    """Информация о боте"""
    text = (
        "ℹ️ *О боте FitnessBot*\n\n"
        "Версия: 2.0\n"
        "Разработчик: @hop31esss\n\n"
        
        "*Возможности:*\n"
        "• 📒 Журнал тренировок\n"
        "• 📊 Статистика и прогресс\n"
        "• 🏆 Таблицы лидеров\n"
        "• 🏅 Ачивки и серии\n"
        "• ⏱️ Таймер\n"
        "• 📅 Календарь\n"
        "• 🔔 Умные уведомления\n\n"
        
        "*Контакты:*\n"
        "Разработчик: @hop31esss\n"
        "Предложения: @hop31esss\n\n"
        
        "Спасибо что используете FitnessBot! 💪"
    )
    
    builder = InlineKeyboardBuilder()
    # КНОПКА ИНСТРУКЦИИ ТЕПЕРЬ РАБОЧАЯ!
    builder.row(
        InlineKeyboardButton(text="📖 ИНСТРУКЦИЯ", callback_data="help"),
        InlineKeyboardButton(text="💡 ПРЕДЛОЖИТЬ", callback_data="suggest_idea")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="settings")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# Обработчики сброса данных
@router.callback_query(F.data == "confirm_reset_all")
async def confirm_reset_all(callback: CallbackQuery):
    """Подтверждение сброса всех данных"""
    user_id = callback.from_user.id
    
    # Удаляем все данные пользователя
    await db.execute("DELETE FROM workouts WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM exercises WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM achievements WHERE user_id = ?", (user_id,))
    await db.execute("DELETE FROM user_stats WHERE user_id = ?", (user_id,))
    
    await callback.message.edit_text(
        "✅ *Все данные сброшены!*\n\n"
        "Ваши тренировки, упражнения, статистика и достижения удалены.\n\n"
        "Можете начать с чистого листа! 🎯",
        reply_markup=get_back_to_settings_keyboard()
    )
    await callback.answer("Данные сброшены")

@router.callback_query(F.data == "confirm_reset_workouts")
async def confirm_reset_workouts(callback: CallbackQuery):
    """Подтверждение сброса только тренировок"""
    user_id = callback.from_user.id
    
    # Удаляем только тренировки
    await db.execute("DELETE FROM workouts WHERE user_id = ?", (user_id,))
    await db.execute("UPDATE user_stats SET total_workouts = 0, current_streak = 0 WHERE user_id = ?", (user_id,))
    
    await callback.message.edit_text(
        "✅ *Тренировки сброшены!*\n\n"
        "Все ваши тренировки удалены, но упражнения, настройки и достижения сохранены.\n\n"
        "Можете начать новую серию тренировок! 💪",
        reply_markup=get_back_to_settings_keyboard()
    )
    await callback.answer("Тренировки сброшены")

    from aiogram.filters import Command

@router.callback_query(F.data == "suggest_feature")
async def suggest_feature(callback: CallbackQuery):
    """Предложить функцию (альтернативное название)"""
    await suggest_idea(callback)  # Используем тот же обработчик

@router.callback_query(F.data == "suggest_idea")
async def suggest_idea(callback: CallbackQuery):
    """Предложить идею для бота"""
    text = (
        "💡 *Предложить идею или улучшение*\n\n"
        "У вас есть идея как улучшить бота? Отлично! 🤩\n\n"
        "📝 *Как отправить идею:*\n"
        "1. Напишите разработчику: @hop31esss\n"
        "2. Опишите вашу идею подробно\n"
        "3. Укажите что именно нужно улучшить\n\n"
        "🎯 *Что можно предложить:*\n"
        "• Новые функции для тренировок\n"
        "• Улучшения интерфейса\n"
        "• Исправление ошибок\n"
        "• Интеграции с другими сервисами\n\n"
        "⭐ *Лучшие идеи будут реализованы!*\n\n"
        "Спасибо за ваше участие! 🚀"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✉️ Написать разработчику", url="https://t.me/hop31esss"),
        InlineKeyboardButton(text="📱 Другие проекты", callback_data="other_projects")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="settings_about"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "other_projects")
async def other_projects(callback: CallbackQuery):
    """Другие проекты разработчика"""
    text = (
        "🚀 *Другие проекты разработчика*\n\n"
        "@hop31esss создает полезные боты и приложения:\n\n"
        "📱 *Текущие проекты:*\n"
        "• FitnessBot - этот бот для тренировок\n"
        "🛠 *В разработке:*\n"
        "• MealPlanner - планировщик питания\n"
        "• HabitTracker - трекер привычек\n\n"
        "💡 *Хотите собственный бот?*\n"
        "Разработаю Telegram бота под ваши задачи!\n"
        "Напишите: @hop31esss"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💡 Предложить идею", callback_data="suggest_idea"),
        InlineKeyboardButton(text="✉️ Связаться", url="https://t.me/hop31esss")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="suggest_idea"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    """Подробная инструкция по использованию бота"""
    text = (
        "📖 *ИНСТРУКЦИЯ ПО ИСПОЛЬЗОВАНИЮ*\n\n"
        
        "🌟 *ОСНОВНЫЕ ФУНКЦИИ*\n\n"
        
        "📋 **Журнал тренировок**\n"
        "• Записывайте упражнения, подходы, вес\n"
        "• Создавайте свои упражнения\n"
        "• Добавляйте алиасы для быстрого ввода\n\n"
        
        "📊 **Прогресс и статистика**\n"
        "• Отслеживайте общий прогресс\n"
        "• Смотрите графики роста\n"
        "• Анализируйте свои достижения\n\n"
        
        "🏆 **Лидерборды**\n"
        "• Глобальный рейтинг всех пользователей\n"
        "• Рейтинг среди друзей\n"
        "• Соревнуйтесь и мотивируйте друг друга\n\n"
        
        "⏱️ **Таймер**\n"
        "• Для отдыха между подходами\n"
        "• Выбирайте время от 30 сек до 15 мин\n\n"
        
        "📅 **Календарь**\n"
        "• Все ваши тренировки по дням\n"
        "• Объем нагрузки каждый день\n\n"
        
        "⭐ **ПРЕМИУМ ФУНКЦИИ**\n\n"
        
        "🏋️ **Калькулятор 1ПМ**\n"
        "• Рассчитывайте максимальный вес\n"
        "• Следите за прогрессом силы\n\n"
        
        "🔥 **Трекер калорий**\n"
        "• База из 100+ продуктов\n"
        "• Расчет БЖУ автоматически\n\n"
        
        "👥 **Друзья и челленджи**\n"
        "• Добавляйте друзей\n"
        "• Создавайте челленджи\n"
        "• Соревнуйтесь в тренировках\n\n"
        
        "🤖 **AI-советы**\n"
        "• Персональные рекомендации\n"
        "• Планы тренировок\n"
        "• Ответы на вопросы\n\n"
        
        "⚙️ **КАК ПОЛЬЗОВАТЬСЯ**\n\n"
        "1️⃣ Нажмите 📋 *Журнал тренировок*\n"
        "2️⃣ Выберите ➕ *Добавить тренировку*\n"
        "3️⃣ Введите упражнение, подходы и вес\n"
        "4️⃣ Следите за прогрессом в 📊 *Статистике*\n\n"
        
        "🎯 **СОВЕТЫ**\n"
        "• Тренируйтесь регулярно\n"
        "• Записывайте все тренировки\n"
        "• Соревнуйтесь с друзьями\n"
        "• Используйте AI-советы\n\n"
        
        "❓ **Есть вопросы?**\n"
        "Пишите разработчику: @hop31esss\n\n"
        
        "Удачных тренировок! 💪"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="◀️ НАЗАД", callback_data="settings_about")
    )
    
    # Добавляем кнопки быстрого доступа
    builder.row(
        InlineKeyboardButton(text="📋 ЖУРНАЛ", callback_data="training_journal"),
        InlineKeyboardButton(text="📊 ПРОГРЕСС", callback_data="progress_stats")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

def get_back_to_settings_keyboard():
    """Клавиатура возврата к настройкам"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    return builder.as_markup()