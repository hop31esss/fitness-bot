from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date

from database.base import db
from keyboards.main import get_main_keyboard
from handlers.referral import handle_referral_join

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start с поддержкой рефералов"""
    user_id = message.from_user.id

    # Регистрируем пользователя
    await db.execute(
        """INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name) 
        VALUES (?, ?, ?, ?)""",
        (user_id, message.from_user.username, 
         message.from_user.first_name, message.from_user.last_name)
    )

    # Обрабатываем реферальный старт (7 дней другу сразу, бонус рефереру после удержания).
    await handle_referral_join(message)

    today = date.today().isoformat()
    today_sessions = await db.fetch_one(
        """
        SELECT COUNT(*) as cnt
        FROM workout_sessions
        WHERE user_id = ? AND date = ? AND end_time IS NOT NULL
        """,
        (user_id, today),
    )
    streak = await db.fetch_one(
        "SELECT current_streak FROM user_stats WHERE user_id = ?",
        (user_id,),
    )

    sessions_done = today_sessions["cnt"] if today_sessions else 0
    current_streak = streak["current_streak"] if streak else 0
    today_status = "✅ Уже тренировались сегодня" if sessions_done > 0 else "⏳ Сегодня тренировки ещё не было"

    welcome_text = (
        f"👋 *Привет, {message.from_user.first_name}!*\n\n"
        "*Сегодня:*\n"
        f"{today_status}\n"
        f"🔥 Стрик: {current_streak} дн.\n\n"
        "Что хотите сделать сейчас?"
    )

    quick = InlineKeyboardBuilder()
    quick.row(InlineKeyboardButton(text="🏋️ Начать тренировку", callback_data="start_workout"))
    quick.row(
        InlineKeyboardButton(text="✍️ Записать", callback_data="training_journal"),
        InlineKeyboardButton(text="📊 Прогресс", callback_data="progress_stats"),
    )
    quick.row(InlineKeyboardButton(text="📋 Открыть всё меню", callback_data="back_to_main"))
    await message.answer(welcome_text, reply_markup=quick.as_markup())

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    user_id = callback.from_user.id

    keyboard = get_main_keyboard(user_id)
    
    # Используем edit_text вместо edit_caption
    await callback.message.edit_text(text="🌟 *Главное меню*\n\nВыберите действие:", reply_markup=keyboard)
    await callback.answer()