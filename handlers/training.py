from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db
from utils.logging import log_action
from utils.units import to_kg
from services.progress_analytics import fetch_session_history, format_kg
from utils.clock import now_hm, today_iso

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
    log_action(callback.from_user.id, "training_journal_open")
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
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="menu_training")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "add_exercise")
async def add_exercise_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления упражнения"""
    log_action(callback.from_user.id, "add_exercise_start")
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
    log_action(message.from_user.id, "process_exercise_name")
    if message.text == "/cancel":
        await message.answer("❌ Добавление отменено.")
        await state.clear()
        return
    if not message.text:
        await message.answer("❌ Пришлите название текстом.")
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
    log_action(callback.from_user.id, "my_exercises_open")
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
    log_action(message.from_user.id, "process_exercise_alias")
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
    log_action(callback.from_user.id, "add_workout_start")
    await callback.message.edit_text(
        "🏋️ *Добавление тренировки*\n\n"
        "Введите название упражнения:"
    )
    await state.set_state(WorkoutStates.waiting_exercise)
    await callback.answer()

@router.message(WorkoutStates.waiting_exercise)
async def process_exercise(message: Message, state: FSMContext):
    """Обработка упражнения"""
    log_action(message.from_user.id, "process_exercise")
    if not message.text:
        await message.answer("❌ Пришлите название упражнения текстом.")
        return
    exercise = message.text.strip()
    await state.update_data(exercise=exercise)
    
    await message.answer("Введите количество подходов:")
    await state.set_state(WorkoutStates.waiting_sets)

@router.message(WorkoutStates.waiting_sets)
async def process_sets(message: Message, state: FSMContext):
    """Обработка подходов"""
    log_action(message.from_user.id, "process_sets")
    if not message.text:
        await message.answer("❌ Введите положительное целое число.")
        return
    try:
        sets = int(message.text)
        if sets <= 0:
            raise ValueError
        await state.update_data(sets=sets)
        await message.answer("Введите количество повторений:")
        await state.set_state(WorkoutStates.waiting_reps)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(WorkoutStates.waiting_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторений"""
    log_action(message.from_user.id, "process_reps")
    if not message.text:
        await message.answer("❌ Введите положительное целое число.")
        return
    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
        await state.update_data(reps=reps)
        await message.answer("Введите вес (кг) или '-'")
        await state.set_state(WorkoutStates.waiting_weight)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(WorkoutStates.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса"""
    log_action(message.from_user.id, "process_weight")
    if not message.text:
        await message.answer("❌ Введите вес или '-' для упражнения без веса.")
        return
    try:
        weight = 0.0 if message.text.strip() == '-' else float(message.text.replace(",", "."))
        if weight < 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите неотрицательный вес или '-'.")
        return
    
    data = await state.get_data()
    user_id = message.from_user.id
    settings = await db.fetch_one(
        "SELECT units FROM user_settings WHERE user_id = ?",
        (user_id,),
    )
    weight = to_kg(weight, (settings or {}).get("units", "kg"))
    
    # Ручной ввод также пишет в каноническую модель сессий и подходов.
    today = today_iso()
    await db.execute(
        """INSERT INTO workout_sessions (user_id, date, start_time, end_time)
           VALUES (?, ?, ?, ?)""",
        (user_id, today, now_hm(), now_hm()),
    )
    session = await db.fetch_one("SELECT last_insert_rowid() AS id")
    await db.execute(
        """INSERT INTO workout_exercises
           (session_id, exercise_name, exercise_type, sets, reps, weight, completed, order_num)
           VALUES (?, ?, 'strength', ?, ?, ?, TRUE, 1)""",
        (session["id"], data["exercise"], data["sets"], data["reps"], weight),
    )
    exercise_row = await db.fetch_one("SELECT last_insert_rowid() AS id")
    await db.execute_many(
        """INSERT INTO workout_sets
           (workout_exercise_id, set_number, weight, reps, completed)
           VALUES (?, ?, ?, ?, TRUE)""",
        [
            (exercise_row["id"], set_number, weight, data["reps"])
            for set_number in range(1, data["sets"] + 1)
        ],
    )
    
    weight_text = f"{weight:g} кг" if weight else "без веса"
    
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
    log_action(callback.from_user.id, "workout_history_open")
    user_id = callback.from_user.id
    
    sessions = await fetch_session_history(user_id, limit=10)

    if sessions:
        text = "📋 *История тренировок*\n\n"
        for s in sessions:
            text += f"📅 {s['date']} {s['start_time'] or ''}\n"
            text += f"{s['exercises']}\n"
            text += f"⚖️ Объём: {format_kg(s['volume'] or 0)} кг\n\n"
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