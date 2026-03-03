import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from database.base import db

router = Router()
logger = logging.getLogger(__name__)

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
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="progress_stats")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "chart_total")
async def chart_total(callback: CallbackQuery):
    """График общего прогресса"""
    user_id = callback.from_user.id
    
    try:
        # Получаем данные за последние 30 дней
        workouts = await db.fetch_all("""
            SELECT date(created_at) as date, 
                   SUM(sets * reps * COALESCE(weight, 1)) as volume
            FROM workouts 
            WHERE user_id = ? AND created_at > datetime('now', '-30 days')
            GROUP BY date(created_at)
            ORDER BY date
        """, (user_id,))
        
        if not workouts or len(workouts) < 2:
            await callback.answer("❌ Недостаточно данных для графика", show_alert=True)
            return
        
        # Подготовка данных
        dates = [w['date'][5:] for w in workouts]  # только день-месяц
        volumes = [w['volume'] or 0 for w in workouts]
        
        # Создание графика
        plt.figure(figsize=(10, 5))
        plt.plot(dates, volumes, 'b-o', linewidth=2, markersize=8)
        plt.fill_between(dates, volumes, alpha=0.3, color='blue')
        plt.title('Объем тренировок по дням', fontsize=14, fontweight='bold')
        plt.xlabel('Дата')
        plt.ylabel('Объем (кг)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Сохраняем в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        # Отправляем фото
        await callback.message.answer_photo(
            BufferedInputFile(buf.read(), filename="progress.png"),
            caption=f"📊 *Прогресс за 30 дней*\n\n"
                    f"📅 Тренировок: {len(workouts)}\n"
                    f"⚖️ Общий объем: {sum(volumes):,.0f} кг"
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания графика: {e}")
        await callback.answer("❌ Ошибка создания графика", show_alert=True)
    
    await callback.answer()