import matplotlib
matplotlib.use('Agg')  # Важно для сервера!
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db

router = Router()

@router.callback_query(F.data == "progress_charts")
async def show_charts_menu(callback: CallbackQuery):
    """Меню графиков прогресса"""
    text = (
        "📊 *Графики прогресса*\n\n"
        "Выберите тип графика:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📈 Общий прогресс", callback_data="chart_total"),
        InlineKeyboardButton(text="🏋️ По упражнению", callback_data="chart_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="⚖️ Максимальные веса", callback_data="chart_weights"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="progress_stats")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "chart_total")
async def chart_total(callback: CallbackQuery):
    """График общего прогресса"""
    user_id = callback.from_user.id
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    workouts = await db.fetch_all("""
        SELECT date(created_at) as date, 
               COUNT(*) as count,
               SUM(sets * reps * COALESCE(weight, 1)) as volume
        FROM workouts 
        WHERE user_id = ? AND created_at BETWEEN ? AND ?
        GROUP BY date(created_at)
        ORDER BY date
    """, (user_id, start_date, end_date))
    
    if not workouts:
        await callback.answer("❌ Недостаточно данных", show_alert=True)
        return
    
    dates = [w['date'] for w in workouts]
    volumes = [w['volume'] or 0 for w in workouts]
    counts = [w['count'] for w in workouts]
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    ax1.plot(dates, volumes, 'b-o', linewidth=2, markersize=6)
    ax1.set_title('Объем тренировок по дням', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Дата')
    ax1.set_ylabel('Объем (кг)')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    ax2.bar(dates, counts, color='green', alpha=0.7)
    ax2.set_title('Количество тренировок по дням', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Дата')
    ax2.set_ylabel('Количество')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close(fig)
    
    await callback.message.answer_photo(
        BufferedInputFile(buf.read(), filename="progress.png"),
        caption=f"📊 *Общий прогресс за 30 дней*\n\n"
                f"📅 Всего тренировок: {sum(counts)}\n"
                f"⚖️ Общий объем: {sum(volumes):,.0f} кг"
    )
    await callback.answer()

@router.callback_query(F.data == "chart_exercise")
async def chart_exercise(callback: CallbackQuery):
    """Заглушка для графика по упражнению"""
    await callback.answer("🚧 Функция в разработке", show_alert=True)

@router.callback_query(F.data == "chart_weights")
async def chart_weights(callback: CallbackQuery):
    """Заглушка для графика весов"""
    await callback.answer("🚧 Функция в разработке", show_alert=True)