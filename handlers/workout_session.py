from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, date
import logging

from database.base import db
from keyboards.training import get_exercises_keyboard

router = Router()
logger = logging.getLogger(__name__)

# Вызываем при импорте модуля
#import asyncio
#asyncio.create_task(ensure_tables_exist())

# ================ СОСТОЯНИЯ ================

class WorkoutSessionStates(StatesGroup):
    choosing_action = State()
    adding_exercise = State()
    choosing_exercise_type = State()
    entering_exercise_name = State()
    entering_sets = State()
    entering_reps = State()
    entering_weight = State()
    entering_duration = State()
    entering_distance = State()
    entering_speed = State()
    entering_notes = State()

# ================ НАЧАЛО ТРЕНИРОВКИ ================

@router.callback_query(F.data == "start_workout")
async def start_workout(callback: CallbackQuery, state: FSMContext):
    """Начало новой тренировки"""
    user_id = callback.from_user.id
    today = date.today().isoformat()
    current_time = datetime.now().strftime("%H:%M")
    
    try:
        # Сначала убедимся, что таблица существует
        await ensure_tables_exist()
        
        # Создаем новую тренировку
        await db.execute(
            "INSERT INTO workout_sessions (user_id, date, start_time) VALUES (?, ?, ?)",
            (user_id, today, current_time)
        )
        
        result = await db.fetch_one("SELECT last_insert_rowid() as id")
        session_id = result['id']
        
        await state.update_data(
            session_id=session_id,
            exercises=[]
        )
        
        await show_workout_menu(callback.message, state)
    except Exception as e:
        logger.error(f"Ошибка при создании тренировки: {e}")
        await callback.message.answer("❌ Не удалось создать тренировку. Попробуйте позже.")
    
    await callback.answer()

async def show_workout_menu(message, state: FSMContext):
    """Показать меню тренировки"""
    data = await state.get_data()
    exercises = data.get('exercises', [])
    
    text = "🏋️ *ТЕКУЩАЯ ТРЕНИРОВКА*\n\n"
    
    if exercises:
        text += "*Упражнения:*\n"
        for i, ex in enumerate(exercises, 1):
            if ex['type'] == 'strength':
                text += f"{i}. {ex['name']}: {ex['sets']}×{ex['reps']} ({ex['weight']} кг)\n"
            elif ex['type'] == 'cardio':
                text += f"{i}. {ex['name']}: {ex['duration']} мин, {ex['distance']} км\n"
    else:
        text += "Пока нет упражнений. Добавьте первое!\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ УПРАЖНЕНИЕ", callback_data="add_to_workout")
    )
    builder.row(
        InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ ТРЕНИРОВКУ", callback_data="finish_workout"),
        InlineKeyboardButton(text="❌ ОТМЕНИТЬ", callback_data="cancel_workout")
    )
    
    await message.edit_text(text, reply_markup=builder.as_markup())

# ================ ДОБАВЛЕНИЕ УПРАЖНЕНИЯ ================

@router.callback_query(F.data == "add_to_workout")
async def add_to_workout(callback: CallbackQuery, state: FSMContext):
    """Выбор типа упражнения"""
    text = "Выберите тип упражнения:"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ СИЛОВОЕ", callback_data="exercise_type_strength"),
        InlineKeyboardButton(text="🏃 КАРДИО", callback_data="exercise_type_cardio")
    )
    builder.row(
        InlineKeyboardButton(text="🧘 РАСТЯЖКА", callback_data="exercise_type_stretch"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_workout")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(WorkoutSessionStates.choosing_exercise_type)
    await callback.answer()

@router.callback_query(F.data.startswith("exercise_type_"))
async def process_exercise_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа упражнения"""
    ex_type = callback.data.replace("exercise_type_", "")
    await state.update_data(current_exercise_type=ex_type)
    
    # Получаем список упражнений пользователя
    user_id = callback.from_user.id
    exercises = await db.fetch_all(
        "SELECT name, alias FROM exercises WHERE user_id = ?",
        (user_id,)
    )
    
    if exercises:
        text = "Выберите упражнение из списка или введите новое:"
        keyboard = get_exercises_keyboard(exercises, context="workout")
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text("Введите название упражнения:")
    
    await state.set_state(WorkoutSessionStates.adding_exercise)
    await callback.answer()

@router.callback_query(F.data.startswith("select_exercise_workout:"))
async def select_workout_exercise(callback: CallbackQuery, state: FSMContext):
    """Выбор существующего упражнения"""
    exercise_name = callback.data.split(":", 1)[1]
    await state.update_data(exercise_name=exercise_name)
    
    data = await state.get_data()
    ex_type = data.get('current_exercise_type')
    
    if ex_type == 'strength':
        await callback.message.edit_text("Введите количество подходов:")
        await state.set_state(WorkoutSessionStates.entering_sets)
    elif ex_type == 'cardio':
        await callback.message.edit_text("Введите длительность (в минутах):")
        await state.set_state(WorkoutSessionStates.entering_duration)
    else:  # stretch
        await callback.message.edit_text("Введите длительность (в минутах):")
        await state.set_state(WorkoutSessionStates.entering_duration)
    
    await callback.answer()

@router.callback_query(F.data == "new_exercise_workout")
async def new_workout_exercise(callback: CallbackQuery, state: FSMContext):
    """Новое упражнение"""
    await callback.message.edit_text("Введите название упражнения:")
    await state.set_state(WorkoutSessionStates.entering_exercise_name)
    await callback.answer()

# ================ ВВОД ПАРАМЕТРОВ ================

@router.message(WorkoutSessionStates.entering_exercise_name)
async def process_exercise_name(message: Message, state: FSMContext):
    """Обработка названия упражнения"""
    exercise_name = message.text.strip()
    await state.update_data(exercise_name=exercise_name)
    
    data = await state.get_data()
    ex_type = data.get('current_exercise_type')
    
    if ex_type == 'strength':
        await message.answer("Введите количество подходов:")
        await state.set_state(WorkoutSessionStates.entering_sets)
    elif ex_type == 'cardio':
        await message.answer("Введите длительность (в минутах):")
        await state.set_state(WorkoutSessionStates.entering_duration)
    else:  # stretch
        await message.answer("Введите длительность (в минутах):")
        await state.set_state(WorkoutSessionStates.entering_duration)

@router.message(WorkoutSessionStates.entering_sets)
async def process_sets(message: Message, state: FSMContext):
    """Обработка подходов"""
    try:
        sets = int(message.text)
        if sets <= 0:
            raise ValueError
        await state.update_data(sets=sets)
        await message.answer("Введите количество повторений:")
        await state.set_state(WorkoutSessionStates.entering_reps)
    except ValueError:
        await message.answer("❌ Введите корректное число подходов:")

@router.message(WorkoutSessionStates.entering_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторений"""
    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
        await state.update_data(reps=reps)
        await message.answer("Введите вес (кг) или '-' если без веса:")
        await state.set_state(WorkoutSessionStates.entering_weight)
    except ValueError:
        await message.answer("❌ Введите корректное число повторений:")

@router.message(WorkoutSessionStates.entering_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса"""
    weight_text = message.text.strip()
    
    # Обработка веса
    if weight_text == '-':
        weight = None
    else:
        try:
            weight = float(weight_text.replace(',', '.'))
            if weight <= 0:
                raise ValueError
        except ValueError:
            await message.answer("❌ Введите корректный вес (например: 80 или 80.5) или '-'")
            return
    
    await state.update_data(weight=weight)
    await save_exercise_to_session(state, message)
    await show_workout_menu(message, state)

@router.message(WorkoutSessionStates.entering_duration)
async def process_duration(message: Message, state: FSMContext):
    """Обработка длительности для кардио"""
    try:
        duration = int(message.text)
        if duration <= 0:
            raise ValueError
        await state.update_data(duration=duration)
        
        data = await state.get_data()
        if data.get('current_exercise_type') == 'cardio':
            await message.answer("Введите дистанцию (км):")
            await state.set_state(WorkoutSessionStates.entering_distance)
        else:  # stretch
            await save_exercise_to_session(state, message)
            await show_workout_menu(message, state)
    except ValueError:
        await message.answer("❌ Введите корректную длительность:")

@router.message(WorkoutSessionStates.entering_distance)
async def process_distance(message: Message, state: FSMContext):
    """Обработка дистанции для кардио"""
    try:
        distance = float(message.text.replace(',', '.'))
        if distance <= 0:
            raise ValueError
        await state.update_data(distance=distance)
        await save_exercise_to_session(state, message)
        await show_workout_menu(message, state)
    except ValueError:
        await message.answer("❌ Введите корректную дистанцию:")

async def save_exercise_to_session(state: FSMContext, message: Message):
    """Сохранить упражнение в текущую тренировку"""
    data = await state.get_data()
    
    exercise = {
        'name': data.get('exercise_name'),
        'type': data.get('current_exercise_type')
    }
    
    if exercise['type'] == 'strength':
        exercise.update({
            'sets': data.get('sets'),
            'reps': data.get('reps'),
            'weight': data.get('weight')  # Теперь вес сохраняется!
        })
    elif exercise['type'] == 'cardio':
        exercise.update({
            'duration': data.get('duration'),
            'distance': data.get('distance')
        })
    else:  # stretch
        exercise.update({
            'duration': data.get('duration')
        })
    
    exercises = data.get('exercises', [])
    exercises.append(exercise)
    await state.update_data(exercises=exercises)
    
    # Сохраняем в базу
    session_id = data['session_id']
    order_num = len(exercises)
    
    if exercise['type'] == 'strength':
        await db.execute("""
            INSERT INTO workout_exercises 
            (session_id, exercise_name, exercise_type, sets, reps, weight, order_num)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, exercise['name'], 'strength', 
              exercise['sets'], exercise['reps'], exercise.get('weight'),
              order_num))
    elif exercise['type'] == 'cardio':
        await db.execute("""
            INSERT INTO workout_exercises 
            (session_id, exercise_name, exercise_type, duration, distance, order_num)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, exercise['name'], 'cardio',
              exercise.get('duration'), exercise.get('distance'),
              order_num))
    else:  # stretch
        await db.execute("""
            INSERT INTO workout_exercises 
            (session_id, exercise_name, exercise_type, duration, order_num)
            VALUES (?, ?, ?, ?, ?)
        """, (session_id, exercise['name'], 'stretch',
              exercise.get('duration'), order_num))

# ================ ЗАВЕРШЕНИЕ ТРЕНИРОВКИ ================

@router.callback_query(F.data == "finish_workout")
async def finish_workout(callback: CallbackQuery, state: FSMContext):
    """Завершение тренировки"""
    data = await state.get_data()
    session_id = data['session_id']
    exercises = data.get('exercises', [])
    
    # Обновляем время окончания
    await db.execute(
        "UPDATE workout_sessions SET end_time = ? WHERE id = ?",
        (datetime.now().strftime("%H:%M"), session_id)
    )
    
    # Статистика
    strength_count = sum(1 for e in exercises if e['type'] == 'strength')
    cardio_count = sum(1 for e in exercises if e['type'] == 'cardio')
    stretch_count = sum(1 for e in exercises if e['type'] == 'stretch')
    
    text = (
        f"✅ *Тренировка завершена!*\n\n"
        f"📊 *Статистика:*\n"
        f"🏋️ Силовых упражнений: {strength_count}\n"
        f"🏃 Кардио: {cardio_count}\n"
        f"🧘 Растяжка: {stretch_count}\n"
        f"📝 Всего упражнений: {len(exercises)}\n\n"
        f"💪 Отличная работа!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 ИСТОРИЯ", callback_data="workout_history"),
        InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_workout")
async def cancel_workout(callback: CallbackQuery, state: FSMContext):
    """Отмена тренировки"""
    data = await state.get_data()
    session_id = data.get('session_id')
    
    if session_id:
        await db.execute("DELETE FROM workout_exercises WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM workout_sessions WHERE id = ?", (session_id,))
    
    await callback.message.edit_text(
        "❌ Тренировка отменена.",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
        ).as_markup()
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "back_to_workout")
async def back_to_workout(callback: CallbackQuery, state: FSMContext):
    """Возврат к меню тренировки"""
    # Отправляем новое сообщение вместо редактирования
    await show_workout_menu(callback.message, state)
    await callback.answer()

# ================ ИСТОРИЯ ТРЕНИРОВОК (ОБНОВЛЕННАЯ) ================

@router.callback_query(F.data == "workout_history")
async def workout_history(callback: CallbackQuery):
    """История тренировок"""
    user_id = callback.from_user.id
    
    # Получаем все тренировки с упражнениями
    sessions = await db.fetch_all("""
        SELECT ws.id, ws.date, ws.start_time, ws.end_time,
               COUNT(we.id) as exercise_count,
               SUM(CASE WHEN we.exercise_type = 'strength' THEN 1 ELSE 0 END) as strength_count,
               SUM(CASE WHEN we.exercise_type = 'cardio' THEN 1 ELSE 0 END) as cardio_count
        FROM workout_sessions ws
        LEFT JOIN workout_exercises we ON ws.id = we.session_id
        WHERE ws.user_id = ?
        GROUP BY ws.id
        ORDER BY ws.date DESC, ws.start_time DESC
        LIMIT 10
    """, (user_id,))
    
    if not sessions:
        text = "📋 *История тренировок*\n\nУ вас пока нет тренировок. Начните первую!"
    else:
        text = "📋 *История тренировок*\n\n"
        
        for session in sessions:
            date_str = session['date'][5:] if session['date'] else "?"
            time_str = f"{session['start_time']}" if session['start_time'] else ""
            
            text += f"📅 *{date_str}* {time_str}\n"
            text += f"   🏋️ {session['strength_count']} силовых | 🏃 {session['cardio_count']} кардио\n"
            text += f"   📊 Всего упражнений: {session['exercise_count']}\n\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ НОВАЯ ТРЕНИРОВКА", callback_data="start_workout"),
        InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

async def show_workout_menu(message, state: FSMContext):
    """Показать меню тренировки"""
    data = await state.get_data()
    exercises = data.get('exercises', [])
    
    text = "🏋️ *ТЕКУЩАЯ ТРЕНИРОВКА*\n\n"
    
    if exercises:
        text += "*Упражнения:*\n"
        for i, ex in enumerate(exercises, 1):
            if ex['type'] == 'strength':
                # Показываем вес, если он есть
                if ex.get('weight'):
                    weight_text = f"{ex['weight']} кг"
                else:
                    weight_text = "б/в"
                text += f"{i}. {ex['name']}: {ex['sets']}×{ex['reps']} ({weight_text})\n"
            elif ex['type'] == 'cardio':
                text += f"{i}. {ex['name']}: {ex['duration']} мин, {ex['distance']} км\n"
            else:  # stretch
                text += f"{i}. {ex['name']}: {ex['duration']} мин (растяжка)\n"
    else:
        text += "Пока нет упражнений. Добавьте первое!\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ УПРАЖНЕНИЕ", callback_data="add_to_workout")
    )
    builder.row(
        InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ ТРЕНИРОВКУ", callback_data="finish_workout"),
        InlineKeyboardButton(text="❌ ОТМЕНИТЬ", callback_data="cancel_workout")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())