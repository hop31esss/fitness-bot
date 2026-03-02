from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database.base import db
from keyboards.training import get_training_menu_keyboard, get_exercises_keyboard

router = Router()

class AddExerciseStates(StatesGroup):
    waiting_exercise_name = State()
    waiting_exercise_alias = State()

# ================ ЖУРНАЛ ТРЕНИРОВОК ================

@router.callback_query(F.data == "training_journal")
async def training_journal(callback: CallbackQuery):
    """Журнал тренировок - главное меню"""
    text = "📒 *Журнал тренировок*\n\nВыберите действие:"
    keyboard = get_training_menu_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

# ================ ИСТОРИЯ ТРЕНИРОВОК ================

@router.callback_query(F.data == "workout_history")
async def workout_history(callback: CallbackQuery):
    """История тренировок (из новых сессий)"""
    user_id = callback.from_user.id
    
    # Получаем тренировки из новой структуры
    sessions = await db.fetch_all("""
        SELECT ws.id, ws.date, ws.start_time, ws.end_time,
               COUNT(we.id) as exercises_count
        FROM workout_sessions ws
        LEFT JOIN workout_exercises we ON ws.id = we.session_id
        WHERE ws.user_id = ?
        GROUP BY ws.id
        ORDER BY ws.date DESC, ws.start_time DESC
        LIMIT 10
    """, (user_id,))
    
    if sessions:
        text = "📋 *История тренировок*\n\n"
        for s in sessions:
            date_str = s['date'][5:] if s['date'] else "?"
            time_str = f" в {s['start_time']}" if s['start_time'] else ""
            exercises = f", {s['exercises_count']} упр." if s['exercises_count'] else ""
            text += f"📅 {date_str}{time_str}{exercises}\n"
    else:
        # Если нет новых, пробуем старые
        old_workouts = await db.fetch_all(
            "SELECT created_at, exercise_name, sets, reps, weight FROM workouts WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
            (user_id,)
        )
        
        if old_workouts:
            text = "📋 *История тренировок (старая)*\n\n"
            for w in old_workouts:
                date = w['created_at'][:16] if w['created_at'] else ""
                weight = f", {w['weight']} кг" if w['weight'] else ""
                text += f"• {date}: {w['exercise_name']} {w['sets']}×{w['reps']}{weight}\n"
        else:
            text = "📋 *История тренировок*\n\nПока нет тренировок"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="➕ НОВАЯ ТРЕНИРОВКА", callback_data="start_workout"),
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="training_journal")
        ).as_markup()
    )
    await callback.answer()

# ================ МОИ УПРАЖНЕНИЯ ================

@router.callback_query(F.data == "my_exercises")
async def my_exercises(callback: CallbackQuery):
    """Мои упражнения"""
    user_id = callback.from_user.id
    
    exercises = await db.fetch_all(
        "SELECT name, alias FROM exercises WHERE user_id = ? ORDER BY name",
        (user_id,)
    )
    
    if exercises:
        text = "💪 *Мои упражнения:*\n\n"
        for i, ex in enumerate(exercises, 1):
            alias = f" ({ex['alias']})" if ex['alias'] else ""
            text += f"{i}. {ex['name']}{alias}\n"
    else:
        text = "📝 У вас пока нет упражнений. Добавьте первое!"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ", callback_data="add_exercise"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="training_journal")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ДОБАВЛЕНИЕ УПРАЖНЕНИЯ ================

@router.callback_query(F.data == "add_exercise")
async def add_exercise_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления упражнения"""
    await callback.message.edit_text(
        "📝 *Добавление упражнения*\n\n"
        "Введите название упражнения:\n\n"
        "Или отправьте /cancel для отмены."
    )
    await state.set_state(AddExerciseStates.waiting_exercise_name)
    await callback.answer()

@router.message(AddExerciseStates.waiting_exercise_name)
async def process_exercise_name(message: Message, state: FSMContext):
    """Обработка названия упражнения"""
    if message.text == "/cancel":
        await message.answer("❌ Добавление отменено.")
        await state.clear()
        return
    
    exercise_name = message.text.strip()
    await state.update_data(exercise_name=exercise_name)
    
    await message.answer(
        f"✅ Название сохранено: {exercise_name}\n\n"
        "Хотите добавить короткое название (алиас)?\n"
        "Отправьте алиас или '-' чтобы пропустить:"
    )
    await state.set_state(AddExerciseStates.waiting_exercise_alias)

@router.message(AddExerciseStates.waiting_exercise_alias)
async def process_exercise_alias(message: Message, state: FSMContext):
    """Обработка алиаса"""
    data = await state.get_data()
    exercise_name = data['exercise_name']
    user_id = message.from_user.id
    
    alias = None if message.text == '-' else message.text.strip()
    
    await db.execute(
        "INSERT INTO exercises (user_id, name, alias) VALUES (?, ?, ?)",
        (user_id, exercise_name, alias)
    )
    
    alias_text = f" (алиас: {alias})" if alias else ""
    
    await message.answer(
        f"✅ *Упражнение добавлено!*\n\n🏋️ {exercise_name}{alias_text}",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📋 В ЖУРНАЛ", callback_data="training_journal")
        ).as_markup()
    )
    await state.clear()