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
    
    try:
        # Получаем данные из новой системы workout_sessions
        workouts = await db.fetch_all("""
            SELECT 
                ws.date,
                SUM(we.sets * we.reps * COALESCE(we.weight, 1)) as volume,
                COUNT(we.id) as exercise_count
            FROM workout_sessions ws
            LEFT JOIN workout_exercises we ON ws.id = we.session_id
            WHERE ws.user_id = ? 
                AND ws.date > date('now', '-30 days')
            GROUP BY ws.date
            ORDER BY ws.date
        """, (user_id,))
        
        if not workouts or len(workouts) < 2:
            await callback.answer("❌ Недостаточно данных для графика", show_alert=True)
            return
        
        # Подготовка данных
        dates = []
        volumes = []
        
        for w in workouts:
            # Преобразуем дату в формат ДД.ММ
            date_obj = datetime.strptime(w['date'], '%Y-%m-%d')
            dates.append(date_obj.strftime('%d.%m'))
            volumes.append(w['volume'] or 0)
        
        # Создание графика
        plt.figure(figsize=(12, 6))
        
        # График объема
        plt.plot(dates, volumes, 'b-o', linewidth=2, markersize=8, label='Объем')
        plt.fill_between(dates, volumes, alpha=0.3, color='blue')
        
        # Настройки
        plt.title('Объем тренировок за 30 дней', fontsize=16, fontweight='bold')
        plt.xlabel('Дата')
        plt.ylabel('Объем (кг)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        # Добавляем значения на график
        for i, (date, volume) in enumerate(zip(dates, volumes)):
            plt.annotate(f'{int(volume)}', (date, volume), 
                        textcoords="offset points", xytext=(0,10), 
                        ha='center', fontsize=8)
        
        plt.tight_layout()
        
        # Сохраняем в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        # Статистика
        total_workouts = len(workouts)
        total_volume = sum(volumes)
        avg_volume = total_volume / total_workouts if total_workouts > 0 else 0
        
        # Отправляем фото
        await callback.message.answer_photo(
            BufferedInputFile(buf.read(), filename="progress.png"),
            caption=(
                f"📊 *Прогресс за 30 дней*\n\n"
                f"📅 Тренировок: {total_workouts}\n"
                f"⚖️ Общий объем: {total_volume:,.0f} кг\n"
                f"📈 Средний объем: {avg_volume:,.0f} кг/тренировка"
            )
        )
        
    except Exception as e:
        logger.error(f"Ошибка создания графика: {e}")
        await callback.answer("❌ Ошибка создания графика", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data == "chart_exercise")
async def chart_exercise(callback: CallbackQuery):
    """Меню выбора упражнения для графика"""
    user_id = callback.from_user.id
    
    try:
        # Получаем список упражнений пользователя
        exercises = await db.fetch_all("""
            SELECT DISTINCT we.exercise_name
            FROM workout_exercises we
            JOIN workout_sessions ws ON we.session_id = ws.id
            WHERE ws.user_id = ?
            ORDER BY we.exercise_name
        """, (user_id,))
        
        if not exercises:
            await callback.answer("❌ Нет данных об упражнениях", show_alert=True)
            return
        
        text = "🏋️ *Выберите упражнение:*\n\n"
        
        builder = InlineKeyboardBuilder()
        for ex in exercises[:10]:  # Максимум 10 упражнений
            name = ex['exercise_name']
            builder.row(
                InlineKeyboardButton(
                    text=f"💪 {name}",
                    callback_data=f"chart_ex_detail:{name}"
                )
            )
        builder.row(
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="progress_charts")
        )
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data.startswith("chart_ex_detail:"))
async def chart_exercise_detail(callback: CallbackQuery):
    """График прогресса по конкретному упражнению"""
    user_id = callback.from_user.id
    exercise_name = callback.data.split(":", 1)[1]
    
    try:
        # Получаем прогресс по упражнению
        progress = await db.fetch_all("""
            SELECT 
                ws.date,
                we.weight,
                we.sets,
                we.reps
            FROM workout_exercises we
            JOIN workout_sessions ws ON we.session_id = ws.id
            WHERE ws.user_id = ? AND we.exercise_name = ? AND we.weight IS NOT NULL
            ORDER BY ws.date
            LIMIT 30
        """, (user_id, exercise_name))
        
        if not progress or len(progress) < 2:
            await callback.answer("❌ Недостаточно данных", show_alert=True)
            return
        
        # Подготовка данных
        dates = []
        weights = []
        
        for p in progress:
            date_obj = datetime.strptime(p['date'], '%Y-%m-%d')
            dates.append(date_obj.strftime('%d.%m'))
            weights.append(p['weight'])
        
        # Создание графика
        plt.figure(figsize=(10, 6))
        
        plt.plot(dates, weights, 'r-o', linewidth=2, markersize=8, label='Вес')
        plt.fill_between(dates, weights, alpha=0.2, color='red')
        
        plt.title(f'Прогресс: {exercise_name}', fontsize=14, fontweight='bold')
        plt.xlabel('Дата')
        plt.ylabel('Вес (кг)')
        plt.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        
        # Добавляем значения
        for i, (date, weight) in enumerate(zip(dates, weights)):
            plt.annotate(f'{weight}', (date, weight), 
                        textcoords="offset points", xytext=(0,10), 
                        ha='center', fontsize=8)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        # Статистика
        max_weight = max(weights)
        avg_weight = sum(weights) / len(weights)
        
        await callback.message.answer_photo(
            BufferedInputFile(buf.read(), filename="exercise_progress.png"),
            caption=(
                f"🏋️ *{exercise_name}*\n\n"
                f"📈 Максимальный вес: {max_weight} кг\n"
                f"📊 Средний вес: {avg_weight:.1f} кг\n"
                f"📅 Всего тренировок: {len(progress)}"
            )
        )
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    
    await callback.answer()

@router.callback_query(F.data == "chart_weights")
async def chart_weights(callback: CallbackQuery):
    """График максимальных весов"""
    user_id = callback.from_user.id
    
    try:
        # Получаем максимальные веса по упражнениям
        max_weights = await db.fetch_all("""
            SELECT 
                we.exercise_name,
                MAX(we.weight) as max_weight
            FROM workout_exercises we
            JOIN workout_sessions ws ON we.session_id = ws.id
            WHERE ws.user_id = ? AND we.weight IS NOT NULL
            GROUP BY we.exercise_name
            ORDER BY max_weight DESC
            LIMIT 10
        """, (user_id,))
        
        if not max_weights:
            await callback.answer("❌ Нет данных о весах", show_alert=True)
            return
        
        # Создание горизонтальной столбчатой диаграммы
        plt.figure(figsize=(10, 8))
        
        names = []
        weights = []
        
        for mw in max_weights:
            name = mw['exercise_name']
            if len(name) > 15:
                name = name[:12] + '...'
            names.append(name)
            weights.append(mw['max_weight'])
        
        bars = plt.barh(names, weights, color='orange', alpha=0.7)
        plt.xlabel('Вес (кг)')
        plt.title('Максимальные веса по упражнениям', fontsize=14, fontweight='bold')
        
        # Добавляем значения
        for i, (bar, weight) in enumerate(zip(bars, weights)):
            plt.text(bar.get_width() + 2, bar.get_y() + bar.get_height()/2, 
                    f'{weight} кг', va='center')
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        await callback.message.answer_photo(
            BufferedInputFile(buf.read(), filename="max_weights.png"),
            caption="📊 *Топ упражнений по максимальному весу*"
        )
        
    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)
    
    await callback.answer()