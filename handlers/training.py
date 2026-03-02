from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database.base import db
from keyboards.training import get_training_menu_keyboard, get_exercises_keyboard

router = Router()

# ================ СОСТОЯНИЯ ДЛЯ FSM ================

class AddExerciseStates(StatesGroup):
    waiting_exercise_name = State()
    waiting_exercise_alias = State()

class AddWorkoutStates(StatesGroup):
    waiting_exercise = State()
    waiting_sets = State()
    waiting_reps = State()
    waiting_weight = State()

# ================ ЖУРНАЛ ТРЕНИРОВОК ================

@router.callback_query(F.data == "training_journal")
async def training_journal(callback: CallbackQuery):
    """Журнал тренировок - главное меню"""
    text = "📒 *Журнал тренировок*\n\nВыберите действие:"
    keyboard = get_training_menu_keyboard()
    
    await callback.message.edit_text(text, reply_markup=keyboard)
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
        text += f"\nВсего упражнений: {len(exercises)}"
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
        
        # Возвращаемся в журнал тренировок
        user_id = message.from_user.id
        text = "📒 *Журнал тренировок*\n\nВыберите действие:"
        keyboard = get_training_menu_keyboard()
        await message.answer(text, reply_markup=keyboard)
        return
    
    exercise_name = message.text.strip()
    
    if len(exercise_name) < 2 or len(exercise_name) > 50:
        await message.answer(
            "❌ Название должно быть от 2 до 50 символов. Попробуйте еще раз:"
        )
        return
    
    await state.update_data(exercise_name=exercise_name)
    
    await message.answer(
        f"✅ Название сохранено: {exercise_name}\n\n"
        "Хотите добавить короткое название (алиас)?\n"
        "Например: 'Жим'\n\n"
        "Отправьте алиас или '-' чтобы пропустить:"
    )
    await state.set_state(AddExerciseStates.waiting_exercise_alias)

@router.message(AddExerciseStates.waiting_exercise_alias)
async def process_exercise_alias(message: Message, state: FSMContext):
    """Обработка алиаса упражнения"""
    if message.text == "/cancel":
        await message.answer("❌ Добавление отменено.")
        await state.clear()
        
        # Возвращаемся в журнал тренировок
        user_id = message.from_user.id
        text = "📒 *Журнал тренировок*\n\nВыберите действие:"
        keyboard = get_training_menu_keyboard()
        await message.answer(text, reply_markup=keyboard)
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
    
    # Клавиатура для возврата
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ЕЩЕ", callback_data="add_exercise"),
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

# ================ ДОБАВЛЕНИЕ ТРЕНИРОВКИ ================

@router.callback_query(F.data == "add_workout")
async def add_workout_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления тренировки"""
    user_id = callback.from_user.id
    
    # Получаем упражнения пользователя
    exercises = await db.fetch_all(
        "SELECT name, alias FROM exercises WHERE user_id = ?",
        (user_id,)
    )
    
    if exercises:
        text = "Выберите упражнение из списка или введите новое:"
        keyboard = get_exercises_keyboard(exercises)
        await callback.message.edit_text(text, reply_markup=keyboard)
    else:
        await callback.message.edit_text(
            "У вас пока нет упражнений. Введите название нового упражнения:"
        )
    
    await state.set_state(AddWorkoutStates.waiting_exercise)
    await callback.answer()

@router.message(AddWorkoutStates.waiting_exercise)
async def process_workout_exercise(message: Message, state: FSMContext):
    """Обработка упражнения для тренировки"""
    if message.text == "/cancel":
        await message.answer("❌ Добавление отменено.")
        await state.clear()
        
        # Возвращаемся в журнал тренировок
        user_id = message.from_user.id
        text = "📒 *Журнал тренировок*\n\nВыберите действие:"
        keyboard = get_training_menu_keyboard()
        await message.answer(text, reply_markup=keyboard)
        return
    
    exercise_name = message.text.strip()
    await state.update_data(exercise_name=exercise_name)
    
    await message.answer("Введите количество подходов:")
    await state.set_state(AddWorkoutStates.waiting_sets)

@router.message(AddWorkoutStates.waiting_sets)
async def process_workout_sets(message: Message, state: FSMContext):
    """Обработка подходов"""
    if message.text == "/cancel":
        await message.answer("❌ Добавление отменено.")
        await state.clear()
        
        # Возвращаемся в журнал тренировок
        user_id = message.from_user.id
        text = "📒 *Журнал тренировок*\n\nВыберите действие:"
        keyboard = get_training_menu_keyboard()
        await message.answer(text, reply_markup=keyboard)
        return
    
    try:
        sets = int(message.text)
        if sets <= 0:
            raise ValueError
        await state.update_data(sets=sets)
        await message.answer("Введите количество повторений:")
        await state.set_state(AddWorkoutStates.waiting_reps)
    except ValueError:
        await message.answer("❌ Введите корректное число подходов:")

@router.message(AddWorkoutStates.waiting_reps)
async def process_workout_reps(message: Message, state: FSMContext):
    """Обработка повторений"""
    if message.text == "/cancel":
        await message.answer("❌ Добавление отменено.")
        await state.clear()
        
        # Возвращаемся в журнал тренировок
        user_id = message.from_user.id
        text = "📒 *Журнал тренировок*\n\nВыберите действие:"
        keyboard = get_training_menu_keyboard()
        await message.answer(text, reply_markup=keyboard)
        return
    
    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
        await state.update_data(reps=reps)
        await message.answer("Введите вес (кг) или '-' если без веса:")
        await state.set_state(AddWorkoutStates.waiting_weight)
    except ValueError:
        await message.answer("❌ Введите корректное число повторений:")

@router.message(AddWorkoutStates.waiting_weight)
async def process_workout_weight(message: Message, state: FSMContext):
    """Обработка веса"""
    if message.text == "/cancel":
        await message.answer("❌ Добавление отменено.")
        await state.clear()
        
        # Возвращаемся в журнал тренировок
        user_id = message.from_user.id
        text = "📒 *Журнал тренировок*\n\nВыберите действие:"
        keyboard = get_training_menu_keyboard()
        await message.answer(text, reply_markup=keyboard)
        return
    
    weight_text = message.text.strip()
    weight = None if weight_text == '-' else float(weight_text) if weight_text.replace('.', '').isdigit() else None
    
    if weight_text != '-' and weight is None:
        await message.answer("❌ Введите корректный вес или '-'")
        return
    
    data = await state.get_data()
    user_id = message.from_user.id
    exercise_name = data['exercise_name']
    sets = data['sets']
    reps = data['reps']
    
    # Сохраняем тренировку
    await db.execute(
        """INSERT INTO workouts 
        (user_id, exercise_name, sets, reps, weight) 
        VALUES (?, ?, ?, ?, ?)""",
        (user_id, exercise_name, sets, reps, weight)
    )
    
    weight_text = f"{weight} кг" if weight else "без веса"
    
    # Клавиатура для возврата
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ЕЩЕ", callback_data="add_workout"),
        InlineKeyboardButton(text="📋 ИСТОРИЯ", callback_data="workout_history")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ В ЖУРНАЛ", callback_data="training_journal")
    )
    
    await message.answer(
        f"✅ *Тренировка добавлена!*\n\n"
        f"🏋️ {exercise_name}\n"
        f"📊 {sets}×{reps} | ⚖️ {weight_text}",
        reply_markup=builder.as_markup()
    )
    await state.clear()

# ================ ВЫБОР УПРАЖНЕНИЯ ИЗ СПИСКА ================

@router.callback_query(F.data.startswith("select_exercise:"))
async def select_exercise(callback: CallbackQuery, state: FSMContext):
    """Выбор упражнения из списка"""
    exercise_name = callback.data.split(":", 1)[1]
    await state.update_data(exercise_name=exercise_name)
    
    await callback.message.edit_text(
        f"Выбрано упражнение: {exercise_name}\n\nВведите количество подходов:"
    )
    await state.set_state(AddWorkoutStates.waiting_sets)
    await callback.answer()

@router.callback_query(F.data == "new_exercise")
async def new_exercise(callback: CallbackQuery, state: FSMContext):
    """Ввод нового упражнения"""
    await callback.message.edit_text(
        "Введите название нового упражнения:"
    )
    await state.set_state(AddWorkoutStates.waiting_exercise)
    await callback.answer()

@router.callback_query(F.data == "workout_history")
async def workout_history(callback: CallbackQuery):
    """История тренировок"""
    user_id = callback.from_user.id
    
    # Получаем последние 20 тренировок
    workouts = await db.fetch_all("""
        SELECT exercise_name, sets, reps, weight, created_at
        FROM workouts 
        WHERE user_id = ? 
        ORDER BY created_at DESC 
        LIMIT 20
    """, (user_id,))
    
    if not workouts:
        text = "📋 *История тренировок*\n\nУ вас пока нет тренировок. Добавьте первую!"
    else:
        text = "📋 *История тренировок*\n\n"
        
        # Группируем по датам
        current_date = None
        daily_workouts = []
        
        for workout in workouts:
            date = workout['created_at'][:10]
            time = workout['created_at'][11:16]
            
            if date != current_date:
                if daily_workouts:
                    text += f"\n"
                text += f"📅 *{date}*\n"
                current_date = date
                daily_workouts = []
            
            weight_text = f"{workout['weight']} кг" if workout['weight'] else "б/в"
            text += f"  {time} - {workout['exercise_name']}: {workout['sets']}×{workout['reps']} ({weight_text})\n"
        
        text += f"\n📊 Всего тренировок: {len(workouts)}"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ", callback_data="add_workout"),
        InlineKeyboardButton(text="📊 СТАТИСТИКА", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="training_journal")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()    