import sqlite3
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, date, timedelta

from database.base import db

router = Router()
logger = logging.getLogger(__name__)

# === ПРОВЕРКА И СОЗДАНИЕ ТАБЛИЦ ===
def ensure_workout_tables():
    """Создание таблиц для тренировок, если их нет"""
    try:
        conn = sqlite3.connect('fitness_bot.db')
        cursor = conn.cursor()
        
        # Создаем таблицу тренировок
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                start_time TEXT,
                end_time TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Создаем таблицу упражнений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_exercises (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                exercise_name TEXT NOT NULL,
                exercise_type TEXT DEFAULT 'strength',
                sets INTEGER,
                reps INTEGER,
                weight REAL,
                duration INTEGER,
                distance REAL,
                notes TEXT,
                order_num INTEGER
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Таблицы для тренировок созданы/проверены")
    except Exception as e:
        logger.error(f"❌ Ошибка создания таблиц: {e}")

# === ДОБАВЛЕНИЕ КОЛОНКИ COMPLETED ===
def add_completed_column():
    """Добавляет колонку completed, если её нет"""
    try:
        conn = sqlite3.connect('fitness_bot.db')
        cursor = conn.cursor()
        
        # Проверяем существование колонки
        cursor.execute("PRAGMA table_info(workout_exercises)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'completed' not in columns:
            cursor.execute("ALTER TABLE workout_exercises ADD COLUMN completed BOOLEAN DEFAULT FALSE")
            conn.commit()
            logger.info("✅ Колонка 'completed' успешно добавлена")
        else:
            logger.info("✅ Колонка 'completed' уже существует")
        
        conn.close()
    except Exception as e:
        logger.error(f"❌ Ошибка добавления колонки: {e}")

# Вызываем
ensure_workout_tables()
add_completed_column()

# === СИНХРОННАЯ ПРОВЕРКА КОЛОНКИ ===
def ensure_completed_column_sync():
    """Синхронная проверка и создание колонки completed"""
    try:
        conn = sqlite3.connect('fitness_bot.db')
        cursor = conn.cursor()
        
        # Проверяем существование колонки
        cursor.execute("PRAGMA table_info(workout_exercises)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'completed' not in columns:
            cursor.execute("ALTER TABLE workout_exercises ADD COLUMN completed BOOLEAN DEFAULT FALSE")
            conn.commit()
            logger.info("✅ Колонка 'completed' создана")
        else:
            logger.info("✅ Колонка 'completed' уже существует")
        
        conn.close()
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

# Вызываем сразу
ensure_completed_column_sync()

router = Router()
logger = logging.getLogger(__name__)

class EditExerciseStates(StatesGroup):
    waiting_new_weight = State()
    waiting_new_reps = State()
    waiting_new_sets = State()

# ================ ГЛАВНОЕ МЕНЮ ДНЕВНИКА ================

@router.callback_query(F.data == "workout_journal")
async def workout_journal_menu(callback: CallbackQuery):
    """Главное меню дневника тренировок"""
    text = (
        "📔 *Дневник тренировок*\n\n"
        "Выберите период:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 СЕГОДНЯ", callback_data="journal_today"),
        InlineKeyboardButton(text="📆 НЕДЕЛЯ", callback_data="journal_week")
    )
    builder.row(
        InlineKeyboardButton(text="📅 ПО ДНЯМ", callback_data="journal_by_date"),
        InlineKeyboardButton(text="📊 ПРОГРЕСС", callback_data="journal_progress")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ СЕГОДНЯ ================

@router.callback_query(F.data == "journal_today")
async def journal_today(callback: CallbackQuery):
    """Тренировки за сегодня"""
    user_id = callback.from_user.id
    today_str = date.today().isoformat()
    ensure_completed_column_sync()
    
    # Получаем сегодняшние тренировки
    exercises = await db.fetch_all("""
        SELECT we.id, we.exercise_name, we.sets, we.reps, we.weight, 
               ws.start_time
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ? AND ws.date = ?
        ORDER BY ws.start_time, we.order_num
    """, (user_id, today_str))
    
    if not exercises:
        text = "📅 *Сегодня*\n\nУ вас пока нет тренировок за сегодня."
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🏋️ НАЧАТЬ ТРЕНИРОВКУ", callback_data="start_workout"),
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="workout_journal")
        )
    else:
        text = f"📅 *Сегодня ({today_str})*\n\n"
        
        for ex in exercises:
            weight = f"{ex['weight']} кг" if ex['weight'] else "б/в"
            text += f"*{ex['exercise_name']}*\n"
            text += f"   {ex['sets']}×{ex['reps']} ({weight})\n"
        
        builder = InlineKeyboardBuilder()
        for ex in exercises:
            builder.row(
                InlineKeyboardButton(
                   text=f"✏️ {ex['exercise_name'][:15]}",
                   callback_data=f"edit_exercise:{ex['id']}"
                )
            )
        builder.row(
            InlineKeyboardButton(text="🔄 ОТМЕТИТЬ ВСЁ", callback_data="complete_all_today"),
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="workout_journal")
        )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ НЕДЕЛЯ ================

@router.callback_query(F.data == "journal_week")
async def journal_week(callback: CallbackQuery):
    """Тренировки за неделю"""
    user_id = callback.from_user.id
    
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    # Получаем тренировки за неделю
    week_data = await db.fetch_all("""
        SELECT 
            ws.date,
            COUNT(we.id) as exercises_count,
            SUM(we.sets * we.reps * COALESCE(we.weight, 1)) as total_volume,
            0 as completed_count  -- временно отключаем
        FROM workout_sessions ws
        LEFT JOIN workout_exercises we ON ws.id = we.session_id
        WHERE ws.user_id = ? AND ws.date BETWEEN ? AND ?
        GROUP BY ws.date
        ORDER BY ws.date DESC
    """, (user_id, start_date.isoformat(), end_date.isoformat()))
    
    if not week_data:
        text = "📆 *Неделя*\n\nНет тренировок за последние 7 дней."
    else:
        text = "📆 *Тренировки за неделю*\n\n"
        total_exercises = 0
        total_completed = 0
        
        for day in week_data:
            date_obj = datetime.strptime(day['date'], '%Y-%m-%d')
            day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
            exercises = day['exercises_count'] or 0
            completed = day['completed_count'] or 0
            volume = int(day['total_volume'] or 0)
            
            total_exercises += exercises
            total_completed += completed
            
            progress = f"{completed}/{exercises}" if exercises > 0 else "0"
            text += f"{day_name} {date_obj.day:02d}: {progress} упр, {volume:,} кг\n"
        
        text += f"\n📊 Итого: {total_completed}/{total_exercises} упражнений"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 ПО ДНЯМ", callback_data="journal_by_date"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="workout_journal")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ВЫБОР ДАТЫ ================

@router.callback_query(F.data == "journal_by_date")
async def journal_by_date(callback: CallbackQuery):
    """Выбор даты"""
    user_id = callback.from_user.id
    
    # Получаем все даты с тренировками
    dates = await db.fetch_all("""
        SELECT DISTINCT date
        FROM workout_sessions
        WHERE user_id = ?
        ORDER BY date DESC
        LIMIT 30
    """, (user_id,))
    
    if not dates:
        text = "📅 *Выбор даты*\n\nУ вас пока нет тренировок."
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="workout_journal")
        )
    else:
        text = "📅 *Выберите дату:*\n\n"
        builder = InlineKeyboardBuilder()
        
        for d in dates:
            date_obj = datetime.strptime(d['date'], '%Y-%m-%d')
            day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
            text += f"• {day_name} {date_obj.day:02d}.{date_obj.month:02d}\n"
            
            builder.row(
                InlineKeyboardButton(
                    text=f"{day_name} {date_obj.day:02d}.{date_obj.month:02d}",
                    callback_data=f"journal_date:{d['date']}"
                )
            )
        builder.row(
            InlineKeyboardButton(text="↩️ НАЗАД", callback_data="workout_journal")
        )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("journal_date:"))
async def journal_show_date(callback: CallbackQuery):
    """Показать тренировки за выбранную дату"""
    user_id = callback.from_user.id
    selected_date = callback.data.split(":")[1]
    
    # Получаем тренировки за выбранную дату
    exercises = await db.fetch_all("""
        SELECT we.id, we.exercise_name, we.sets, we.reps, we.weight, 
               ws.start_time
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ? AND ws.date = ?
        ORDER BY ws.start_time, we.order_num
    """, (user_id, selected_date))
    
    if not exercises:
        text = f"📅 *{selected_date}*\n\nНет тренировок за этот день."
    else:
        date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
        text = f"📅 *{day_name}, {selected_date}*\n\n"
        
        for ex in exercises:
            weight = f"{ex['weight']} кг" if ex['weight'] else "б/в"
            text += f"*{ex['exercise_name']}*\n"
            text += f"   {ex['sets']}×{ex['reps']} ({weight})\n"
        
        builder = InlineKeyboardBuilder()
        for ex in exercises:
            builder.row(
                InlineKeyboardButton(
                   text=f"✏️ {ex['exercise_name'][:15]}",
                   callback_data=f"edit_exercise:{ex['id']}"
                )
            )
        builder.row(
            InlineKeyboardButton(text="↩️ К ДАТАМ", callback_data="journal_by_date"),
            InlineKeyboardButton(text="◀️ НАЗАД", callback_data="workout_journal")
        )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ РЕДАКТИРОВАНИЕ УПРАЖНЕНИЯ ================

@router.callback_query(F.data.startswith("edit_exercise:"))
async def edit_exercise_menu(callback: CallbackQuery, state: FSMContext):
    """Меню редактирования упражнения"""
    exercise_id = int(callback.data.split(":")[1])
    
    # Получаем данные упражнения
    exercise = await db.fetch_one("""
        SELECT we.*, ws.date, ws.user_id
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE we.id = ?
    """, (exercise_id,))
    
    if not exercise:
        await callback.answer("❌ Упражнение не найдено")
        return
    
    # Проверяем, что это упражнение принадлежит пользователю
    if exercise['user_id'] != callback.from_user.id:
        await callback.answer("❌ Нет доступа")
        return
    
    await state.update_data(exercise_id=exercise_id)
    
    weight = f"{exercise['weight']} кг" if exercise['weight'] else "без веса"
    status = "✅ Выполнено" if exercise['completed'] else "⭕ Не выполнено"
    
    text = (
        f"✏️ *Редактирование*\n\n"
        f"*{exercise['exercise_name']}*\n"
        f"📊 {exercise['sets']}×{exercise['reps']} ({weight})\n"
        f"📌 Статус: {status}\n\n"
        f"Что хотите изменить?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Повторения", callback_data=f"edit_reps:{exercise_id}"),
        InlineKeyboardButton(text="⚖️ Вес", callback_data=f"edit_weight:{exercise_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📊 Подходы", callback_data=f"edit_sets:{exercise_id}"),
        InlineKeyboardButton(text="✅ Отметить выполненным", callback_data=f"toggle_complete:{exercise_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ Удалить", callback_data=f"delete_exercise:{exercise_id}"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="journal_today")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("edit_weight:"))
async def edit_weight_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования веса"""
    exercise_id = int(callback.data.split(":")[1])
    await state.update_data(exercise_id=exercise_id, edit_type="weight")
    
    await callback.message.edit_text(
        "⚖️ *Изменить вес*\n\n"
        "Введите новый вес (кг) или '-' если без веса:"
    )
    await state.set_state(EditExerciseStates.waiting_new_weight)
    await callback.answer()

@router.message(EditExerciseStates.waiting_new_weight)
async def process_new_weight(message: Message, state: FSMContext):
    """Обработка нового веса"""
    data = await state.get_data()
    exercise_id = data['exercise_id']
    
    try:
        new_weight = None if message.text == '-' else float(message.text)
        
        await db.execute(
            "UPDATE workout_exercises SET weight = ? WHERE id = ?",
            (new_weight, exercise_id)
        )
        
        await message.answer(
            "✅ Вес обновлен!",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="↩️ В ДНЕВНИК", callback_data="journal_today")
            ).as_markup()
        )
    except ValueError:
        await message.answer("❌ Введите корректное число или '-'")
        return
    
    await state.clear()

@router.callback_query(F.data.startswith("edit_reps:"))
async def edit_reps_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования повторений"""
    exercise_id = int(callback.data.split(":")[1])
    await state.update_data(exercise_id=exercise_id, edit_type="reps")
    
    await callback.message.edit_text(
        "🔄 *Изменить повторения*\n\n"
        "Введите новое количество повторений:"
    )
    await state.set_state(EditExerciseStates.waiting_new_reps)
    await callback.answer()

@router.message(EditExerciseStates.waiting_new_reps)
async def process_new_reps(message: Message, state: FSMContext):
    """Обработка новых повторений"""
    data = await state.get_data()
    exercise_id = data['exercise_id']
    
    try:
        new_reps = int(message.text)
        if new_reps <= 0:
            raise ValueError
        
        await db.execute(
            "UPDATE workout_exercises SET reps = ? WHERE id = ?",
            (new_reps, exercise_id)
        )
        
        await message.answer(
            "✅ Повторения обновлены!",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="↩️ В ДНЕВНИК", callback_data="journal_today")
            ).as_markup()
        )
    except ValueError:
        await message.answer("❌ Введите положительное число")
        return
    
    await state.clear()

@router.callback_query(F.data.startswith("edit_sets:"))
async def edit_sets_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования подходов"""
    exercise_id = int(callback.data.split(":")[1])
    await state.update_data(exercise_id=exercise_id, edit_type="sets")
    
    await callback.message.edit_text(
        "📊 *Изменить подходы*\n\n"
        "Введите новое количество подходов:"
    )
    await state.set_state(EditExerciseStates.waiting_new_sets)
    await callback.answer()

@router.message(EditExerciseStates.waiting_new_sets)
async def process_new_sets(message: Message, state: FSMContext):
    """Обработка новых подходов"""
    data = await state.get_data()
    exercise_id = data['exercise_id']
    
    try:
        new_sets = int(message.text)
        if new_sets <= 0:
            raise ValueError
        
        await db.execute(
            "UPDATE workout_exercises SET sets = ? WHERE id = ?",
            (new_sets, exercise_id)
        )
        
        await message.answer(
            "✅ Подходы обновлены!",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="↩️ В ДНЕВНИК", callback_data="journal_today")
            ).as_markup()
        )
    except ValueError:
        await message.answer("❌ Введите положительное число")
        return
    
    await state.clear()

@router.callback_query(F.data.startswith("toggle_complete:"))
async def toggle_complete(callback: CallbackQuery):
    """Отметить упражнение как выполненное/невыполненное"""
    exercise_id = int(callback.data.split(":")[1])
    
    # Получаем текущий статус
    exercise = await db.fetch_one(
        "SELECT completed FROM workout_exercises WHERE id = ?",
        (exercise_id,)
    )
    
    if exercise:
        new_status = not exercise['completed']
        await db.execute(
            "UPDATE workout_exercises SET completed = ? WHERE id = ?",
            (new_status, exercise_id)
        )
        
        status_text = "выполненным" if new_status else "невыполненным"
        await callback.answer(f"✅ Упражнение отмечено {status_text}")
    
    await edit_exercise_menu(callback, None)

@router.callback_query(F.data.startswith("delete_exercise:"))
async def delete_exercise(callback: CallbackQuery):
    """Удалить упражнение"""
    exercise_id = int(callback.data.split(":")[1])
    
    # Проверяем, что это последнее упражнение в сессии
    session = await db.fetch_one("""
        SELECT session_id FROM workout_exercises WHERE id = ?
    """, (exercise_id,))
    
    if session:
        # Удаляем упражнение
        await db.execute(
            "DELETE FROM workout_exercises WHERE id = ?",
            (exercise_id,)
        )
        
        # Проверяем, остались ли еще упражнения в сессии
        remaining = await db.fetch_one("""
            SELECT COUNT(*) as count FROM workout_exercises WHERE session_id = ?
        """, (session['session_id'],))
        
        # Если упражнений не осталось, удаляем и сессию
        if remaining['count'] == 0:
            await db.execute(
                "DELETE FROM workout_sessions WHERE id = ?",
                (session['session_id'],)
            )
        
        await callback.answer("❌ Упражнение удалено")
    
    await callback.message.edit_text(
        "✅ Упражнение удалено",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="↩️ В ДНЕВНИК", callback_data="journal_today")
        ).as_markup()
    )

# ================ ПРОГРЕСС ================

@router.callback_query(F.data == "journal_progress")
async def journal_progress(callback: CallbackQuery):
    """Прогресс по упражнениям"""
    user_id = callback.from_user.id
    
    # Получаем прогресс по основным упражнениям
    progress = await db.fetch_all("""
        SELECT 
            we.exercise_name,
            MIN(we.weight) as min_weight,
            MAX(we.weight) as max_weight,
            AVG(we.weight) as avg_weight,
            COUNT(*) as times,
            MAX(we.reps) as max_reps
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ? AND we.weight IS NOT NULL
        GROUP BY we.exercise_name
        ORDER BY times DESC
        LIMIT 10
    """, (user_id,))
    
    if not progress:
        text = "📊 *Прогресс*\n\nНедостаточно данных."
    else:
        text = "📊 *Прогресс по упражнениям*\n\n"
        for p in progress:
            text += f"*{p['exercise_name']}*\n"
            text += f"📈 Макс: {p['max_weight']} кг | Мин: {p['min_weight']} кг\n"
            text += f"📊 Средний: {p['avg_weight']:.1f} кг | Выполнено: {p['times']} раз\n"
            if p['max_reps']:
                text += f"🔄 Макс повторений: {p['max_reps']}\n"
            text += "\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 ГРАФИКИ", callback_data="progress_charts"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="workout_journal")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ДОБАВИТЬ КНОПКУ В ГЛАВНОЕ МЕНЮ ================
# Нужно добавить в keyboards/main.py:
# InlineKeyboardButton(text="📔 ДНЕВНИК", callback_data="workout_journal")