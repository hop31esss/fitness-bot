from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import calendar

from database.base import db

router = Router()

@router.callback_query(F.data == "calendar")
async def show_calendar(callback: CallbackQuery):
    """Календарь с кликабельными днями"""
    user_id = callback.from_user.id
    now = datetime.now()
    
    # Получаем статистику за прошлый месяц
    last_month = now.month - 1 if now.month > 1 else 12
    last_year = now.year if now.month > 1 else now.year - 1
    
    if last_month == 12:
        last_month_first = datetime(last_year, last_month, 1)
        last_month_last = datetime(last_year + 1, 1, 1) - timedelta(days=1)
    else:
        last_month_first = datetime(last_year, last_month, 1)
        last_month_last = datetime(last_year, last_month + 1, 1) - timedelta(days=1)
    
    # Тренировки за прошлый месяц
    last_month_workouts = await db.fetch_all("""
        SELECT COUNT(*) as count, SUM(sets * reps * COALESCE(weight, 1)) as volume
        FROM workouts 
        WHERE user_id = ? 
            AND date(created_at) BETWEEN date(?) AND date(?)
    """, (user_id, last_month_first, last_month_last))
    
    # Тренировки за текущий месяц
    current_month_first = datetime(now.year, now.month, 1)
    if now.month == 12:
        current_month_last = datetime(now.year + 1, 1, 1) - timedelta(days=1)
    else:
        current_month_last = datetime(now.year, now.month + 1, 1) - timedelta(days=1)
    
    # Получаем данные из новой системы (тренировочные сессии)
    workouts = await db.fetch_all("""
        SELECT 
            ws.date as workout_date,
            COUNT(we.id) as workout_count,
            SUM(we.sets * we.reps * COALESCE(we.weight, 1)) as total_volume
        FROM workout_sessions ws
        LEFT JOIN workout_exercises we ON ws.id = we.session_id
        WHERE ws.user_id = ? 
            AND ws.date BETWEEN ? AND ?
        GROUP BY ws.date
        ORDER BY ws.date
    """, (user_id, current_month_first, current_month_last))
    
    # Словарь для быстрого доступа
    workout_dict = {}
    for w in workouts:
        workout_dict[w['workout_date']] = {
            'count': w['workout_count'],
            'volume': w['total_volume']
        }
    
    # Создаем календарь
    cal = calendar.monthcalendar(now.year, now.month)
    month_name = calendar.month_name[now.month]
    
    # Формируем текст
    text = f"📅 *Календарь тренировок - {month_name} {now.year}*\n\n"
    
    # Статистика прошлого месяца
    if last_month_workouts and last_month_workouts[0]['count']:
        last_month_name = calendar.month_name[last_month]
        last_count = last_month_workouts[0]['count']
        last_volume = int(last_month_workouts[0]['volume'] or 0)
        text += f"📊 *{last_month_name}:* {last_count} тренировок, {last_volume:,} кг\n\n"
    
    text += "*Нажми на день, чтобы посмотреть детали:*\n"
    
    # Создаем клавиатуру с днями
    builder = InlineKeyboardBuilder()
    
    # Заголовки дней недели (некликабельные)
    week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for day in week_days:
        builder.button(text=day, callback_data="ignore")
    
    builder.adjust(7)  # 7 кнопок в ряду
    
    # Добавляем дни
    for week in cal:
        for day in week:
            if day == 0:
                # Пустой день
                builder.button(text=" ", callback_data="ignore")
            else:
                current_date = f"{now.year}-{now.month:02d}-{day:02d}"
                
                if current_date in workout_dict:
                    # День с тренировкой
                    info = workout_dict[current_date]
                    count = info['count']
                    volume = int(info['volume'] or 0)
                    
                    # Определяем цвет/эмодзи
                    if count >= 3:
                        emoji = "🔥"  # Много тренировок
                    elif count == 2:
                        emoji = "💪"  # Средне
                    else:
                        emoji = "✅"  # Одна тренировка
                    
                    text_btn = f"{emoji}{day}"
                    callback_data = f"day_detail:{current_date}"
                else:
                    # День без тренировки
                    text_btn = f" {day} "
                    callback_data = f"day_empty:{current_date}"
                
                builder.button(text=text_btn, callback_data=callback_data)
    
    builder.adjust(7)  # Всегда 7 кнопок в ряду
    
    # Статистика текущего месяца
    total_workouts = sum([w['workout_count'] for w in workouts])
    total_volume = sum([int(w['total_volume'] or 0) for w in workouts])
    
    text += f"\n📊 *{month_name} (текущий):*\n"
    text += f"• Дней с тренировками: {len(workouts)}\n"
    text += f"• Всего тренировок: {total_workouts}\n"
    text += f"• Общий объем: {total_volume:,} кг\n"
    
    if len(workouts) > 0:
        avg_per_day = total_volume / len(workouts)
        text += f"• Средний объем за день: {int(avg_per_day):,} кг\n"
    
    # Кнопки навигации
    prev_month = now.month - 1 if now.month > 1 else 12
    prev_year = now.year if now.month > 1 else now.year - 1
    next_month = now.month + 1 if now.month < 12 else 1
    next_year = now.year if now.month < 12 else now.year + 1
    
    builder.row(
        InlineKeyboardButton(
            text="◀️ Предыдущий", 
            callback_data=f"month_nav:{prev_year}:{prev_month}"
        ),
        InlineKeyboardButton(
            text="▶️ Следующий", 
            callback_data=f"month_nav:{next_year}:{next_month}"
        )
    )
    
    builder.row(
        InlineKeyboardButton(text="📊 Общая статистика", callback_data="stats"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("day_detail:"))
async def show_day_detail(callback: CallbackQuery):
    """Детали дня с тренировками"""
    user_id = callback.from_user.id
    date_str = callback.data.split(":")[1]
    
    # Получаем упражнения из тренировочной сессии за этот день
    workouts = await db.fetch_all("""
        SELECT 
            we.exercise_name,
            we.sets,
            we.reps,
            we.weight,
            ws.start_time as time
        FROM workout_sessions ws
        JOIN workout_exercises we ON ws.id = we.session_id
        WHERE ws.user_id = ? 
            AND ws.date = ?
        ORDER BY ws.start_time, we.order_num
    """, (user_id, date_str))
    
    # Получаем общую статистику дня
    day_stats = await db.fetch_one("""
        SELECT 
            COUNT(*) as workout_count,
            SUM(sets * reps * COALESCE(weight, 1)) as total_volume,
            SUM(sets) as total_sets,
            SUM(reps) as total_reps
        FROM workouts 
        WHERE user_id = ? 
            AND date(created_at) = date(?)
    """, (user_id, date_str))
    
    # Форматируем дату
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
    month_name = calendar.month_name[date_obj.month]
    
    text = f"📅 *Детали дня: {day_name}, {date_obj.day} {month_name} {date_obj.year}*\n\n"
    
    if workouts:
        text += f"🏋️ *Тренировок: {day_stats['workout_count']}*\n"
        text += f"⚖️ *Общий объем: {int(day_stats['total_volume'] or 0):,} кг*\n"
        text += f"📊 *Подходы: {day_stats['total_sets'] or 0} | Повторения: {day_stats['total_reps'] or 0}*\n\n"
        
        text += "*Упражнения:*\n"
        for i, workout in enumerate(workouts, 1):
            weight_text = f"{workout['weight']} кг" if workout['weight'] else "без веса"
            time = workout['created_at'][11:16] if 'created_at' in workout else ""
            
            text += f"{i}. *{workout['exercise_name']}*\n"
            text += f"   {workout['sets']}×{workout['reps']} | {weight_text}"
            if time:
                text += f" | {time}"
            text += "\n"
    else:
        text += "В этот день не было тренировок.\n"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Вернуться в календарь", callback_data="calendar"),
        InlineKeyboardButton(text="➕ Добавить тренировку", callback_data="add_workout")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("day_empty:"))
async def show_empty_day(callback: CallbackQuery):
    """День без тренировок"""
    date_str = callback.data.split(":")[1]
    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
    day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
    month_name = calendar.month_name[date_obj.month]
    
    text = f"📅 *{day_name}, {date_obj.day} {month_name} {date_obj.year}*\n\n"
    text += "В этот день не было тренировок.\n\n"
    text += "Хотите добавить тренировку?"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить тренировку", callback_data=f"add_workout_to_day:{date_str}"),
        InlineKeyboardButton(text="📅 Календарь", callback_data="calendar")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("month_nav:"))
async def navigate_month(callback: CallbackQuery):
    """Навигация по месяцам"""
    try:
        _, year_str, month_str = callback.data.split(":")
        year = int(year_str)
        month = int(month_str)
        
        user_id = callback.from_user.id
        
        # Статистика за предыдущий месяц относительно выбранного
        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        
        if prev_month == 12:
            prev_month_first = datetime(prev_year, prev_month, 1)
            prev_month_last = datetime(prev_year + 1, 1, 1) - timedelta(days=1)
        else:
            prev_month_first = datetime(prev_year, prev_month, 1)
            prev_month_last = datetime(prev_year, prev_month + 1, 1) - timedelta(days=1)
        
        # Тренировки за предыдущий месяц
        prev_month_workouts = await db.fetch_all("""
            SELECT COUNT(*) as count, SUM(sets * reps * COALESCE(weight, 1)) as volume
            FROM workouts 
            WHERE user_id = ? 
                AND date(created_at) BETWEEN date(?) AND date(?)
        """, (user_id, prev_month_first, prev_month_last))
        
        # Тренировки за выбранный месяц
        month_first = datetime(year, month, 1)
        if month == 12:
            month_last = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_last = datetime(year, month + 1, 1) - timedelta(days=1)
        
        workouts = await db.fetch_all("""
            SELECT 
                ws.date as workout_date,
                COUNT(we.id) as workout_count,
                SUM(we.sets * we.reps * COALESCE(we.weight, 1)) as total_volume
            FROM workout_sessions ws
            LEFT JOIN workout_exercises we ON ws.id = we.session_id
            WHERE ws.user_id = ? 
                AND ws.date BETWEEN ? AND ?
            GROUP BY ws.date
            ORDER BY ws.date
        """, (user_id, month_first, month_last))
        
        # Словарь тренировок
        workout_dict = {}
        for w in workouts:
            workout_dict[w['workout_date']] = {
                'count': w['workout_count'],
                'volume': w['total_volume']
            }
        
        # Календарь
        cal = calendar.monthcalendar(year, month)
        month_name = calendar.month_name[month]
        
        # Текст
        text = f"📅 *Календарь тренировок - {month_name} {year}*\n\n"
        
        # Статистика прошлого месяца
        if prev_month_workouts and prev_month_workouts[0]['count']:
            prev_month_name = calendar.month_name[prev_month]
            prev_count = prev_month_workouts[0]['count']
            prev_volume = int(prev_month_workouts[0]['volume'] or 0)
            text += f"📊 *{prev_month_name}:* {prev_count} тренировок, {prev_volume:,} кг\n\n"
        
        text += "*Нажми на день, чтобы посмотреть детали:*\n"
        
        # Клавиатура с днями
        builder = InlineKeyboardBuilder()
        
        # Дни недели
        week_days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        for day in week_days:
            builder.button(text=day, callback_data="ignore")
        
        builder.adjust(7)
        
        # Дни месяца
        for week in cal:
            for day in week:
                if day == 0:
                    builder.button(text=" ", callback_data="ignore")
                else:
                    current_date = f"{year}-{month:02d}-{day:02d}"
                    
                    if current_date in workout_dict:
                        info = workout_dict[current_date]
                        count = info['count']
                        
                        if count >= 3:
                            emoji = "🔥"
                        elif count == 2:
                            emoji = "💪"
                        else:
                            emoji = "✅"
                        
                        text_btn = f"{emoji}{day}"
                        callback_data = f"day_detail:{current_date}"
                    else:
                        text_btn = f" {day} "
                        callback_data = f"day_empty:{current_date}"
                    
                    builder.button(text=text_btn, callback_data=callback_data)
        
        builder.adjust(7)
        
        # Статистика месяца
        total_workouts = sum([w['workout_count'] for w in workouts])
        total_volume = sum([int(w['total_volume'] or 0) for w in workouts])
        
        text += f"\n📊 *{month_name}:*\n"
        text += f"• Дней с тренировками: {len(workouts)}\n"
        text += f"• Всего тренировок: {total_workouts}\n"
        text += f"• Общий объем: {total_volume:,} кг\n"
        
        # Навигация
        prev_prev_month = month - 1 if month > 1 else 12
        prev_prev_year = year if month > 1 else year - 1
        next_next_month = month + 1 if month < 12 else 1
        next_next_year = year if month < 12 else year + 1
        
        builder.row(
            InlineKeyboardButton(
                text="◀️ Предыдущий", 
                callback_data=f"month_nav:{prev_prev_year}:{prev_prev_month}"
            ),
            InlineKeyboardButton(
                text="▶️ Следующий", 
                callback_data=f"month_nav:{next_next_year}:{next_next_month}"
            )
        )
        
        builder.row(
            InlineKeyboardButton(text="📅 Текущий месяц", callback_data="calendar"),
            InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
        )
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        await callback.answer()
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

# Заглушка для игнорируемых callback-ов
@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    """Игнорируем ненужные callback-и"""
    await callback.answer()