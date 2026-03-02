from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database.base import db

router = Router()

@router.callback_query(F.data == "training_journal")
async def training_journal(callback: CallbackQuery):
    """Журнал тренировок - главное меню"""
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
async def add_workout(callback: CallbackQuery):
    """Добавление тренировки (упрощенно)"""
    user_id = callback.from_user.id
    
    # Просто добавляем тестовую тренировку
    await db.execute(
        "INSERT INTO workouts (user_id, exercise_name, sets, reps) VALUES (?, ?, ?, ?)",
        (user_id, "Тестовое упражнение", 3, 10)
    )
    
    await callback.message.edit_text(
        "✅ Тренировка добавлена!",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="training_journal")
        ).as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "workout_history")
async def workout_history(callback: CallbackQuery):
    """История тренировок"""
    user_id = callback.from_user.id
    
    workouts = await db.fetch_all(
        "SELECT exercise_name, sets, reps, weight, created_at FROM workouts WHERE user_id = ? ORDER BY created_at DESC LIMIT 10",
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
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="training_journal")
        ).as_markup()
    )
    await callback.answer()