from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database.base import db
from services.analytics import get_user_stats, get_workout_history

router = Router()

@router.callback_query(F.data == "stats")
async def show_stats(callback: CallbackQuery):
    """Детальная статистика тренировок"""
    user_id = callback.from_user.id
    
    # Получаем статистику
    stats = await get_user_stats(user_id)
    
    if not stats:
        text = "📊 *Статистика*\n\nУ вас пока нет данных о тренировках."
    else:
        # Получаем дополнительную статистику
        total_volume = await db.fetch_one("""
            SELECT SUM(sets * reps * COALESCE(weight, 1)) as total_volume 
            FROM workouts WHERE user_id = ?
        """, (user_id,))
        
        avg_workouts_per_week = await db.fetch_one("""
            SELECT COUNT(*) * 7.0 / 
            (JULIANDAY('now') - JULIANDAY(MIN(created_at)) + 1) as avg_per_week
            FROM workouts WHERE user_id = ?
        """, (user_id,))
        
        # Получаем самые популярные упражнения
        top_exercises = await db.fetch_all("""
            SELECT exercise_name, COUNT(*) as count 
            FROM workouts WHERE user_id = ?
            GROUP BY exercise_name ORDER BY count DESC LIMIT 5
        """, (user_id,))
        
        text = "📊 *Детальная статистика тренировок*\n\n"
        text += f"🏋️ Всего тренировок: {stats['total_workouts']}\n"
        text += f"💪 Уникальных упражнений: {stats['total_exercises']}\n"
        text += f"🔥 Текущая серия: {stats['current_streak']} дней\n"
        text += f"🏆 Максимальная серия: {stats['longest_streak']} дней\n"
        
        if total_volume and total_volume['total_volume']:
            text += f"⚖️ Общий тоннаж: {total_volume['total_volume']:,.0f} кг\n"
        
        if avg_workouts_per_week and avg_workouts_per_week['avg_per_week']:
            text += f"📅 Среднее в неделю: {avg_workouts_per_week['avg_per_week']:.1f} тренировок\n"
        
        if stats['last_workout_date']:
            last_date = datetime.strptime(stats['last_workout_date'][:10], '%Y-%m-%d')
            days_ago = (datetime.now() - last_date).days
            text += f"⏰ Последняя тренировка: {days_ago} дней назад\n"
        
        if top_exercises:
            text += "\n🏅 *Топ-5 упражнений:*\n"
            for i, exercise in enumerate(top_exercises, 1):
                text += f"{i}. {exercise['exercise_name']} - {exercise['count']} раз\n"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Прогресс", callback_data="progress"),
        InlineKeyboardButton(text="📅 Календарь", callback_data="calendar")
    )
    builder.row(
        InlineKeyboardButton(text="📋 История тренировок", callback_data="workout_history"),
        InlineKeyboardButton(text="📊 Графики", callback_data="charts")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "charts")
async def show_charts(callback: CallbackQuery):
    """Графики статистики (текстовый вариант без matplotlib)"""
    user_id = callback.from_user.id
    
    # Получаем данные за последние 30 дней
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    history = await get_workout_history(user_id, start_date, end_date)
    
    if not history:
        text = "📈 *Графики статистики*\n\nНедостаточно данных для построения графиков."
    else:
        # Создаем текстовую визуализацию
        text = "📈 *График активности за 30 дней*\n\n"
        
        max_workouts = max([day.get('workout_count', 0) for day in history])
        
        for day in history[-14:]:  # Показываем последние 14 дней
            date = day.get('date', '')[:10]
            workout_count = day.get('workout_count', 0)
            
            # Текстовая шкала
            bar = "█" * int((workout_count / max(max_workouts, 1)) * 10)
            
            text += f"{date}: {bar} {workout_count} тренировок\n"
        
        text += f"\nВсего тренировок за 30 дней: {sum([d.get('workout_count', 0) for d in history])}"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Общая статистика", callback_data="stats"),
        InlineKeyboardButton(text="📈 Прогресс", callback_data="progress")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()