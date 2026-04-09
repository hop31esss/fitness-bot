from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from database.base import db
from services.analytics import get_user_stats
from utils.formatters import format_stats
import matplotlib.pyplot as plt
import io
from aiogram.types import BufferedInputFile
import logging
logger = logging.getLogger(__name__)

router = Router()

@router.callback_query(F.data == "profile")
async def profile_menu(callback: CallbackQuery):
    """Меню профиля и статистики"""
    user_id = callback.from_user.id
    
    # Получаем статистику пользователя
    stats = await get_user_stats(user_id)
    
    if stats:
        text = format_stats(stats)
    else:
        text = "Статистика пока недоступна. Начните тренироваться!"
    
    keyboard = get_profile_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "progress")
async def show_progress(callback: CallbackQuery):
    """Показ прогресса с графиками"""
    user_id = callback.from_user.id
    
    # Получаем данные за последние 30 дней
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Берем данные из новых сессий
    history = await db.fetch_all("""
        SELECT ws.date, 
               COUNT(we.id) as workout_count,
               SUM(we.sets * we.reps * COALESCE(we.weight, 1)) as total_volume
        FROM workout_sessions ws
        LEFT JOIN workout_exercises we ON ws.id = we.session_id
        WHERE ws.user_id = ? AND ws.date BETWEEN ? AND ?
        GROUP BY ws.date
        ORDER BY ws.date
    """, (user_id, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    
    if not history:
        await callback.message.edit_text(
            "📈 *Прогресс*\n\nНедостаточно данных для построения графиков. "
            "Добавьте больше тренировок!"
        )
        await callback.answer()
        return
    
    # Подготовка данных
    dates = [h['date'] for h in history]
    volumes = [h['total_volume'] or 0 for h in history]
    counts = [h['workout_count'] for h in history]
    
    # СОЗДАНИЕ ГРАФИКА 1: Объем тренировок
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
    
    # График объема
    ax1.plot(dates, volumes, 'b-', linewidth=2, marker='o', markersize=6)
    ax1.fill_between(dates, volumes, alpha=0.3, color='blue')
    ax1.set_title('Объем тренировок по дням', fontsize=14, fontweight='bold')
    ax1.set_xlabel('Дата')
    ax1.set_ylabel('Объем (кг)')
    ax1.grid(True, alpha=0.3)
    ax1.tick_params(axis='x', rotation=45)
    
    # Добавляем значения на график
    for i, (date, volume) in enumerate(zip(dates, volumes)):
        ax1.annotate(f'{int(volume)}', (date, volume), 
                    textcoords="offset points", xytext=(0,10), ha='center', fontsize=8)
    
    # График количества тренировок
    colors = ['green' if c == 1 else 'orange' if c == 2 else 'red' for c in counts]
    ax2.bar(dates, counts, color=colors, alpha=0.7)
    ax2.set_title('Количество тренировок по дням', fontsize=14, fontweight='bold')
    ax2.set_xlabel('Дата')
    ax2.set_ylabel('Количество')
    ax2.grid(True, alpha=0.3)
    ax2.tick_params(axis='x', rotation=45)
    
    # Добавляем значения на столбцы
    for i, (date, count) in enumerate(zip(dates, counts)):
        ax2.annotate(str(count), (date, count), 
                    textcoords="offset points", xytext=(0,5), ha='center', fontsize=8)
    
    plt.tight_layout()
    
    # Сохраняем первый график
    buf1 = io.BytesIO()
    plt.savefig(buf1, format='png', dpi=100)
    buf1.seek(0)
    plt.close()
    
    # СОЗДАНИЕ ГРАФИКА 2: Прогресс весов (если есть данные о весе)
    weights_data = await db.fetch_all("""
        SELECT date(created_at) as date, 
               exercise_name,
               MAX(weight) as max_weight
        FROM workouts 
        WHERE user_id = ? AND weight IS NOT NULL
        GROUP BY date(created_at), exercise_name
        ORDER BY date
        LIMIT 50
    """, (user_id,))
    
    if weights_data:
        fig2, ax3 = plt.subplots(figsize=(12, 6))
        
        # Группируем по упражнениям
        exercises = {}
        for w in weights_data:
            if w['exercise_name'] not in exercises:
                exercises[w['exercise_name']] = {'dates': [], 'weights': []}
            exercises[w['exercise_name']]['dates'].append(w['date'])
            exercises[w['exercise_name']]['weights'].append(w['max_weight'])
        
        # Рисуем линии для каждого упражнения
        colors = ['red', 'blue', 'green', 'orange', 'purple']
        for i, (ex_name, data) in enumerate(list(exercises.items())[:5]):
            ax3.plot(data['dates'], data['weights'], 'o-', 
                    color=colors[i % len(colors)], 
                    linewidth=2, markersize=6, 
                    label=ex_name[:15] + '...' if len(ex_name) > 15 else ex_name)
        
        ax3.set_title('Прогресс весов по упражнениям', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Дата')
        ax3.set_ylabel('Вес (кг)')
        ax3.grid(True, alpha=0.3)
        ax3.legend(loc='best')
        ax3.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        buf2 = io.BytesIO()
        plt.savefig(buf2, format='png', dpi=100)
        buf2.seek(0)
        plt.close()
    
    # Текстовая статистика
    total_workouts = sum(counts)
    total_volume = sum(volumes)
    avg_volume = total_volume / len(volumes) if volumes else 0
    
    # Получаем данные за прошлый месяц для сравнения
    prev_start = start_date - timedelta(days=30)
    prev_history = await db.fetch_all("""
        SELECT COUNT(*) as workout_count,
               SUM(sets * reps * COALESCE(weight, 1)) as total_volume
        FROM workouts 
        WHERE user_id = ? AND created_at BETWEEN ? AND ?
    """, (user_id, prev_start, start_date))
    
    comparison_text = ""
    if prev_history and prev_history[0]['workout_count']:
        prev_workouts = prev_history[0]['workout_count']
        prev_volume = prev_history[0]['total_volume'] or 0
        
        workout_diff = total_workouts - prev_workouts
        volume_diff = total_volume - prev_volume
        
        workout_trend = "📈" if workout_diff > 0 else "📉" if workout_diff < 0 else "➡️"
        volume_trend = "📈" if volume_diff > 0 else "📉" if volume_diff < 0 else "➡️"
        
        comparison_text = (
            f"\n\n*Сравнение с прошлым месяцем:*\n"
            f"{workout_trend} Тренировки: {workout_diff:+.0f}\n"
            f"{volume_trend} Объем: {volume_diff:+,.0f} кг"
        )
    
    # Формируем текст
    text = (
        f"📈 *Прогресс за 30 дней*\n\n"
        f"🏋️ Всего тренировок: {total_workouts}\n"
        f"⚖️ Общий объем: {total_volume:,.0f} кг\n"
        f"📊 Средний объем: {avg_volume:,.0f} кг/день"
        f"{comparison_text}"
    )
    
    # Отправляем первый график
    await callback.message.answer_photo(
        BufferedInputFile(buf1.read(), filename="progress_volume.png"),
        caption="📊 *Динамика тренировок*"
    )
    
    # Отправляем второй график (если есть данные о весе)
    if weights_data:
        await callback.message.answer_photo(
            BufferedInputFile(buf2.read(), filename="progress_weights.png"),
            caption="🏋️ *Прогресс весов по упражнениям*"
        )
    
    # Отправляем текстовую статистику
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="progress"),
        InlineKeyboardButton(text="📊 Детали", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main")
    )
    
    await callback.message.answer(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "stats")
async def show_detailed_stats(callback: CallbackQuery):
    """Детальная статистика"""
    user_id = callback.from_user.id
    
    # Получаем статистику по упражнениям
    exercises_stats = await db.fetch_all("""
        SELECT exercise_name, 
               COUNT(*) as times,
               MAX(weight) as max_weight,
               AVG(weight) as avg_weight
        FROM workouts 
        WHERE user_id = ? AND weight IS NOT NULL
        GROUP BY exercise_name
        ORDER BY times DESC
        LIMIT 10
    """, (user_id,))
    
    text = "📊 *Детальная статистика*\n\n"
    
    if exercises_stats:
        text += "*Топ упражнений:*\n"
        for i, ex in enumerate(exercises_stats, 1):
            text += f"{i}. {ex['exercise_name']}\n"
            text += f"   ▫️ Выполнялось: {ex['times']} раз\n"
            if ex['max_weight']:
                text += f"   ▫️ Макс. вес: {ex['max_weight']} кг\n"
                text += f"   ▫️ Сред. вес: {ex['avg_weight']:.1f} кг\n"
    else:
        text += "Пока недостаточно данных для статистики."
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="progress_stats")
        ).as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "export_data")
async def export_data(callback: CallbackQuery):
    """Экспорт данных пользователя"""
    user_id = callback.from_user.id
    
    await callback.message.answer("⏳ Начинаем экспорт ваших данных...")
    
    from services.export import export_user_data
    import os
    
    # Проверяем, существует ли папка exports
    if not os.path.exists('exports'):
        os.makedirs('exports')
        await callback.message.answer("📁 Создана папка для экспорта")
    
    file_path = await export_user_data(user_id)
    
    # ОТЛАДКА: проверим, что вернула функция
    await callback.message.answer(f"🔍 Путь к файлу: {file_path}")
    
    if file_path and os.path.exists(file_path):
        # Проверяем размер файла
        size = os.path.getsize(file_path)
        await callback.message.answer(f"📊 Размер файла: {size} байт")
        
        # Отправляем файл
        with open(file_path, 'rb') as file:
            await callback.message.answer_document(
                file,
                caption="✅ Ваши данные экспортированы в CSV файл."
            )
        
        # Удаляем файл после отправки
        os.remove(file_path)
        logger.info(f"Файл {file_path} удален после отправки")
    else:
        await callback.message.answer(
            f"❌ Не удалось экспортировать данные.\n"
            f"Путь: {file_path}\n"
            f"Файл существует: {os.path.exists(file_path) if file_path else False}"
        )
    
    await callback.answer()

def get_profile_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура профиля"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="📈 Прогресс", callback_data="progress"),
        InlineKeyboardButton(text="📅 Календарь", callback_data="calendar")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),
        InlineKeyboardButton(text="🔄 Экспорт", callback_data="export_data")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")  # Изменен текст
    )
    
    return builder.as_markup()