from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import List, Dict

from database.base import db
from utils.formatters import format_leaderboard

router = Router()

@router.callback_query(F.data == "leaderboard")
async def leaderboard_menu(callback: CallbackQuery):
    """Меню таблиц лидеров"""
    text = "🏆 Таблицы лидеров\n\nВыберите тип:"
    keyboard = get_leaderboard_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "global_leaderboard")
async def global_leaderboard(callback: CallbackQuery):
    """Глобальная таблица лидеров"""
    # Получаем топ-10 пользователей по количеству тренировок
    query = """
        SELECT u.username, u.first_name, u.last_name, us.total_workouts
        FROM user_stats us
        JOIN users u ON us.user_id = u.user_id
        ORDER BY us.total_workouts DESC
        LIMIT 10
    """
    leaders = await db.fetch_all(query)
    
    if leaders:
        text = format_leaderboard(leaders, "Глобальный рейтинг (всего тренировок)")
    else:
        text = "Пока нет данных для таблицы лидеров"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_leaderboard_keyboard())
    await callback.answer()

@router.callback_query(F.data == "friends_leaderboard")
async def friends_leaderboard(callback: CallbackQuery):
    """Таблица лидеров среди друзей"""
    user_id = callback.from_user.id
    
    # В будущем здесь можно реализовать логику друзей
    # Пока просто покажем глобальный рейтинг
    query = """
        SELECT u.username, u.first_name, u.last_name, us.total_workouts
        FROM user_stats us
        JOIN users u ON us.user_id = u.user_id
        ORDER BY us.total_workouts DESC
        LIMIT 10
    """
    leaders = await db.fetch_all(query)
    
    if leaders:
        text = format_leaderboard(leaders, "Рейтинг среди друзей (всего тренировок)")
    else:
        text = "Пока нет данных для таблицы лидеров"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_leaderboard_keyboard())
    await callback.answer()

def get_leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура лидербордов"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🌍 Глобальный", callback_data="global_leaderboard"),
        InlineKeyboardButton(text="👥 Среди друзей", callback_data="friends_leaderboard")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_back_to_leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата к лидербордам"""
    builder = InlineKeyboardBuilder()
    builder.row (InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main"))
    return builder.as_markup()