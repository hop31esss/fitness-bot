from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database.base import db

router = Router()

class WorkoutStates(StatesGroup):
    waiting_exercise = State()
    waiting_sets = State()
    waiting_reps = State()
    waiting_weight = State()

class AddExerciseStates(StatesGroup):
    waiting_exercise_name = State()
    waiting_exercise_alias = State()

@router.callback_query(F.data == "training_journal")
async def training_journal(callback: CallbackQuery):
    """Журнал тренировок - главное меню"""
    text = "📒 *Журнал тренировок*\n\nВыберите действие:"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ НАЧАТЬ ТРЕНИРОВКУ", callback_data="start_workout"),  # ВЕДЁТ В СЕССИИ
        InlineKeyboardButton(text="📋 ИСТОРИЯ", callback_data="workout_history")
    )
    builder.row(
        InlineKeyboardButton(text="💪 МОИ УПРАЖНЕНИЯ", callback_data="my_exercises"),
        InlineKeyboardButton(text="📝 ДОБАВИТЬ УПРАЖНЕНИЕ", callback_data="add_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "add_exercise")
async def add_exercise_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления упражнения"""
    await callback.message.edit_text(
        "📝 *Добавление упражнения*\n\n"
        "Введите название упражнения (например: Жим лежа):\n\n"
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
        "Например: 'Жим'\n\n"
        "Отправьте алиас или '-' чтобы пропустить:"
    )
    await state.set_state(AddExerciseStates.waiting_exercise_alias)

@router.callback_query(F.data == "my_exercises")
async def my_exercises(callback: CallbackQuery):
    """Мои упражнения - список упражнений пользователя"""
    user_id = callback.from_user.id
    
    # Получаем список упражнений пользователя
    exercises = await db.fetch_all(
        "SELECT name, alias FROM exercises WHERE user_id = ? ORDER BY name",
        (user_id,)
    )
    
    if exercises:
        text = "💪 *Мои упражнения:*\n\n"
        for i, ex in enumerate(exercises, 1):
            alias = f" ({ex['alias']})" if ex['alias'] else ""
            text += f"{i}. {ex['name']}{alias}\n"
        text += f"\n📊 Всего упражнений: {len(exercises)}"
    else:
        text = "📝 *Мои упражнения*\n\nУ вас пока нет сохраненных упражнений.\n\nДобавьте первое упражнение!"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ", callback_data="add_exercise"),
        InlineKeyboardButton(text="🔤 АЛИАСЫ", callback_data="exercise_aliases")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="training_journal")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.message(AddExerciseStates.waiting_exercise_alias)
async def process_exercise_alias(message: Message, state: FSMContext):
    """Обработка алиаса упражнения"""
    if message.text == "/cancel":
        await message.answer("❌ Добавление отменено.")
        await state.clear()
        return
    
    data = await state.get_data()
    exercise_name = data['exercise_name']
    user_id = message.from_user.id
    
    alias = None if message.text == '-' else message.text.strip()
    
    # Сохраняем упражнение
    await db.execute(
        "INSERT INTO exercises (user_id, name, alias) VALUES (?, ?, ?)",
        (user_id, exercise_name, alias)
    )
    
    alias_text = f" (алиас: {alias})" if alias else ""
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ЕЩЁ", callback_data="add_exercise"),
        InlineKeyboardButton(text="📋 МОИ УПРАЖНЕНИЯ", callback_data="my_exercises")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ В ЖУРНАЛ", callback_data="training_journal")
    )
    
    await message.answer(
        f"✅ *Упражнение добавлено!*\n\n"
        f"🏋️ {exercise_name}{alias_text}",
        reply_markup=builder.as_markup()
    )
    await state.clear()
@router.callback_query(F.data == "add_workout")
async def add_workout_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления тренировки"""
    await callback.message.edit_text(
        "🏋️ *Добавление тренировки*\n\n"
        "Введите название упражнения:"
    )
    await state.set_state(WorkoutStates.waiting_exercise)
    await callback.answer()

@router.message(WorkoutStates.waiting_exercise)
async def process_exercise(message: Message, state: FSMContext):
    """Обработка упражнения"""
    exercise = message.text.strip()
    await state.update_data(exercise=exercise)
    
    await message.answer("Введите количество подходов:")
    await state.set_state(WorkoutStates.waiting_sets)

@router.message(WorkoutStates.waiting_sets)
async def process_sets(message: Message, state: FSMContext):
    """Обработка подходов"""
    try:
        sets = int(message.text)
        await state.update_data(sets=sets)
        await message.answer("Введите количество повторений:")
        await state.set_state(WorkoutStates.waiting_reps)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(WorkoutStates.waiting_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторений"""
    try:
        reps = int(message.text)
        await state.update_data(reps=reps)
        await message.answer("Введите вес (кг) или '-'")
        await state.set_state(WorkoutStates.waiting_weight)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(WorkoutStates.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса"""
    weight = None if message.text == '-' else float(message.text)
    
    data = await state.get_data()
    user_id = message.from_user.id
    
    # Сохраняем в старую таблицу workouts
    await db.execute(
        "INSERT INTO workouts (user_id, exercise_name, sets, reps, weight) VALUES (?, ?, ?, ?, ?)",
        (user_id, data['exercise'], data['sets'], data['reps'], weight)
    )
    
    weight_text = f"{weight} кг" if weight else "без веса"
    
    await message.answer(
        f"✅ *Тренировка добавлена!*\n\n"
        f"🏋️ {data['exercise']}: {data['sets']}×{data['reps']} ({weight_text})",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="➕ ЕЩЁ", callback_data="add_workout"),
            InlineKeyboardButton(text="📋 ИСТОРИЯ", callback_data="workout_history")
        ).as_markup()
    )
    await state.clear()

@router.callback_query(F.data == "workout_history")
async def workout_history(callback: CallbackQuery):
    """История тренировок"""
    user_id = callback.from_user.id
    
    # Показываем сессии с упражнениями
    sessions = await db.fetch_all("""
        SELECT ws.id, ws.date, ws.start_time,
               GROUP_CONCAT(we.exercise_name || ' ' || we.sets || '×' || we.reps, '\n') as exercises
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
            text += f"📅 {s['date']} {s['start_time'] or ''}\n"
            text += f"{s['exercises']}\n\n"
    else:
        text = "📋 *История тренировок*\n\nПока нет тренировок"
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="➕ ДОБАВИТЬ", callback_data="add_workout"),
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="training_journal")
        ).as_markup()
    )
    await callback.answer()