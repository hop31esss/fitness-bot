import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database.base import db
from services.progress_analytics import (
    fetch_canonical_history,
    fetch_day_exercises,
    fetch_week_journal,
    format_kg,
)
from utils.clock import today as local_today

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
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="menu_training")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ СЕГОДНЯ ================

@router.callback_query(F.data == "journal_today")
async def journal_today(callback: CallbackQuery):
    """Тренировки за сегодня"""
    user_id = callback.from_user.id
    today_str = local_today().isoformat()
    exercises = await fetch_day_exercises(user_id, today_str)
    
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
            weight = f"{ex['weight']:g} кг" if ex['weight'] else "б/в"
            text += f"*{ex['exercise_name']}*\n"
            text += f"   {ex['sets']}×{int(ex['reps'])} ({weight}) · {format_kg(ex['volume'])} кг\n"
        
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
    
    end_date = local_today()
    start_date = end_date - timedelta(days=7)
    
    week_data = await fetch_week_journal(
        user_id, start_date.isoformat(), end_date.isoformat()
    )
    
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
            volume = format_kg(day['total_volume'] or 0)
            
            total_exercises += exercises
            total_completed += completed
            
            progress = f"{completed}/{exercises}" if exercises > 0 else "0"
            text += f"{day_name} {date_obj.day:02d}: {progress} упр, {volume} кг\n"
        
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
    
    exercises = await fetch_day_exercises(user_id, selected_date)
    
    builder = InlineKeyboardBuilder()
    if not exercises:
        text = f"📅 *{selected_date}*\n\nНет тренировок за этот день."
        builder.row(
            InlineKeyboardButton(text="↩️ К ДАТАМ", callback_data="journal_by_date")
        )
    else:
        date_obj = datetime.strptime(selected_date, '%Y-%m-%d')
        day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
        text = f"📅 *{day_name}, {selected_date}*\n\n"
        
        for ex in exercises:
            weight = f"{ex['weight']:g} кг" if ex['weight'] else "б/в"
            text += f"*{ex['exercise_name']}*\n"
            text += f"   {ex['sets']}×{int(ex['reps'])} ({weight}) · {format_kg(ex['volume'])} кг\n"
        
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
    
    if state is not None:
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
        if not message.text:
            raise ValueError
        new_weight = 0.0 if message.text.strip() == '-' else float(message.text.replace(",", "."))
        if new_weight < 0:
            raise ValueError
        
        await db.execute(
            "UPDATE workout_exercises SET weight = ? WHERE id = ?",
            (new_weight, exercise_id)
        )
        await db.execute(
            "UPDATE workout_sets SET weight = ? WHERE workout_exercise_id = ?",
            (new_weight, exercise_id),
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
        if not message.text:
            raise ValueError
        new_reps = int(message.text)
        if new_reps <= 0:
            raise ValueError
        
        await db.execute(
            "UPDATE workout_exercises SET reps = ? WHERE id = ?",
            (new_reps, exercise_id)
        )
        await db.execute(
            "UPDATE workout_sets SET reps = ? WHERE workout_exercise_id = ?",
            (new_reps, exercise_id),
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
        if not message.text:
            raise ValueError
        new_sets = int(message.text)
        if new_sets <= 0:
            raise ValueError
        
        exercise = await db.fetch_one(
            "SELECT reps, weight, completed FROM workout_exercises WHERE id = ?",
            (exercise_id,),
        )
        if not exercise:
            await message.answer("❌ Упражнение не найдено.")
            await state.clear()
            return
        await db.execute(
            "UPDATE workout_exercises SET sets = ? WHERE id = ?",
            (new_sets, exercise_id)
        )
        # Изменение агрегатного количества подходов означает одинаковые подходы.
        await db.execute(
            "DELETE FROM workout_sets WHERE workout_exercise_id = ?",
            (exercise_id,),
        )
        await db.execute_many(
            """INSERT INTO workout_sets
               (workout_exercise_id, set_number, weight, reps, completed)
               VALUES (?, ?, ?, ?, ?)""",
            [
                (
                    exercise_id,
                    set_number,
                    float(exercise["weight"] or 0),
                    int(exercise["reps"] or 0),
                    bool(exercise["completed"]),
                )
                for set_number in range(1, new_sets + 1)
            ],
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
        await db.execute(
            "UPDATE workout_sets SET completed = ? WHERE workout_exercise_id = ?",
            (new_status, exercise_id),
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
            "DELETE FROM workout_sets WHERE workout_exercise_id = ?",
            (exercise_id,),
        )
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
    
    history = await fetch_canonical_history(user_id)
    grouped: dict[str, dict] = {}
    for row in history:
        if row["weight"] <= 0:
            continue
        name = row["exercise_name"]
        item = grouped.setdefault(
            name,
            {"min_weight": row["weight"], "max_weight": row["weight"], "sum_weight": 0.0,
             "n": 0, "times": set(), "max_reps": 0},
        )
        item["min_weight"] = min(item["min_weight"], row["weight"])
        item["max_weight"] = max(item["max_weight"], row["weight"])
        item["sum_weight"] += row["weight"]
        item["n"] += 1
        item["times"].add(row["workout_exercise_id"])
        item["max_reps"] = max(item["max_reps"], row["reps"])
    progress = sorted(
        (
            {
                "exercise_name": name,
                "min_weight": data["min_weight"],
                "max_weight": data["max_weight"],
                "avg_weight": data["sum_weight"] / data["n"],
                "times": len(data["times"]),
                "max_reps": data["max_reps"],
            }
            for name, data in grouped.items()
        ),
        key=lambda item: item["times"],
        reverse=True,
    )[:10]
    
    if not progress:
        text = "📊 *Прогресс*\n\nНедостаточно данных."
    else:
        text = "📊 *Прогресс по упражнениям*\n\n"
        for p in progress:
            text += f"*{p['exercise_name']}*\n"
            text += f"📈 Макс: {format_kg(p['max_weight'], 1)} кг | Мин: {format_kg(p['min_weight'], 1)} кг\n"
            text += f"📊 Средний: {format_kg(p['avg_weight'], 1)} кг | Выполнено: {p['times']} раз\n"
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