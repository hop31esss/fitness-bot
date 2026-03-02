from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, date
import logging
import sqlite3

from database.base import db
from keyboards.training import get_exercises_keyboard

router = Router()
logger = logging.getLogger(__name__)

# === ПРОВЕРКА И СОЗДАНИЕ ТАБЛИЦ ===
def ensure_tables():
    """Создает таблицы если их нет"""
    try:
        conn = sqlite3.connect('fitness_bot.db')
        cursor = conn.cursor()
        
        # Таблица тренировок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица упражнений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                exercise_name TEXT NOT NULL,
                exercise_type TEXT DEFAULT 'strength',
                sets INTEGER,
                reps INTEGER,
                weight REAL,
                duration INTEGER,
                distance REAL,
                notes TEXT,
                order_num INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Таблицы для тренировок созданы/проверены")
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблиц: {e}")

# Вызываем при импорте
ensure_tables()

class WorkoutSessionStates(StatesGroup):
    choosing_exercise_type = State()
    entering_exercise_name = State()
    entering_sets = State()
    entering_reps = State()
    entering_weight = State()
    entering_duration = State()
    entering_distance = State()

@router.callback_query(F.data == "start_workout")
async def start_workout(callback: CallbackQuery, state: FSMContext):
    """Начало новой тренировки"""
    user_id = callback.from_user.id
    today = date.today().isoformat()
    current_time = datetime.now().strftime("%H:%M")
    
    try:
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
        logger.error(f"Ошибка: {e}")
        await callback.message.answer("❌ Ошибка создания тренировки")
    
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
                weight = f"{ex['weight']} кг" if ex.get('weight') else "б/в"
                text += f"{i}. {ex['name']}: {ex['sets']}×{ex['reps']} ({weight})\n"
            elif ex['type'] == 'cardio':
                text += f"{i}. {ex['name']}: {ex['duration']} мин, {ex['distance']} км\n"
    else:
        text += "Пока нет упражнений. Добавьте первое!\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ", callback_data="add_to_workout")
    )
    builder.row(
        InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ", callback_data="finish_workout"),
        InlineKeyboardButton(text="❌ ОТМЕНИТЬ", callback_data="cancel_workout")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "add_to_workout")
async def add_to_workout(callback: CallbackQuery, state: FSMContext):
    """Выбор типа упражнения"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ СИЛОВОЕ", callback_data="ex_type_strength"),
        InlineKeyboardButton(text="🏃 КАРДИО", callback_data="ex_type_cardio")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_workout")
    )
    
    await callback.message.edit_text("Выберите тип упражнения:", reply_markup=builder.as_markup())
    await state.set_state(WorkoutSessionStates.choosing_exercise_type)
    await callback.answer()

@router.callback_query(F.data.startswith("ex_type_"))
async def process_exercise_type(callback: CallbackQuery, state: FSMContext):
    """Обработка типа упражнения"""
    ex_type = callback.data.replace("ex_type_", "")
    await state.update_data(current_exercise_type=ex_type)
    
    await callback.message.edit_text("Введите название упражнения:")
    await state.set_state(WorkoutSessionStates.entering_exercise_name)
    await callback.answer()

@router.message(WorkoutSessionStates.entering_exercise_name)
async def process_exercise_name(message: Message, state: FSMContext):
    """Обработка названия упражнения"""
    await state.update_data(exercise_name=message.text.strip())
    data = await state.get_data()
    
    if data['current_exercise_type'] == 'strength':
        await message.answer("Введите количество подходов:")
        await state.set_state(WorkoutSessionStates.entering_sets)
    else:
        await message.answer("Введите длительность (мин):")
        await state.set_state(WorkoutSessionStates.entering_duration)

@router.message(WorkoutSessionStates.entering_sets)
async def process_sets(message: Message, state: FSMContext):
    """Обработка подходов"""
    try:
        sets = int(message.text)
        await state.update_data(sets=sets)
        await message.answer("Введите количество повторений:")
        await state.set_state(WorkoutSessionStates.entering_reps)
    except:
        await message.answer("❌ Введите число")

@router.message(WorkoutSessionStates.entering_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторений"""
    try:
        reps = int(message.text)
        await state.update_data(reps=reps)
        await message.answer("Введите вес (кг) или '-'")
        await state.set_state(WorkoutSessionStates.entering_weight)
    except:
        await message.answer("❌ Введите число")

@router.message(WorkoutSessionStates.entering_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса"""
    weight = None if message.text == '-' else float(message.text)
    await state.update_data(weight=weight)
    await save_exercise(state, message)
    await show_workout_menu(message, state)

@router.message(WorkoutSessionStates.entering_duration)
async def process_duration(message: Message, state: FSMContext):
    """Обработка длительности кардио"""
    try:
        duration = int(message.text)
        await state.update_data(duration=duration)
        
        data = await state.get_data()
        if data['current_exercise_type'] == 'cardio':
            await message.answer("Введите дистанцию (км):")
            await state.set_state(WorkoutSessionStates.entering_distance)
        else:
            await save_exercise(state, message)
            await show_workout_menu(message, state)
    except:
        await message.answer("❌ Введите число")

@router.message(WorkoutSessionStates.entering_distance)
async def process_distance(message: Message, state: FSMContext):
    """Обработка дистанции"""
    try:
        distance = float(message.text)
        await state.update_data(distance=distance)
        await save_exercise(state, message)
        await show_workout_menu(message, state)
    except:
        await message.answer("❌ Введите число")

async def save_exercise(state: FSMContext, message: Message):
    """Сохранить упражнение"""
    data = await state.get_data()
    
    exercise = {
        'name': data['exercise_name'],
        'type': data['current_exercise_type']
    }
    
    if exercise['type'] == 'strength':
        exercise.update({
            'sets': data['sets'],
            'reps': data['reps'],
            'weight': data.get('weight')
        })
    else:
        exercise.update({
            'duration': data.get('duration'),
            'distance': data.get('distance')
        })
    
    exercises = data.get('exercises', [])
    exercises.append(exercise)
    await state.update_data(exercises=exercises)
    
    # Сохраняем в БД
    session_id = data['session_id']
    if exercise['type'] == 'strength':
        await db.execute("""
            INSERT INTO workout_exercises 
            (session_id, exercise_name, exercise_type, sets, reps, weight, order_num)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (session_id, exercise['name'], 'strength', 
              exercise['sets'], exercise['reps'], exercise.get('weight'),
              len(exercises)))
    else:
        await db.execute("""
            INSERT INTO workout_exercises 
            (session_id, exercise_name, exercise_type, duration, distance, order_num)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, exercise['name'], 'cardio',
              exercise.get('duration'), exercise.get('distance'),
              len(exercises)))

@router.callback_query(F.data == "finish_workout")
async def finish_workout(callback: CallbackQuery, state: FSMContext):
    """Завершение тренировки"""
    data = await state.get_data()
    session_id = data['session_id']
    
    await db.execute(
        "UPDATE workout_sessions SET end_time = ? WHERE id = ?",
        (datetime.now().strftime("%H:%M"), session_id)
    )
    
    await callback.message.edit_text(
        "✅ *Тренировка завершена!*\n\nОтличная работа! 💪",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
        ).as_markup()
    )
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_workout")
async def cancel_workout(callback: CallbackQuery, state: FSMContext):
    """Отмена тренировки"""
    await callback.message.edit_text("❌ Тренировка отменена")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "back_to_workout")
async def back_to_workout(callback: CallbackQuery, state: FSMContext):
    """Возврат к меню тренировки"""
    await show_workout_menu(callback.message, state)
    await callback.answer()