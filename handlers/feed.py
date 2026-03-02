# handlers/feed.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.base import db

router = Router()

@router.callback_query(F.data == "activity_feed")
async def show_feed(callback: CallbackQuery):
    """Лента активности"""
    # Получаем последние активности
    activities = await db.fetch_all("""
        SELECT u.first_name, w.exercise_name, w.created_at 
        FROM workouts w
        JOIN users u ON w.user_id = u.user_id
        ORDER BY w.created_at DESC
        LIMIT 15
    """)
    
    if activities:
        text = "📰 *Лента активности*\n\n"
        text += "*Последние тренировки пользователей:*\n\n"
        
        for activity in activities:
            time = activity['created_at'][11:16]  # Берем только время
            text += f"👤 {activity['first_name']} - {activity['exercise_name']} в {time}\n"
    else:
        text = "📰 *Лента активности*\n\nПока нет активностей. Будьте первым!"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить свою тренировку", callback_data="add_workout"),
        InlineKeyboardButton(text="🏆 Лидерборд", callback_data="global_leaderboard")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="activity_feed"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()