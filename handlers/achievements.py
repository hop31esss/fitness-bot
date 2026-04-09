from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database.base import db

router = Router()

@router.callback_query(F.data == "achievements")
async def achievements_menu(callback: CallbackQuery):
    """Главное меню ачивок и серий"""
    user_id = callback.from_user.id
    
    # Получаем статистику пользователя
    stats = await db.fetch_one(
        "SELECT current_streak, longest_streak FROM user_stats WHERE user_id = ?",
        (user_id,)
    )
    
    # Получаем количество ачивок пользователя
    achievements_count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM achievements WHERE user_id = ?",
        (user_id,)
    )
    a_count = achievements_count['count'] if achievements_count else 0
    
    current_streak = stats['current_streak'] if stats else 0
    longest_streak = stats['longest_streak'] if stats else 0
    
    text = (
        "🏅 *Достижения*\n\n"
        f"🔥 *Серии:*\n"
        f"• Текущая серия: {current_streak} дней\n"
        f"• Лучшая серия: {longest_streak} дней\n\n"
        f"🏆 *Ачивки:* {a_count} получено\n\n"
        "Выберите раздел:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔥 СЕРИИ", callback_data="streaks_detail"),
        InlineKeyboardButton(text="🏆 АЧИВКИ", callback_data="achievements_list")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "streaks_detail")
async def streaks_detail(callback: CallbackQuery):
    """Детальная информация о сериях"""
    user_id = callback.from_user.id
    
    # Получаем историю тренировок для расчёта серий
    workouts = await db.fetch_all("""
        SELECT date FROM workout_sessions 
        WHERE user_id = ? 
        ORDER BY date DESC
    """, (user_id,))
    
    if not workouts:
        text = "🔥 *Серии тренировок*\n\nУ вас пока нет тренировок. Начните заниматься, чтобы появилась серия! 💪"
    else:
        # Конвертируем строки в даты
        workout_dates = [datetime.strptime(w['date'], '%Y-%m-%d').date() for w in workouts]
        
        # Вычисляем текущую серию
        current_streak = 0
        today = datetime.now().date()
        check_date = today
        
        for date in workout_dates:
            if date == check_date:
                current_streak += 1
                check_date = check_date - timedelta(days=1)
            else:
                break
        
        # Вычисляем лучшую серию
        longest_streak = 0
        temp_streak = 1
        
        for i in range(1, len(workout_dates)):
            if (workout_dates[i-1] - workout_dates[i]).days == 1:
                temp_streak += 1
            else:
                longest_streak = max(longest_streak, temp_streak)
                temp_streak = 1
        longest_streak = max(longest_streak, temp_streak)
        
        text = (
            "🔥 *Серии тренировок*\n\n"
            f"📅 Текущая серия: *{current_streak} дней*\n"
            f"🏆 Лучшая серия: *{longest_streak} дней*\n\n"
        )
        
        if current_streak > 0:
            text += "Продолжайте в том же духе! 💪\n"
            if current_streak >= 7:
                text += "✨ Целую неделю без пропусков! Отлично!\n"
            if current_streak >= 30:
                text += "🌟 Месяц тренировок! Вы настоящий чемпион!\n"
        else:
            text += "Начните тренироваться сегодня, чтобы начать новую серию! ⏰"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="achievements")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "achievements_list")
async def achievements_list(callback: CallbackQuery):
    """Список полученных ачивок"""
    user_id = callback.from_user.id
    
    # Получаем ачивки пользователя
    achievements = await db.fetch_all("""
        SELECT achievement_name, achieved_at 
        FROM achievements 
        WHERE user_id = ? 
        ORDER BY achieved_at DESC
    """, (user_id,))
    
    if not achievements:
        text = (
            "🏆 *Ачивки*\n\n"
            "У вас пока нет ачивок.\n\n"
            "💡 *Как получить:*\n"
            "• Первая тренировка 🏅\n"
            "• 10 тренировок 🥉\n"
            "• 30 тренировок 🥈\n"
            "• 100 тренировок 🥇\n"
            "• Серия 30 дней 🔥"
        )
    else:
        text = "🏆 *Полученные ачивки*\n\n"
        for ach in achievements:
            date = ach['achieved_at'][:10] if ach['achieved_at'] else "??"
            text += f"• {ach['achievement_name']} ({date})\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="achievements")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()