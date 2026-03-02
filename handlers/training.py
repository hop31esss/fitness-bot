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

@router.callback_query(F.data == "training_journal")
async def training_journal(callback: CallbackQuery):
    """Журнал тренировок"""
    text = "📒 *Журнал тренировок*\n\nВыберите действие:"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ ТРЕНИРОВКУ", callback_data="add_workout"),
        InlineKeyboardButton(text="📋 ИСТОРИЯ", callback_data="workout_history")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

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
    
    workouts = await db.fetch_all(
        "SELECT exercise_name, sets, reps, weight, created_at FROM workouts WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user_id,)
    )
    
    if workouts:
        text = "📋 *История тренировок*\n\n"
        for w in workouts:
            date = w['created_at'][:16] if w['created_at'] else ""
            weight = f", {w['weight']} кг" if w['weight'] else ""
            text += f"• {date}: {w['exercise_name']} {w['sets']}×{w['reps']}{weight}\n"
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