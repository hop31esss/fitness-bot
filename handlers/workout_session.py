from aiogram import Router, F
import json
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from database.base import db
from services.premium_triggers import maybe_send_workout_milestone_prompt
from handlers.referral import maybe_grant_referrer_retention_bonus
from utils.units import to_kg
from utils.clock import now, now_hm, today_iso

router = Router()
logger = logging.getLogger(__name__)


def _exact_sets(exercise: dict) -> list[tuple[int, int, float]]:
    """Return normalized (set number, reps, kg) rows for a strength exercise."""
    count = max(0, int(exercise.get("sets") or 0))
    set_data = exercise.get("set_data") or []
    reps_list = exercise.get("reps_list") or []
    weights = exercise.get("weights") or []
    rows = []
    for index in range(count):
        details = set_data[index] if index < len(set_data) else {}
        reps = details.get(
            "reps",
            reps_list[index] if index < len(reps_list) else exercise.get("reps", 0),
        )
        weight = details.get(
            "weight",
            weights[index] if index < len(weights) else exercise.get("weight", 0),
        )
        rows.append((index + 1, max(0, int(reps or 0)), max(0.0, float(weight or 0))))
    return rows


def _replace_exact_sets(
    exercise: dict,
    *,
    count: int | None = None,
    reps: int | None = None,
    weight: float | None = None,
) -> None:
    """Apply an aggregate edit without discarding untouched per-set values."""
    rows = _exact_sets(exercise)
    target_count = len(rows) if count is None else max(1, count)
    seed_reps = rows[-1][1] if rows else max(0, int(exercise.get("reps") or 0))
    seed_weight = rows[-1][2] if rows else max(0.0, float(exercise.get("weight") or 0))
    while len(rows) < target_count:
        rows.append((len(rows) + 1, seed_reps, seed_weight))
    rows = rows[:target_count]
    exercise["sets"] = target_count
    exercise["set_data"] = [
        {
            "reps": reps if reps is not None else row_reps,
            "weight": weight if weight is not None else row_weight,
            "weight_done": True,
        }
        for _, row_reps, row_weight in rows
    ]
    exercise.pop("reps_list", None)
    exercise.pop("weights", None)
    if reps is not None:
        exercise["reps"] = reps
        exercise["reps_display"] = str(reps)
    if weight is not None:
        exercise["weight"] = weight
        exercise["weight_display"] = f"{weight:g} кг" if weight else "б/в"


def planned_to_live_exercise(exercise: dict) -> dict:
    """Turn a saved program row into the live workout format with per-set data."""
    if exercise.get("type") and exercise.get("type") != "strength":
        return dict(exercise)
    sets = max(1, int(exercise.get("sets") or 0))
    reps = int(exercise.get("reps") or 0)
    weight = exercise.get("weight")
    try:
        weight = None if weight in (None, "", "-") else float(weight)
    except (TypeError, ValueError):
        weight = None
    live = {
        "name": exercise.get("name") or "Упражнение",
        "type": "strength",
        "sets": sets,
        "reps": reps,
        "weight": weight,
        "set_data": [
            {"reps": reps, "weight": weight, "weight_done": True}
            for _ in range(sets)
        ],
        "reps_display": str(reps),
        "weight_display": f"{weight:g} кг" if weight else "б/в",
        "planned_sets": sets,
        "planned_reps": reps,
        "planned_weight": weight,
    }
    return live


async def delete_workout_session(session_id: int | None) -> None:
    if not session_id:
        return
    await db.execute("DELETE FROM workout_sessions WHERE id = ?", (session_id,))


async def delete_empty_sessions(
    user_id: int | None = None,
    keep_session_id: int | None = None,
) -> None:
    """Drop sessions that never received exercises so they do not clutter history."""
    clauses = [
        "id NOT IN (SELECT DISTINCT session_id FROM workout_exercises)",
        """id NOT IN (
            SELECT CAST(json_extract(session_data, '$.session_id') AS INTEGER)
            FROM active_workout_sessions
            WHERE json_extract(session_data, '$.session_id') IS NOT NULL
        )""",
    ]
    params: list = []
    if user_id is not None:
        clauses.append("user_id = ?")
        params.append(user_id)
    if keep_session_id is not None:
        clauses.append("id != ?")
        params.append(keep_session_id)
    await db.execute(
        f"DELETE FROM workout_sessions WHERE {' AND '.join(clauses)}",
        tuple(params),
    )


async def persist_session_exercises_from_state(session_id: int, exercises: list):
    """Atomically replace canonical exercise rows and their exact sets."""
    if not db.conn:
        await db.connect()
    conn = db.conn
    await conn.execute("BEGIN IMMEDIATE")
    try:
        await conn.execute(
            """
            DELETE FROM workout_sets
            WHERE workout_exercise_id IN (
                SELECT id FROM workout_exercises WHERE session_id = ?
            )
            """,
            (session_id,),
        )
        await conn.execute("DELETE FROM workout_exercises WHERE session_id = ?", (session_id,))
        cursor = await conn.execute(
            """
            SELECT COALESCE(us.units, 'kg') AS units
            FROM workout_sessions ws
            LEFT JOIN user_settings us ON us.user_id = ws.user_id
            WHERE ws.id = ?
            """,
            (session_id,),
        )
        units_row = await cursor.fetchone()
        units = units_row["units"] if units_row else "kg"
        for order_num, exercise in enumerate(exercises, start=1):
            if exercise.get("type") != "strength":
                continue
            exact_sets = [
                (number, reps, to_kg(weight, units))
                for number, reps, weight in _exact_sets(exercise)
            ]
            aggregate_reps = (
                int(round(sum(item[1] for item in exact_sets) / len(exact_sets)))
                if exact_sets else 0
            )
            aggregate_weight = (
                sum(item[2] for item in exact_sets) / len(exact_sets)
                if exact_sets else 0
            )
            cursor = await conn.execute(
                """
                INSERT INTO workout_exercises
                    (session_id, exercise_name, exercise_type, sets, reps, weight,
                     planned_sets, planned_reps, planned_weight, order_num)
                VALUES (?, ?, 'strength', ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id, exercise.get("name"), len(exact_sets),
                    aggregate_reps, aggregate_weight,
                    exercise.get("planned_sets"), exercise.get("planned_reps"),
                    exercise.get("planned_weight"), order_num,
                ),
            )
            exercise_id = cursor.lastrowid
            if exact_sets:
                await conn.executemany(
                    """
                    INSERT INTO workout_sets
                        (workout_exercise_id, set_number, reps, weight, completed)
                    VALUES (?, ?, ?, ?, TRUE)
                    """,
                    [
                        (exercise_id, set_number, reps, weight)
                        for set_number, reps, weight in exact_sets
                    ],
                )
        await conn.commit()
    except Exception:
        await conn.rollback()
        raise

class WorkoutSessionStates(StatesGroup):
    choosing_exercise_type = State()
    entering_exercise_name = State()
    entering_sets = State()
    choosing_reps_method = State()  # НОВОЕ: выбор метода ввода повторений
    entering_set_data = State()
    entering_set_reps = State()      # НОВОЕ: ввод повторений по подходам
    entering_reps = State()          # для одинаковых повторений
    choosing_weight_method = State()  # выбор метода ввода веса
    entering_set_weights = State()    # ввод веса по подходам
    entering_weight = State()         # для одного веса
    entering_duration = State()
    entering_distance = State()
    editing_exercise_value = State()

@router.callback_query(F.data == "start_workout")
async def start_workout(callback: CallbackQuery, state: FSMContext):
    """Начало новой тренировки"""
    user_id = callback.from_user.id
    restored = await load_workout_session(user_id, state)
    data = await state.get_data() if restored else {}
    keep_id = data.get("session_id")
    await delete_empty_sessions(user_id, keep_session_id=keep_id)

    if restored:
        session_id = data.get("session_id")
        exercises = data.get("exercises") or []
        exists = None
        if session_id:
            exists = await db.fetch_one(
                "SELECT id FROM workout_sessions WHERE id = ?",
                (session_id,),
            )
        if exercises:
            if not exists:
                await db.execute(
                    "INSERT INTO workout_sessions (user_id, date, start_time) VALUES (?, ?, ?)",
                    (user_id, today_iso(), now_hm()),
                )
                row = await db.fetch_one("SELECT last_insert_rowid() as id")
                await state.update_data(session_id=row["id"])
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="✅ ПРОДОЛЖИТЬ", callback_data="continue_workout"),
                InlineKeyboardButton(text="🆕 НАЧАТЬ ЗАНОВО", callback_data="new_workout")
            )
            await callback.message.edit_text(
                "💪 *У вас есть незавершённая тренировка!*\n\n"
                "Хотите продолжить или начать новую?",
                reply_markup=builder.as_markup()
            )
            await callback.answer()
            return
        await delete_workout_session(session_id)
        await clear_workout_session(user_id)
        await state.clear()

    await start_new_workout(callback.message, state)
    await callback.answer()

async def start_new_workout(message, state: FSMContext):
    """Начинает новую тренировку"""
    user_id = message.chat.id
    
    # Создаём новую сессию в БД
    today = today_iso()
    current_time = now_hm()
    
    await db.execute(
        "INSERT INTO workout_sessions (user_id, date, start_time) VALUES (?, ?, ?)",
        (user_id, today, current_time)
    )
    
    result = await db.fetch_one("SELECT last_insert_rowid() as id")
    session_id = result['id']
    
    await state.update_data(
        session_id=session_id,
        exercises=[]
    )
    
    await show_workout_menu(message, state)

@router.callback_query(F.data == "continue_workout")
async def continue_workout(callback: CallbackQuery, state: FSMContext):
    """Продолжить сохранённую тренировку"""
    await show_workout_menu(callback.message, state)
    await callback.answer()

@router.callback_query(F.data == "new_workout")
async def new_workout(callback: CallbackQuery, state: FSMContext):
    """Начать новую тренировку (удаляя старую)"""
    user_id = callback.from_user.id
    data = await state.get_data()
    await delete_workout_session(data.get("session_id"))
    await clear_workout_session(user_id)
    await state.clear()
    await start_new_workout(callback.message, state)
    await callback.answer()

async def _show_workout_menu_legacy(message, state: FSMContext):
    """Legacy версия меню тренировки (не используется)."""
    data = await state.get_data()
    exercises = data.get('exercises', [])
    
    text = "🏋️ *ТЕКУЩАЯ ТРЕНИРОВКА*\n\n"
    
    if exercises:
        text += "*Упражнения:*\n"
        for i, ex in enumerate(exercises, 1):
            if ex['type'] == 'strength':
                text += f"{i}. {ex['name']}: {ex['sets']}×{ex['reps_display']} ({ex['weight_display']})\n"
                
                # Детали по подходам
                if 'set_data' in ex:
                    for j, s in enumerate(ex['set_data'], 1):
                        weight = f"{s['weight']} кг" if s['weight'] else "б/в"
                        text += f"   {j}. {weight} × {s['reps']}\n"
            elif ex['type'] == 'cardio':
                text += f"{i}. {ex['name']}: {ex['duration']} мин, {ex['distance']} км\n"
            else:
                text += f"{i}. {ex['name']}: {ex['duration']} мин (растяжка)\n"
    else:
        text += "Пока нет упражнений. Добавьте первое!\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ УПРАЖНЕНИЕ", callback_data="add_to_workout")
    )
    builder.row(
        InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ", callback_data="finish_workout"),
        InlineKeyboardButton(text="💾 СОХРАНИТЬ И ВЫЙТИ", callback_data="save_workout")
    )
    builder.row(
        InlineKeyboardButton(text="❌ ОТМЕНИТЬ", callback_data="cancel_workout")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "save_workout")
async def save_workout(callback: CallbackQuery, state: FSMContext):
    """Сохранить тренировку и выйти"""
    user_id = callback.from_user.id
    logger.info(f"💾 Попытка сохранения тренировки для пользователя {user_id}")
    
    try:
        data = await state.get_data()
        logger.info(f"📦 Данные тренировки: {data.get('exercises', [])}")
        if not data.get("exercises"):
            await delete_workout_session(data.get("session_id"))
            await clear_workout_session(user_id)
            await state.clear()
            await callback.message.edit_text(
                "❌ Нечего сохранять: нет упражнений.",
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="🏠 В ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
                ).as_markup(),
            )
            await callback.answer()
            return
        
        await save_workout_session(user_id, state)
        logger.info("✅ Тренировка сохранена в БД")
        
        await callback.message.edit_text(
            "💾 *Тренировка сохранена!*\n\n"
            "Вы можете вернуться к ней позже через меню тренировок.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🏠 В ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
            ).as_markup()
        )
        logger.info("✅ Сообщение отправлено пользователю")
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")
        await callback.message.answer(f"❌ Ошибка: {e}")
    
    await callback.answer()

# ========== СОХРАНЕНИЕ И ЗАГРУЗКА СЕССИИ ==========

async def save_workout_session(user_id: int, state: FSMContext):
    """Сохраняет текущую тренировку в БД"""
    data = await state.get_data()
    logger.info(f"💾 Сохранение для {user_id}, данные: {data}")
    
    # Сохраняем только нужные данные (исключаем временные)
    session_data = {
        'session_id': data.get('session_id'),
        'exercises': data.get('exercises', []),
        'start_time': now().isoformat()
    }
    
    logger.info(f"📦 session_data: {session_data}")
    
    await db.execute("""
        INSERT OR REPLACE INTO active_workout_sessions (user_id, session_data)
        VALUES (?, ?)
    """, (user_id, json.dumps(session_data)))
    
    logger.info(f"💾 Тренировка сохранена для пользователя {user_id}")

async def load_workout_session(user_id: int, state: FSMContext):
    """Загружает сохранённую тренировку"""
    session = await db.fetch_one(
        "SELECT session_data FROM active_workout_sessions WHERE user_id = ?",
        (user_id,)
    )
    
    if session:
        data = json.loads(session['session_data'])
        await state.update_data(**data)
        return True
    return False

async def clear_workout_session(user_id: int):
    """Очищает сохранённую тренировку"""
    await db.execute(
        "DELETE FROM active_workout_sessions WHERE user_id = ?",
        (user_id,)
    )

async def show_workout_menu(message, state: FSMContext):
    """Показать меню тренировки с деталями"""
    data = await state.get_data()
    exercises = data.get('exercises', [])
    template_id = data.get("template_id")
    
    text = "🏋️ *ТЕКУЩАЯ ТРЕНИРОВКА*\n\n"
    if template_id:
        text += "📚 Режим: по программе\n\n"
    
    if exercises:
        text += "*Упражнения:*\n"
        for i, ex in enumerate(exercises, 1):
            if ex['type'] == 'strength':
                text += f"{i}. {ex['name']}: {ex['sets']}×{ex['reps_display']} ({ex['weight_display']})\n"
                
                # Детали по подходам (если нужно)
                if 'set_data' in ex:
                    details = ""
                    for j, s in enumerate(ex['set_data'], 1):
                        weight = f"{s['weight']} кг" if s['weight'] else "б/в"
                        details += f"   {j}. {weight} × {s['reps']}\n"
                    text += details
                    
            elif ex['type'] == 'cardio':
                text += f"{i}. {ex['name']}: {ex['duration']} мин, {ex['distance']} км\n"
            else:  # stretch
                text += f"{i}. {ex['name']}: {ex['duration']} мин (растяжка)\n"
        text += "\n"
    else:
        text += "Пока нет упражнений. Добавьте первое!\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ УПРАЖНЕНИЕ", callback_data="add_to_workout")
    )
    if exercises:
        builder.row(
            InlineKeyboardButton(text="✏️ ИЗМЕНИТЬ УПРАЖНЕНИЯ", callback_data="edit_workout_exercises")
        )
    builder.row(
        InlineKeyboardButton(text="✅ ЗАВЕРШИТЬ ТРЕНИРОВКУ", callback_data="finish_workout"),
        InlineKeyboardButton(text="❌ ОТМЕНИТЬ", callback_data="cancel_workout")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

async def save_exercise_from_set_data(state: FSMContext, message: Message):
    """Сохранить упражнение из данных по подходам"""
    data = await state.get_data()
    
    exercise = {
        'name': data['exercise_name'],
        'type': data['current_exercise_type'],
        'sets': data['sets'],
        'set_data': data['set_data']
    }
    
    # Формируем отображение
    weight_values = [s['weight'] for s in data['set_data'] if s['weight'] is not None]
    reps_values = [s['reps'] for s in data['set_data']]
    
    if weight_values:
        min_w = min(weight_values)
        max_w = max(weight_values)
        weight_display = f"{min_w}-{max_w} кг" if min_w != max_w else f"{min_w} кг"
    else:
        weight_display = "б/в"
    
    if len(set(reps_values)) == 1:
        reps_display = str(reps_values[0])
    else:
        min_r = min(reps_values)
        max_r = max(reps_values)
        reps_display = f"{min_r}-{max_r}"
    
    exercise['weight_display'] = weight_display
    exercise['reps_display'] = reps_display
    
    # Добавляем к списку упражнений
    exercises = data.get('exercises', [])
    exercises.append(exercise)
    await state.update_data(exercises=exercises)
    
    try:
        await persist_session_exercises_from_state(data["session_id"], exercises)
        logger.info(f"✅ Упражнение {exercise['name']} сохранено")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения упражнения: {e}")    

@router.callback_query(F.data == "add_to_workout")
async def add_to_workout(callback: CallbackQuery, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ СИЛОВОЕ", callback_data="ex_type_strength"),
        InlineKeyboardButton(text="🏃 КАРДИО", callback_data="ex_type_cardio")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_workout")
    )
    await callback.message.edit_text("Выберите тип упражнения:", reply_markup=builder.as_markup())
    await state.set_state(WorkoutSessionStates.choosing_exercise_type)
    await callback.answer()

@router.callback_query(F.data.startswith("ex_type_"))
async def process_exercise_type(callback: CallbackQuery, state: FSMContext):
    ex_type = callback.data.replace("ex_type_", "")
    await state.update_data(current_exercise_type=ex_type)
    await callback.message.edit_text("Введите название упражнения:")
    await state.set_state(WorkoutSessionStates.entering_exercise_name)
    await callback.answer()

@router.message(WorkoutSessionStates.entering_exercise_name)
async def process_exercise_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пришлите название текстом или /cancel.")
        return
    await state.update_data(exercise_name=message.text.strip())
    data = await state.get_data()
    if data['current_exercise_type'] == 'strength':
        await message.answer("Введите количество подходов:")
        await state.set_state(WorkoutSessionStates.entering_sets)
    else:
        await message.answer("Введите длительность (мин):")
        await state.set_state(WorkoutSessionStates.entering_duration)

@router.message(WorkoutSessionStates.entering_sets)
async def process_sets(message: Message, state: FSMContext):
    """Обработка подходов - начинаем ввод данных по подходам"""
    if not message.text:
        await message.answer("❌ Введите число")
        return
    try:
        sets = int(message.text)
        if sets <= 0:
            raise ValueError
        
        # Инициализируем данные для подходов
        set_data = []
        for i in range(sets):
            set_data.append({'weight': None, 'reps': None, 'weight_done': False})
        
        await state.update_data(
            sets=sets,
            set_data=set_data,
            current_set=1
        )
        
        # Начинаем с первого подхода - спрашиваем вес
        await message.answer(
            f"⚖️ *Подход 1 из {sets}*\n\n"
            f"Введите вес (кг) или '-' если без веса:"
        )
        await state.set_state(WorkoutSessionStates.entering_set_data)
        
    except ValueError:
        await message.answer("❌ Введите число")
@router.callback_query(F.data == "weight_one")
async def weight_one_method(callback: CallbackQuery, state: FSMContext):
    """Ввод одного веса для всех подходов"""
    await callback.message.edit_text(
        "⚖️ Введите вес (кг) для всех подходов или '-' если без веса:"
    )
    await state.set_state(WorkoutSessionStates.entering_weight)
    await callback.answer()

@router.callback_query(F.data == "reps_same")
async def reps_same_method(callback: CallbackQuery, state: FSMContext):
    """Одинаковые повторения для всех подходов"""
    await callback.message.edit_text(
        "🔄 Введите количество повторений (одинаково для всех подходов):"
    )
    await state.set_state(WorkoutSessionStates.entering_reps)
    await callback.answer()

@router.callback_query(F.data == "reps_each")
async def reps_each_method(callback: CallbackQuery, state: FSMContext):
    """Разные повторения для каждого подхода"""
    data = await state.get_data()
    sets = data['sets']
    
    await state.update_data(current_set=1, reps_list=[])
    await callback.message.edit_text(
        f"🔄 *Подход 1 из {sets}*\n\n"
        f"Введите количество повторений для первого подхода:"
    )
    await state.set_state(WorkoutSessionStates.entering_set_reps)
    await callback.answer()

@router.callback_query(F.data == "weight_each")
async def weight_each_method(callback: CallbackQuery, state: FSMContext):
    """Ввод веса для каждого подхода"""
    data = await state.get_data()
    sets = data['sets']
    
    await state.update_data(current_set=1, weights=[])
    await callback.message.edit_text(
        f"⚖️ *Подход 1 из {sets}*\n\n"
        f"Введите вес для первого подхода (или '-' без веса):"
    )
    await state.set_state(WorkoutSessionStates.entering_set_weights)
    await callback.answer()

@router.message(WorkoutSessionStates.entering_set_data)
async def process_set_data(message: Message, state: FSMContext):
    """Обработка ввода данных для текущего подхода (сначала вес, потом повторения)"""
    if not message.text:
        await message.answer("❌ Пришлите число текстом или '-' без веса.")
        return
    data = await state.get_data()
    current_set = data['current_set']
    total_sets = data['sets']
    set_data = data['set_data']
    
    current_entry = set_data[current_set-1]
    
    if not current_entry.get('weight_done'):
        if message.text.strip() == '-':
            current_entry['weight'] = 0
        else:
            try:
                current_entry['weight'] = float(message.text.replace(',', '.'))
            except ValueError:
                await message.answer("❌ Введите число или '-'")
                return
        current_entry['weight_done'] = True
        set_data[current_set-1] = current_entry
        await state.update_data(set_data=set_data)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="⏸️ ПРИОСТАНОВИТЬ", callback_data="save_workout")
        )
        
        await message.answer(
            f"🔄 *Подход {current_set} из {total_sets}*\n\n"
            f"Введите количество повторений:",
            reply_markup=builder.as_markup()
        )
        return

    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
        current_entry['reps'] = reps
        set_data[current_set-1] = current_entry
        await state.update_data(set_data=set_data)

        if current_set < total_sets:
            current_set += 1
            await state.update_data(current_set=current_set)
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="⏸️ ПРИОСТАНОВИТЬ", callback_data="save_workout")
            )
            await message.answer(
                f"⚖️ *Подход {current_set} из {total_sets}*\n\n"
                f"Введите вес (кг) или '-' если без веса:",
                reply_markup=builder.as_markup()
            )
        else:
            await save_exercise_from_set_data(state, message)
            await show_workout_menu(message, state)

    except ValueError:
        await message.answer("❌ Введите число")

@router.message(WorkoutSessionStates.entering_set_reps)
async def process_set_reps(message: Message, state: FSMContext):
    """Обработка повторений для текущего подхода"""
    data = await state.get_data()
    current_set = data['current_set']
    total_sets = data['sets']
    reps_list = data.get('reps_list', [])
    
    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
        reps_list.append(reps)
        await state.update_data(reps_list=reps_list)
        
        # Если есть еще подходы
        if current_set < total_sets:
            current_set += 1
            await state.update_data(current_set=current_set)
            await message.answer(
                f"🔄 *Подход {current_set} из {total_sets}*\n\n"
                f"Введите количество повторений для {current_set}-го подхода:"
            )
        else:
            # Все повторения введены, теперь спрашиваем про вес
            await ask_weight_method(message, state)
            
    except ValueError:
        await message.answer("❌ Введите число")
async def ask_weight_method(message: Message, state: FSMContext):
    """Спрашивает про способ ввода веса"""
    data = await state.get_data()
    sets = data['sets']
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ ОДИН ВЕС", callback_data="weight_one"),
        InlineKeyboardButton(text="📊 ПО ПОДХОДАМ", callback_data="weight_each")
    )
    
    await message.answer(
        f"⚖️ *Ввод веса*\n\n"
        f"У вас {sets} подходов. Как вводить вес?\n\n"
        f"• Один вес - одинаковый для всех подходов\n"
        f"• По подходам - разный вес для каждого",
        reply_markup=builder.as_markup()
    )
    await state.set_state(WorkoutSessionStates.choosing_weight_method)

@router.message(WorkoutSessionStates.entering_set_weights)
async def process_set_weight(message: Message, state: FSMContext):
    """Обработка веса для текущего подхода"""
    data = await state.get_data()
    current_set = data['current_set']
    total_sets = data['sets']
    weights = data.get('weights', [])
    
    # Сохраняем вес текущего подхода
    if message.text == '-':
        weights.append(None)
    else:
        try:
            weight = float(message.text)
            weights.append(weight)
        except ValueError:
            await message.answer("❌ Введите число или '-'")
            return
    
    await state.update_data(weights=weights)
    
    # Если есть еще подходы
    if current_set < total_sets:
        current_set += 1
        await state.update_data(current_set=current_set)
        await message.answer(
            f"⚖️ *Подход {current_set} из {total_sets}*\n\n"
            f"Введите вес для {current_set}-го подхода:"
        )
    else:
        # Все веса введены, теперь повторения
        await state.update_data(weight_method='each')
        await message.answer(
            "🔄 *Повторения*\n\n"
            "Введите количество повторений для всех подходов (одинаково):"
        )
        await state.set_state(WorkoutSessionStates.entering_reps)

@router.message(WorkoutSessionStates.entering_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторений (одинаковых для всех подходов)"""
    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
        await state.update_data(reps=reps)
        
        # Проверяем метод ввода веса
        data = await state.get_data()
        if data.get('weight_method') == 'each':
            # Уже есть все веса
            await save_exercise_with_weights(state, message)
        else:
            # Будем вводить один вес
            await message.answer("⚖️ Введите вес (кг) или '-'")
            await state.set_state(WorkoutSessionStates.entering_weight)
            
    except ValueError:
        await message.answer("❌ Введите число")


async def save_exercise_with_weights(state: FSMContext, message: Message): #noqa
    """Сохранить упражнение с разными весами по подходам"""
    data = await state.get_data()
    
    exercise = {
        'name': data['exercise_name'],
        'type': data['current_exercise_type'],
        'sets': data['sets'],
        'reps': data['reps'],
        'weights': data.get('weights', [])
    }
    
    exercises = data.get('exercises', [])
    exercises.append(exercise)
    await state.update_data(exercises=exercises)
    
    # Вычисляем средний вес для отображения
    weights = [w for w in data.get('weights', []) if w]
    await persist_session_exercises_from_state(data["session_id"], exercises)
    
    # Показываем детали
    weight_details = ""
    if weights:
        weight_details = "\n*Вес по подходам:*\n"
        for i, w in enumerate(weights, 1):
            w_text = f"{w} кг" if w else "б/в"
            weight_details += f"  {i}. {w_text}\n"
    
    await message.answer(
        f"✅ *Упражнение добавлено!*\n\n"
        f"🏋️ {exercise['name']}\n"
        f"📊 {exercise['sets']}×{exercise['reps']}\n"
        f"{weight_details}"
    )
    
    await show_workout_menu(message, state)

@router.message(WorkoutSessionStates.entering_weight)
async def process_weight(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Введите вес или '-'")
        return
    try:
        weight = None if message.text.strip() == '-' else float(message.text.replace(',', '.'))
    except ValueError:
        await message.answer("❌ Введите число или '-'")
        return
    await state.update_data(weight=weight)
    await save_exercise(state, message)
    await show_workout_menu(message, state)

@router.message(WorkoutSessionStates.entering_duration)
async def process_duration(message: Message, state: FSMContext):
    try:
        duration = int(message.text)
        await state.update_data(duration=duration)
        data = await state.get_data()
        if data['current_exercise_type'] == 'cardio':
            await message.answer("Введите дистанцию (км):")
            await state.set_state(WorkoutSessionStates.entering_distance)
        else:
            await save_exercise(state, message)
            await show_workout_menu(message, state)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(WorkoutSessionStates.entering_distance)
async def process_distance(message: Message, state: FSMContext):
    try:
        distance = float(message.text.replace(',', '.'))
        await state.update_data(distance=distance)
        await save_exercise(state, message)
        await show_workout_menu(message, state)
    except ValueError:
        await message.answer("❌ Введите число")

async def save_exercise(state: FSMContext, message: Message):
    """Сохранить упражнение с учетом разных повторений"""
    data = await state.get_data()
    
    exercise = {
        'name': data['exercise_name'],
        'type': data['current_exercise_type'],
        'sets': data['sets']
    }
    
    # Сохраняем повторения (список или одно значение)
    if 'reps_list' in data:
        exercise['reps_list'] = data['reps_list']
        # Для отображения покажем диапазон
        min_reps = min(data['reps_list'])
        max_reps = max(data['reps_list'])
        reps_display = f"{min_reps}-{max_reps}" if min_reps != max_reps else str(min_reps)
        exercise['reps_display'] = reps_display
        exercise['reps'] = data['reps_list'][0]  # для БД возьмем первое значение (можно сохранять все)
    else:
        exercise['reps'] = data['reps']
        exercise['reps_display'] = str(data['reps'])
    
    # Сохраняем вес (список или одно значение)
    if 'weights' in data:
        exercise['weights'] = data['weights']
        weights = [w for w in data['weights'] if w]
        if weights:
            min_w = min(weights)
            max_w = max(weights)
            weight_display = f"{min_w}-{max_w} кг" if min_w != max_w else f"{min_w} кг"
        else:
            weight_display = "б/в"
        exercise['weight_display'] = weight_display
    else:
        exercise['weight'] = data.get('weight')
        weight_display = f"{data.get('weight')} кг" if data.get('weight') else "б/в"
        exercise['weight_display'] = weight_display
    
    exercises = data.get('exercises', [])
    exercises.append(exercise)
    await state.update_data(exercises=exercises)
    
    try:
        if exercise['type'] == 'strength':
            await persist_session_exercises_from_state(data["session_id"], exercises)
        else:
            # кардио и растяжка без изменений
            pass
            
        logger.info(f"✅ Упражнение {exercise['name']} сохранено")
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения упражнения: {e}")
        

@router.callback_query(F.data == "finish_workout")
async def finish_workout(callback: CallbackQuery, state: FSMContext):
    """Завершение тренировки"""
    data = await state.get_data()
    session_id = data.get("session_id")
    exercises = data.get("exercises", [])
    user_id = callback.from_user.id

    if not exercises:
        await delete_workout_session(session_id)
        await clear_workout_session(user_id)
        await state.clear()
        await callback.message.edit_text(
            "❌ Тренировка не сохранена: нет упражнений.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
            ).as_markup(),
        )
        await callback.answer()
        return

    await persist_session_exercises_from_state(session_id, exercises)
    
    await db.execute(
        "UPDATE workout_sessions SET end_time = ? WHERE id = ?",
        (now_hm(), session_id)
    )
    
    await clear_workout_session(user_id)
    
    text = (
        f"✅ *Тренировка завершена!*\n\n"
        f"📊 Выполнено упражнений: {len(exercises)}\n"
        f"💪 Отличная работа!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.clear()
    await callback.answer()
    await maybe_send_workout_milestone_prompt(callback.message, user_id)
    await maybe_grant_referrer_retention_bonus(user_id, callback.bot)

@router.callback_query(F.data == "cancel_workout")
async def cancel_workout(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await delete_workout_session(data.get("session_id"))
    await clear_workout_session(callback.from_user.id)
    await callback.message.edit_text("❌ Тренировка отменена")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "back_to_workout")
async def back_to_workout(callback: CallbackQuery, state: FSMContext):
    await show_workout_menu(callback.message, state)
    await callback.answer()


@router.callback_query(F.data == "edit_workout_exercises")
async def edit_workout_exercises(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    exercises = data.get("exercises", [])
    if not exercises:
        await callback.answer("❌ Нет упражнений для редактирования", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for idx, ex in enumerate(exercises):
        builder.row(
            InlineKeyboardButton(
                text=f"✏️ {idx + 1}. {ex.get('name', 'Упражнение')}",
                callback_data=f"edit_workout_ex:{idx}"
            )
        )
    builder.row(InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_workout"))
    await callback.message.edit_text("Выберите упражнение для редактирования:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("edit_workout_ex:"))
async def edit_workout_exercise(callback: CallbackQuery, state: FSMContext):
    ex_index = int(callback.data.split(":")[1])
    data = await state.get_data()
    exercises = data.get("exercises", [])
    if ex_index >= len(exercises):
        await callback.answer("❌ Упражнение не найдено", show_alert=True)
        return

    ex = exercises[ex_index]
    await state.update_data(edit_ex_index=ex_index)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Подходы", callback_data="edit_current_field:sets"),
        InlineKeyboardButton(text="🔄 Повторы", callback_data="edit_current_field:reps"),
    )
    builder.row(
        InlineKeyboardButton(text="⚖️ Вес", callback_data="edit_current_field:weight"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data="edit_current_field:delete"),
    )
    builder.row(InlineKeyboardButton(text="↩️ НАЗАД", callback_data="edit_workout_exercises"))
    await callback.message.edit_text(
        f"✏️ {ex.get('name')}\n"
        f"Текущее: {ex.get('sets', '-') }x{ex.get('reps_display', ex.get('reps', '-'))}, "
        f"{ex.get('weight_display', ex.get('weight', 'б/в'))}",
        reply_markup=builder.as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("edit_current_field:"))
async def edit_current_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    data = await state.get_data()
    ex_index = data.get("edit_ex_index")
    exercises = data.get("exercises", [])
    if ex_index is None or ex_index >= len(exercises):
        await callback.answer("❌ Упражнение не найдено", show_alert=True)
        return

    if field == "delete":
        exercises.pop(ex_index)
        await state.update_data(exercises=exercises)
        await persist_session_exercises_from_state(data["session_id"], exercises)
        await callback.answer("✅ Удалено")
        await show_workout_menu(callback.message, state)
        return

    field_text = {"sets": "подходов", "reps": "повторов", "weight": "вес (кг или '-')"}
    await state.update_data(edit_field=field)
    await callback.message.edit_text(f"Введите новое значение для {field_text[field]}:")
    await state.set_state(WorkoutSessionStates.editing_exercise_value)
    await callback.answer()


@router.message(WorkoutSessionStates.editing_exercise_value)
async def save_current_field(message: Message, state: FSMContext):
    data = await state.get_data()
    ex_index = data.get("edit_ex_index")
    field = data.get("edit_field")
    exercises = data.get("exercises", [])
    if ex_index is None or ex_index >= len(exercises) or not field:
        await message.answer("❌ Не удалось сохранить изменение")
        return

    ex = exercises[ex_index]
    try:
        if field == "sets":
            sets = int(message.text)
            if sets <= 0:
                raise ValueError
            _replace_exact_sets(ex, count=sets)
        elif field == "reps":
            reps = int(message.text)
            if reps <= 0:
                raise ValueError
            _replace_exact_sets(ex, reps=reps)
        elif field == "weight":
            if message.text.strip() == "-":
                _replace_exact_sets(ex, weight=0)
            else:
                weight = float(message.text.replace(",", "."))
                if weight < 0:
                    raise ValueError
                _replace_exact_sets(ex, weight=weight)
    except ValueError:
        await message.answer("❌ Неверный формат")
        return

    exercises[ex_index] = ex
    await state.update_data(exercises=exercises)
    await persist_session_exercises_from_state(data["session_id"], exercises)
    await show_workout_menu(message, state)