from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database.base import db

router = Router()

@router.callback_query(F.data == "daily_routine")
async def daily_routine_menu(callback: CallbackQuery):
    """Меню режима дня и восстановления"""
    text = (
        "📅 *Режим дня и восстановление*\n\n"
        "Выберите раздел:\n\n"
        "⏰ *Режим дня* - планирование времени для тренировок\n"
        "💤 *Режим восстановления* - сон, растяжка, вода\n"
        "📊 *Мой график* - ваше расписание тренировок\n"
        "🔔 *Напоминания* - настройка уведомлений"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⏰ Режим дня", callback_data="day_schedule"),
        InlineKeyboardButton(text="💤 Восстановление", callback_data="recovery_mode")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Мой график", callback_data="my_schedule"),
        InlineKeyboardButton(text="🔔 Напоминания", callback_data="routine_reminders")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "day_schedule")
async def day_schedule(callback: CallbackQuery):
    """Режим дня - планирование времени для тренировок"""
    user_id = callback.from_user.id
    
    # Получаем статистику тренировок пользователя
    user_stats = await db.fetch_one(
        "SELECT * FROM user_stats WHERE user_id = ?",
        (user_id,)
    )
    
    text = "⏰ *Режим дня - планирование тренировок*\n\n"
    
    if user_stats and user_stats['total_workouts'] > 0:
        # Анализируем привычки пользователя
        workout_times = await db.fetch_all("""
            SELECT strftime('%H', created_at) as hour, COUNT(*) as count
            FROM workouts 
            WHERE user_id = ?
            GROUP BY strftime('%H', created_at)
            ORDER BY count DESC
            LIMIT 3
        """, (user_id,))
        
        if workout_times:
            text += "📊 *Ваши привычки:*\n"
            for time in workout_times:
                hour = int(time['hour'])
                time_text = f"{hour}:00-{hour+1}:00"
                text += f"• {time_text}: {time['count']} тренировок\n"
            text += "\n"
    
    text += (
        "🎯 *Рекомендации по планированию:*\n\n"
        "1. *Утро (6:00-9:00)*\n"
        "   • Кардио и легкие тренировки\n"
        "   • Повышает энергию на весь день\n"
        "   • Лучше для сжигания жира\n\n"
        
        "2. *День (12:00-15:00)*\n"
        "   • Силовые тренировки\n"
        "   • Пик физической активности\n"
        "   • Выше температура тела\n\n"
        
        "3. *Вечер (18:00-21:00)*\n"
        "   • Силовые и объемные тренировки\n"
        "   • Максимальная сила и выносливость\n"
        "   • Больше времени на разминку\n\n"
        
        "💡 *Совет:* Выберите постоянное время тренировок и придерживайтесь его!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Запланировать тренировку", callback_data="schedule_workout"),
        InlineKeyboardButton(text="⏰ Установить время", callback_data="set_training_time")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="daily_routine"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "recovery_mode")
async def recovery_mode(callback: CallbackQuery):
    """Режим восстановления"""
    user_id = callback.from_user.id
    
    # Получаем последние тренировки
    last_workouts = await db.fetch_all("""
        SELECT created_at FROM workouts 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 3
    """, (user_id,))
    
    text = "💤 *Режим восстановления*\n\n"
    
    if last_workouts:
        last_date = datetime.strptime(last_workouts[0]['created_at'][:10], '%Y-%m-%d')
        days_since = (datetime.now() - last_date).days
        
        text += f"📅 Последняя тренировка: {days_since} дней назад\n\n"
        
        if days_since == 0:
            text += "✅ Сегодня уже тренировались - время восстановления!\n\n"
        elif days_since == 1:
            text += "🔄 Вчера тренировались - сегодня легкое восстановление\n\n"
    
    text += (
        "🎯 *Ключевые аспекты восстановления:*\n\n"
        
        "1. *Сон (7-9 часов)*\n"
        "   • Ложитесь до 23:00\n"
        "   • Темная комната, прохладный воздух\n"
        "   • Отказ от гаджетов за час до сна\n\n"
        
        "2. *Вода (2-3 литра в день)*\n"
        "   • Стакан воды после пробуждения\n"
        "   • Пить до, во время и после тренировки\n"
        "   • Рассчитать: 30 мл на 1 кг веса\n\n"
        
        "3. *Растяжка (10-15 мин/день)*\n"
        "   • Утром - динамическая растяжка\n"
        "   • После тренировки - статическая\n"
        "   • Вечером - расслабляющая\n\n"
        
        "4. *Питание для восстановления*\n"
        "   • Белок: 1.6-2.2 г на кг веса\n"
        "   • Углеводы после тренировки\n"
        "   • Омега-3 для уменьшения воспалений\n\n"
        
        "5. *Активное восстановление*\n"
        "   • Легкое кардио (ходьба, велосипед)\n"
        "   • Массаж/самомассаж\n"
        "   • Контрастный душ\n\n"
        
        "💡 *Формула успеха:* Тренировка + Восстановление = Прогресс"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💧 Трекер воды", callback_data="water_tracker"),
        InlineKeyboardButton(text="😴 Трекер сна", callback_data="sleep_tracker")
    )
    builder.row(
        InlineKeyboardButton(text="🧘‍♂️ Упражнения на растяжку", callback_data="stretching_exercises"),
        InlineKeyboardButton(text="📝 План восстановления", callback_data="recovery_plan")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="daily_routine"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "my_schedule")
async def my_schedule(callback: CallbackQuery):
    """Мой график тренировок"""
    user_id = callback.from_user.id
    
    # Получаем тренировки за последнюю неделю
    week_ago = datetime.now() - timedelta(days=7)
    
    workouts = await db.fetch_all("""
        SELECT 
            strftime('%w', created_at) as weekday,
            strftime('%H:%M', created_at) as time,
            exercise_name,
            COUNT(*) as count
        FROM workouts 
        WHERE user_id = ? AND created_at > ?
        GROUP BY strftime('%w', created_at), strftime('%H', created_at)
        ORDER BY weekday, time
    """, (user_id, week_ago))
    
    # Дни недели
    days = ["Вс", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб"]
    
    text = "📊 *Мой график тренировок (последняя неделя)*\n\n"
    
    if workouts:
        # Группируем по дням
        schedule = {}
        for w in workouts:
            day_num = int(w['weekday'])
            day_name = days[day_num]
            time = w['time'][:5]  # Берем только часы:минуты
            
            if day_name not in schedule:
                schedule[day_name] = []
            
            schedule[day_name].append(f"{time} - {w['exercise_name']} ({w['count']} раз)")
        
        # Выводим график
        for day in days:
            if day in schedule:
                text += f"*{day}:*\n"
                for item in schedule[day]:
                    text += f"  • {item}\n"
                text += "\n"
    else:
        text += "У вас еще нет регулярного графика тренировок.\n\n"
        text += "💡 *Совет:* Попробуйте тренироваться в одно и то же время 3 раза в неделю для формирования привычки."
    
    text += "\n📈 *Рекомендация:* Лучше всего тренироваться в одно и то же время дня!"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Установить график", callback_data="set_weekly_schedule"),
        InlineKeyboardButton(text="🔔 Напоминания", callback_data="routine_reminders")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="daily_routine"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "routine_reminders")
async def routine_reminders(callback: CallbackQuery):
    """Напоминания для режима дня"""
    text = (
        "🔔 *Напоминания для режима дня*\n\n"
        "Настройте напоминания для поддержания режима:\n\n"
        
        "⏰ *Для тренировок:*\n"
        "• За 1 час до тренировки\n"
        "• За 30 минут до тренировки\n"
        "• За 10 минут до тренировки\n\n"
        
        "💧 *Для воды:*\n"
        "• Каждые 2 часа (с 8:00 до 20:00)\n"
        "• После пробуждения\n"
        "• Перед сном\n\n"
        
        "😴 *Для сна:*\n"
        "• За 1 час до сна (отдых)\n"
        "• За 30 минут до сна (отход ко сну)\n"
        "• Утреннее пробуждение\n\n"
        
        "🧘‍♂️ *Для растяжки:*\n"
        "• Утренняя растяжка\n"
        "• После тренировки\n"
        "• Вечерняя расслабляющая\n\n"
        
        "⚙️ *Настроить можно в разделе 'Настройки' → 'Уведомления'*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚙️ Настройки уведомлений", callback_data="settings_notifications"),
        InlineKeyboardButton(text="📱 Быстрые напоминания", callback_data="quick_reminders")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="daily_routine"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# Заглушки для остальных кнопок
@router.callback_query(F.data.in_([
    "schedule_workout", "set_training_time", "water_tracker",
    "sleep_tracker", "stretching_exercises", "recovery_plan",
    "set_weekly_schedule", "quick_reminders"
]))
async def feature_coming_soon(callback: CallbackQuery):
    """Функции в разработке"""
    feature_names = {
        "schedule_workout": "Планирование тренировки",
        "set_training_time": "Установка времени тренировок",
        "water_tracker": "Трекер воды",
        "sleep_tracker": "Трекер сна",
        "stretching_exercises": "Упражнения на растяжку",
        "recovery_plan": "План восстановления",
        "set_weekly_schedule": "Установка недельного графика",
        "quick_reminders": "Быстрые напоминания"
    }
    
    feature_name = feature_names.get(callback.data, "Эта функция")
    
    await callback.answer(f"{feature_name} скоро будет доступна! 🚀")