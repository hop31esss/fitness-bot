from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart

from database.base import db
from keyboards.main import get_main_keyboard
from services.analytics import update_user_stats

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Красивое приветствие"""
    user_id = message.from_user.id
    username = message.from_user.username
    first_name = message.from_user.first_name
    
    # Регистрация пользователя
    await db.execute(
        """INSERT OR REPLACE INTO users 
        (user_id, username, first_name) 
        VALUES (?, ?, ?)""",
        (user_id, username, first_name)
    )
    
    await update_user_stats(user_id)
    
    # Проверяем премиум-статус
    user = await db.fetch_one(
        "SELECT is_subscribed FROM users WHERE user_id = ?",
        (user_id,)
    )
    is_premium = user and user['is_subscribed'] if user else False
    
    # Красивое приветствие
    welcome_text = (
        f"🌟 *Добро пожаловать, {first_name}!*\n\n"
        "Я ваш персональный фитнес-помощник. Помогу достичь ваших целей! 💪\n\n"
        "▫️ Записывайте тренировки\n"
        "▫️ Отслеживайте прогресс\n"
        "▫️ Соревнуйтесь с друзьями\n"
        "▫️ Получайте AI-советы\n\n"
        "👇 *Выберите действие:*"
    )
    
    keyboard = get_main_keyboard(user_id, is_premium)
    await message.answer(welcome_text, reply_markup=keyboard)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    user_id = callback.from_user.id
    
    # Проверяем премиум
    user = await db.fetch_one(
        "SELECT is_subscribed FROM users WHERE user_id = ?",
        (user_id,)
    )
    is_premium = user and user['is_subscribed'] if user else False
    
    keyboard = get_main_keyboard(user_id, is_premium)
    
    # Используем edit_text вместо edit_caption
    await callback.message.edit_text(
        text="🌟 *Главное меню*\n\nВыберите действие:",
        reply_markup=keyboard
    )
    await callback.answer()