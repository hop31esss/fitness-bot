import matplotlib.pyplot as plt
import io
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton

from database.base import db
from config import ADMIN_ID

router = Router()

@router.callback_query(F.data == "progress_charts")
async def show_charts_menu(callback: CallbackQuery):
    """Меню графиков прогресса"""
    text = (
        "📊 *Графики прогресса*\n\n"
        "Выберите тип графика:\n\n"
        "1️⃣ Общий прогресс по тренировкам\n"
        "2️⃣ Прогресс по упражнению\n"
        "3️⃣ Динамика весов\n"
        "4️⃣ Календарь активности"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1️⃣ Общий", callback_data="chart_total"),
        InlineKeyboardButton(text="2️⃣ По упражнению", callback_data="chart_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="3️⃣ Веса", callback_data="chart_weights"),
        InlineKeyboardButton(text="4️⃣ Активность", callback_data="chart_activity")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="progress")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "chart_total")
async def chart_total(callback: CallbackQuery):
    """График общего прогресса"""
    user_id = callback.from_user.id
    
    # Получаем данные за последние 30 дней
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
    
    # Подготовка данных
    dates = [w['date'] for w in workouts]
    volumes = [w['volume'] or 0 for w in workouts]
    counts = [w['count'] for w in workouts]
    
    # Создание графика
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
    
    # График объема
    ax1.plot(dates, volumes, 'b-o', linewidth=2, markersize=6)
    ax1.set_title('Объем тренировок по дням', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Дата')
    ax1.set_ylabel('Объем (кг)')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # График количества тренировок
    ax2.bar(dates, counts, color='green', alpha=0.7)
    ax2.set_title('Количество тренировок по дням', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Дата')
    ax2.set_ylabel('Количество')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Сохранение в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    # Отправка графика
    await callback.message.answer_photo(
        BufferedInputFile(buf.read(), filename="progress.png"),
        caption="📊 *Общий прогресс за 30 дней*\n\n"
                f"📅 Всего тренировок: {sum(counts)}\n"
                f"⚖️ Общий объем: {sum(volumes):,.0f} кг\n"
                f"📈 Средний объем: {sum(volumes)/len(volumes):,.0f} кг/день"
    )
    await callback.answer()

@router.callback_query(F.data == "chart_exercise")
async def chart_exercise(callback: CallbackQuery):
    """Меню выбора упражнения для графика"""
    user_id = callback.from_user.id
    
    # Получаем список упражнений пользователя
    exercises = await db.fetch_all("""
        SELECT DISTINCT exercise_name
        FROM workouts
        WHERE user_id = ?
        ORDER BY exercise_name
    """, (user_id,))
    
    if not exercises:
        await callback.answer("❌ Нет упражнений", show_alert=True)
        return
    
    text = "📊 *Выберите упражнение для анализа:*\n\n"
    
    builder = InlineKeyboardBuilder()
    for ex in exercises[:10]:  # Максимум 10 упражнений
        builder.row(
            InlineKeyboardButton(
                text=f"🏋️ {ex['exercise_name']}",
                callback_data=f"chart_ex_{ex['exercise_name']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="progress_charts")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("chart_ex_"))
async def show_exercise_chart(callback: CallbackQuery):
    """График прогресса по конкретному упражнению"""
    user_id = callback.from_user.id
    exercise_name = callback.data.replace("chart_ex_", "")
    
    # Получаем данные по упражнению
    workouts = await db.fetch_all("""
        SELECT date(created_at) as date, 
               sets, reps, weight
        FROM workouts 
        WHERE user_id = ? AND exercise_name = ?
        ORDER BY created_at
        LIMIT 50
    """, (user_id, exercise_name))
    
    if not workouts:
        await callback.answer("❌ Нет данных", show_alert=True)
        return
    
    # Подготовка данных
    dates = [w['date'] for w in workouts]
    weights = [w['weight'] or 0 for w in workouts]
    
    # Создание графика
    fig, ax = plt.subplots(figsize=(10, 6))
    
    ax.plot(dates, weights, 'r-o', linewidth=2, markersize=8)
    ax.set_title(f'Прогресс: {exercise_name}', fontsize=14, fontweight='bold')
    ax.set_xlabel('Дата')
    ax.set_ylabel('Вес (кг)')
    ax.grid(True, alpha=0.3)
    ax.tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    
    # Сохранение в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    # Статистика
    max_weight = max(weights)
    avg_weight = sum(weights) / len(weights)
    
    await callback.message.answer_photo(
        BufferedInputFile(buf.read(), filename="exercise_progress.png"),
        caption=f"📊 *Прогресс: {exercise_name}*\n\n"
                f"🏋️ Максимальный вес: {max_weight} кг\n"
                f"📈 Средний вес: {avg_weight:.1f} кг\n"
                f"📅 Всего тренировок: {len(workouts)}"
    )
    await callback.answer()

@router.callback_query(F.data == "chart_weights")
async def chart_weights(callback: CallbackQuery):
    """График динамики весов"""
    user_id = callback.from_user.id
    
    # Получаем топ-5 упражнений по весам
    exercises = await db.fetch_all("""
        SELECT exercise_name, MAX(weight) as max_weight
        FROM workouts
        WHERE user_id = ? AND weight IS NOT NULL
        GROUP BY exercise_name
        ORDER BY max_weight DESC
        LIMIT 5
    """, (user_id,))
    
    if not exercises:
        await callback.answer("❌ Нет данных о весах", show_alert=True)
        return
    
    # Создание графика
    fig, ax = plt.subplots(figsize=(10, 6))
    
    names = [ex['exercise_name'][:15] + '...' if len(ex['exercise_name']) > 15 else ex['exercise_name'] 
             for ex in exercises]
    weights = [ex['max_weight'] for ex in exercises]
    
    bars = ax.barh(names, weights, color='orange')
    ax.set_title('Максимальные веса по упражнениям', fontsize=14, fontweight='bold')
    ax.set_xlabel('Вес (кг)')
    
    # Добавляем значения на столбцы
    for i, (bar, weight) in enumerate(zip(bars, weights)):
        ax.text(bar.get_width() + 5, bar.get_y() + bar.get_height()/2, 
                f'{weight} кг', va='center')
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    await callback.message.answer_photo(
        BufferedInputFile(buf.read(), filename="max_weights.png"),
        caption="📊 *Максимальные веса*\n\n"
                "Топ-5 упражнений по максимальному весу"
    )
    await callback.answer()

@router.callback_query(F.data == "chart_activity")
async def chart_activity(callback: CallbackQuery):
    """Тепловая карта активности"""
    user_id = callback.from_user.id
    
    # Получаем активность по часам
    activity = await db.fetch_all("""
        SELECT strftime('%H', created_at) as hour, 
               COUNT(*) as count
        FROM workouts
        WHERE user_id = ?
        GROUP BY hour
        ORDER BY hour
    """, (user_id,))
    
    if not activity:
        await callback.answer("❌ Нет данных", show_alert=True)
        return
    
    # Подготовка данных
    hours = [int(a['hour']) for a in activity]
    counts = [a['count'] for a in activity]
    
    # Создание графика
    fig, ax = plt.subplots(figsize=(12, 5))
    
    ax.bar(hours, counts, width=0.8, color='purple', alpha=0.7)
    ax.set_title('Активность по часам', fontsize=14, fontweight='bold')
    ax.set_xlabel('Час дня')
    ax.set_ylabel('Количество тренировок')
    ax.set_xticks(range(0, 24))
    ax.grid(True, alpha=0.3, axis='y')
    
    # Находим пиковый час
    peak_hour = hours[counts.index(max(counts))]
    
    plt.tight_layout()
    
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100)
    buf.seek(0)
    plt.close()
    
    await callback.message.answer_photo(
        BufferedInputFile(buf.read(), filename="activity.png"),
        caption=f"📊 *Активность по часам*\n\n"
                f"⏰ Пик активности: {peak_hour}:00\n"
                f"📅 Всего тренировок: {sum(counts)}"
    )
    await callback.answer()