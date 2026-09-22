import json
import sqlite3
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db
from handlers.premium import build_teaser_paywall, premium_cta_markup
from services.openai_service import openai_service
from services.premium_access import has_premium_access
from services.program_import import (
    format_template_exercises,
    parse_program_text,
    suggested_program_name,
)
from utils.clock import now_hm, today_iso


# === ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ ТАБЛИЦЫ (как в workout_journal) ===
def ensure_templates_table():
    """Создаёт таблицу workout_templates, если её нет"""
    try:
        conn = sqlite3.connect('fitness_bot.db')
        cursor = conn.cursor()
        
        # Создаём таблицу
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS workout_templates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                exercises TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        print("Table workout_templates created/checked")
    except Exception as e:
        print(f"Error creating table: {e}")

# Вызываем сразу
ensure_templates_table()

router = Router()

class TemplateEditStates(StatesGroup):
    waiting_new_exercise_name = State()
    waiting_new_sets = State()
    waiting_new_reps = State()
    waiting_new_weight = State()

class TemplateStates(StatesGroup):
    waiting_name = State()
    waiting_edit_name = State()
    waiting_edit_exercises = State()
    waiting_manual_exercise_name = State()
    waiting_manual_sets = State()
    waiting_manual_reps = State()
    waiting_manual_weight = State()

class TemplateCopyStates(StatesGroup):
    waiting_new_name = State()

class TemplateShareStates(StatesGroup):
    waiting_friend_id = State()

class TemplateImportStates(StatesGroup):
    waiting_paste = State()
    waiting_import_name = State()
    waiting_ai_prompt = State()
    waiting_ai_name = State()


def _normalize_db_exercise(ex: dict) -> dict:
    """Приводит запись workout_exercises к формату шаблона."""
    return {
        "name": ex.get("exercise_name"),
        "type": ex.get("exercise_type", "strength"),
        "sets": int(ex.get("sets") or 0),
        "reps": int(ex.get("reps") or 0),
        "weight": ex.get("weight"),
    }


def _normalize_state_exercise(ex: dict) -> dict:
    """Приводит exercise из FSM к формату шаблона."""
    if ex.get("type") != "strength":
        return {"name": ex.get("name", "Упражнение"), "type": ex.get("type", "strength")}
    reps = ex.get("reps")
    if reps is None and ex.get("reps_list"):
        reps = ex["reps_list"][0]
    return {
        "name": ex.get("name", "Упражнение"),
        "type": "strength",
        "sets": int(ex.get("sets") or 0),
        "reps": int(reps or 0),
        "weight": ex.get("weight"),
    }


async def _load_session_exercises(session_id: int) -> list:
    rows = await db.fetch_all(
        """
        SELECT exercise_name, exercise_type, sets, reps, weight
        FROM workout_exercises
        WHERE session_id = ?
        ORDER BY order_num ASC, id ASC
        """,
        (session_id,),
    )
    return [_normalize_db_exercise(row) for row in rows]


async def _save_user_template(user_id: int, name: str, exercises: list) -> None:
    await db.execute(
        "INSERT INTO workout_templates (user_id, name, exercises) VALUES (?, ?, ?)",
        (user_id, name.strip()[:60], json.dumps(exercises, ensure_ascii=False)),
    )


def _saved_template_markup():
    return InlineKeyboardBuilder().row(
        InlineKeyboardButton(text="🚀 НАЧАТЬ", callback_data="template_start_list"),
        InlineKeyboardButton(text="📚 В БИБЛИОТЕКУ", callback_data="templates"),
    ).as_markup()

# ========== ГЛАВНОЕ МЕНЮ ШАБЛОНОВ ==========

@router.callback_query(F.data == "templates")
async def templates_menu(callback: CallbackQuery):
    ensure_templates_table()

    user_id = callback.from_user.id
    
    templates = await db.fetch_all(
        "SELECT id, name FROM workout_templates WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    
    text = "📚 *Библиотека тренировок*\n\n"
    if templates:
        text += "Нажмите на программу, чтобы открыть, начать или изменить её.\n"
    else:
        text += "У вас пока нет сохранённых программ.\nВставьте свою из заметок, создайте вручную или попросите ИИ."
    
    builder = InlineKeyboardBuilder()
    for t in templates:
        builder.row(
            InlineKeyboardButton(text=f"📌 {t['name']}", callback_data=f"template_open:{t['id']}")
        )
    builder.row(
        InlineKeyboardButton(text="📥 ВСТАВИТЬ ИЗ ТЕКСТА", callback_data="template_import_paste")
    )
    builder.row(
        InlineKeyboardButton(text="🤖 СОЗДАТЬ С ИИ", callback_data="template_ai_create")
    )
    builder.row(
        InlineKeyboardButton(text="➕ СОЗДАТЬ ИЗ ТЕКУЩЕЙ", callback_data="template_create_from_current")
    )
    builder.row(
        InlineKeyboardButton(text="🧩 СОЗДАТЬ ВРУЧНУЮ", callback_data="template_create_manual"),
        InlineKeyboardButton(text="🕘 ИЗ ИСТОРИИ", callback_data="template_create_from_history")
    )
    if templates:
        builder.row(
            InlineKeyboardButton(text="🚀 НАЧАТЬ ПО ПРОГРАММЕ", callback_data="template_start_list"),
            InlineKeyboardButton(text="✏️ РЕДАКТИРОВАТЬ", callback_data="template_edit_list")
        )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="menu_training")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ========== СОЗДАНИЕ ШАБЛОНА ИЗ ТЕКУЩЕЙ ТРЕНИРОВКИ ==========

@router.callback_query(F.data == "template_create_from_current")
async def create_template_from_current(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    exercises = []
    session_id = data.get("session_id")

    if session_id:
        exercises = await _load_session_exercises(session_id)
    if not exercises:
        exercises = [_normalize_state_exercise(ex) for ex in data.get("exercises", []) if ex.get("name")]

    if not exercises:
        await callback.message.edit_text(
            "❌ В текущей тренировке пока нет сохранённых упражнений.\n\n"
            "Сначала добавьте хотя бы одно упражнение или создайте программу вручную.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🧩 СОЗДАТЬ ВРУЧНУЮ", callback_data="template_create_manual"),
                InlineKeyboardButton(text="↩️ НАЗАД", callback_data="templates")
            ).as_markup()
        )
        await callback.answer()
        return

    await state.update_data(template_source_exercises=exercises)
    await callback.message.edit_text(
        "📝 *Назовите программу*\n\n"
        "Например: «Тяжёлая неделя», «Грудь‑трицепс», «Ноги‑плечи»"
    )
    await state.set_state(TemplateStates.waiting_name)
    await callback.answer()

@router.message(TemplateStates.waiting_name)
async def save_template_name(message: Message, state: FSMContext):
    name = message.text.strip()
    data = await state.get_data()
    manual_mode = 'manual_exercises' in data and not data.get('template_source_exercises')
    if manual_mode:
        await state.update_data(manual_template_name=name, pending_template_name=name)
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➕ ДОБАВИТЬ УПРАЖНЕНИЕ", callback_data="template_manual_add_exercise")
        )
        builder.row(
            InlineKeyboardButton(text="✅ СОХРАНИТЬ ПРОГРАММУ", callback_data="template_manual_save")
        )
        await message.answer(
            f"🧩 Программа «{name}» создана. Теперь добавьте упражнения.",
            reply_markup=builder.as_markup()
        )
        return

    exercises = data.get('template_source_exercises') or data.get('manual_exercises') or data.get('exercises', [])
    user_id = message.from_user.id
    
    await db.execute(
        "INSERT INTO workout_templates (user_id, name, exercises) VALUES (?, ?, ?)",
        (user_id, name, json.dumps(exercises, ensure_ascii=False))
    )
    
    await message.answer(
        f"✅ Программа «{name}» сохранена!",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📚 В БИБЛИОТЕКУ", callback_data="templates")
        ).as_markup()
    )
    await state.clear()


@router.callback_query(F.data == "template_create_from_history")
async def template_create_from_history(callback: CallbackQuery):
    sessions = await db.fetch_all(
        """
        SELECT ws.id, ws.date, ws.start_time, COUNT(we.id) as exercises_count
        FROM workout_sessions ws
        JOIN workout_exercises we ON we.session_id = ws.id
        WHERE ws.user_id = ?
        GROUP BY ws.id
        HAVING COUNT(we.id) > 0
        ORDER BY ws.id DESC
        LIMIT 10
        """,
        (callback.from_user.id,),
    )
    if not sessions:
        await callback.answer("❌ История тренировок пуста", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for session in sessions:
        label = f"🗓️ {session['date']} {session.get('start_time') or ''} ({session['exercises_count']} упр.)"
        builder.row(
            InlineKeyboardButton(
                text=label.strip(),
                callback_data=f"template_history_pick:{session['id']}"
            )
        )
    builder.row(InlineKeyboardButton(text="↩️ НАЗАД", callback_data="templates"))
    await callback.message.edit_text("Выберите тренировку из истории:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("template_history_pick:"))
async def template_history_pick(callback: CallbackQuery, state: FSMContext):
    session_id = int(callback.data.split(":")[1])
    exercises = await _load_session_exercises(session_id)
    if not exercises:
        await callback.answer("❌ В этой тренировке нет упражнений", show_alert=True)
        return
    await state.update_data(template_source_exercises=exercises)
    await callback.message.edit_text("📝 Введите название новой программы из истории:")
    await state.set_state(TemplateStates.waiting_name)
    await callback.answer()


@router.callback_query(F.data == "template_create_manual")
async def template_create_manual(callback: CallbackQuery, state: FSMContext):
    await state.update_data(manual_exercises=[])
    await callback.message.edit_text("📝 Введите название программы:")
    await state.set_state(TemplateStates.waiting_name)
    await callback.answer()


@router.callback_query(F.data == "template_manual_add_exercise")
async def template_manual_add_exercise(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🏋️ Введите название упражнения:")
    await state.set_state(TemplateStates.waiting_manual_exercise_name)
    await callback.answer()


@router.message(TemplateStates.waiting_manual_exercise_name)
async def template_manual_exercise_name(message: Message, state: FSMContext):
    await state.update_data(manual_current_name=message.text.strip())
    await message.answer("Введите количество подходов:")
    await state.set_state(TemplateStates.waiting_manual_sets)


@router.message(TemplateStates.waiting_manual_sets)
async def template_manual_sets(message: Message, state: FSMContext):
    try:
        sets = int(message.text)
        if sets <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число подходов")
        return
    await state.update_data(manual_current_sets=sets)
    await message.answer("Введите количество повторений:")
    await state.set_state(TemplateStates.waiting_manual_reps)


@router.message(TemplateStates.waiting_manual_reps)
async def template_manual_reps(message: Message, state: FSMContext):
    try:
        reps = int(message.text)
        if reps <= 0:
            raise ValueError
    except ValueError:
        await message.answer("❌ Введите положительное число повторений")
        return
    await state.update_data(manual_current_reps=reps)
    await message.answer("Введите вес (кг) или '-' если без веса:")
    await state.set_state(TemplateStates.waiting_manual_weight)


@router.message(TemplateStates.waiting_manual_weight)
async def template_manual_weight(message: Message, state: FSMContext):
    raw = message.text.strip()
    if raw == "-":
        weight = None
    else:
        try:
            weight = float(raw.replace(",", "."))
        except ValueError:
            await message.answer("❌ Введите число или '-'")
            return

    data = await state.get_data()
    exercises = data.get("manual_exercises", [])
    exercises.append({
        "name": data.get("manual_current_name", "Упражнение"),
        "type": "strength",
        "sets": data.get("manual_current_sets", 0),
        "reps": data.get("manual_current_reps", 0),
        "weight": weight,
    })
    await state.update_data(manual_exercises=exercises)

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ЕЩЁ УПРАЖНЕНИЕ", callback_data="template_manual_add_exercise"),
        InlineKeyboardButton(text="✅ СОХРАНИТЬ ПРОГРАММУ", callback_data="template_manual_save")
    )
    await message.answer(
        f"✅ Добавлено. Упражнений в программе: {len(exercises)}",
        reply_markup=builder.as_markup()
    )


@router.callback_query(F.data == "template_manual_save")
async def template_manual_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data.get("manual_template_name") or data.get("pending_template_name")
    exercises = data.get("manual_exercises", [])
    if not name:
        await callback.answer("❌ Сначала укажите название программы", show_alert=True)
        return
    if not exercises:
        await callback.answer("❌ Добавьте хотя бы одно упражнение", show_alert=True)
        return

    await db.execute(
        "INSERT INTO workout_templates (user_id, name, exercises) VALUES (?, ?, ?)",
        (callback.from_user.id, name, json.dumps(exercises, ensure_ascii=False))
    )
    await callback.message.edit_text(
        f"✅ Программа «{name}» сохранена.",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📚 В БИБЛИОТЕКУ", callback_data="templates")
        ).as_markup()
    )
    await state.clear()
    await callback.answer()

# ========== ПРИМЕНЕНИЕ ШАБЛОНА ==========

@router.callback_query(F.data == "template_list")
async def template_list(callback: CallbackQuery):
    await templates_menu(callback)


@router.callback_query(F.data == "template_start_list")
async def template_start_list(callback: CallbackQuery):
    templates = await db.fetch_all(
        "SELECT id, name FROM workout_templates WHERE user_id = ? ORDER BY created_at DESC",
        (callback.from_user.id,),
    )
    if not templates:
        await callback.answer("❌ У вас пока нет программ", show_alert=True)
        return

    builder = InlineKeyboardBuilder()
    for t in templates:
        builder.row(
            InlineKeyboardButton(text=f"🚀 {t['name']}", callback_data=f"start_template:{t['id']}")
        )
    builder.row(InlineKeyboardButton(text="↩️ НАЗАД", callback_data="templates"))
    await callback.message.edit_text("Выберите программу для старта тренировки:", reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("start_template:"))
async def start_template_workout(callback: CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split(":")[1])
    template = await db.fetch_one(
        "SELECT id, name, exercises FROM workout_templates WHERE id = ? AND user_id = ?",
        (template_id, callback.from_user.id),
    )
    if not template:
        await callback.answer("❌ Программа не найдена", show_alert=True)
        return

    planned = json.loads(template["exercises"])
    if not planned:
        await callback.answer("❌ В программе нет упражнений", show_alert=True)
        return

    from handlers.workout_session import (
        clear_workout_session,
        delete_empty_sessions,
        delete_workout_session,
        planned_to_live_exercise,
        save_workout_session,
        show_workout_menu,
    )

    data = await state.get_data()
    await delete_workout_session(data.get("session_id"))
    await delete_empty_sessions(callback.from_user.id)
    await clear_workout_session(callback.from_user.id)

    today = today_iso()
    current_time = now_hm()
    await db.execute(
        "INSERT INTO workout_sessions (user_id, date, start_time, template_id) VALUES (?, ?, ?, ?)",
        (callback.from_user.id, today, current_time, template_id),
    )
    row = await db.fetch_one("SELECT last_insert_rowid() as id")
    session_id = row["id"]

    exercises = [planned_to_live_exercise(ex) for ex in planned if ex.get("name")]
    await state.clear()
    await state.update_data(
        session_id=session_id,
        template_id=template_id,
        exercises=exercises,
    )
    await save_workout_session(callback.from_user.id, state)
    await callback.message.answer(
        f"🚀 Тренировка по программе «{template['name']}» начата.\n"
        "Упражнения уже подставлены — поправьте подходы при необходимости и завершите, как обычную тренировку."
    )
    await show_workout_menu(callback.message, state)
    await callback.answer()

@router.callback_query(F.data.startswith("apply_template:"))
async def apply_template(callback: CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split(":")[1])
    
    template = await db.fetch_one(
        "SELECT name, exercises FROM workout_templates WHERE id = ?",
        (template_id,)
    )
    
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return

    from handlers.workout_session import planned_to_live_exercise, show_workout_menu

    exercises = json.loads(template["exercises"])
    data = await state.get_data()
    if not data.get("session_id"):
        callback.data = f"start_template:{template_id}"
        await start_template_workout(callback, state)
        return

    live = [planned_to_live_exercise(ex) for ex in exercises if ex.get("name")]
    current_exercises = data.get("exercises", [])
    current_exercises.extend(live)
    await state.update_data(exercises=current_exercises)

    await callback.answer(f"✅ Программа «{template['name']}» добавлена")
    await show_workout_menu(callback.message, state)

# ========== РЕДАКТИРОВАНИЕ ==========

@router.callback_query(F.data == "template_edit_list")
async def template_edit_list(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    templates = await db.fetch_all(
        "SELECT id, name FROM workout_templates WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    
    builder = InlineKeyboardBuilder()
    for t in templates:
        builder.row(
            InlineKeyboardButton(
                text=f"✏️ {t['name']}",
                callback_data=f"template_edit:{t['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="templates")
    )
    
    await callback.message.edit_text(
        "Выберите программу для редактирования:",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("template_edit:"))
async def template_edit_menu(callback: CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split(":")[1])
    
    template = await db.fetch_one(
        "SELECT name, exercises FROM workout_templates WHERE id = ?",
        (template_id,)
    )
    
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    await state.update_data(edit_template_id=template_id)
    
    exercises = json.loads(template['exercises'])
    exercises_text = ""
    for i, ex in enumerate(exercises[:5], 1):
        if ex['type'] == 'strength':
            weight = f"{ex['weight']} кг" if ex.get('weight') else "б/в"
            exercises_text += f"{i}. {ex['name']}: {ex['sets']}×{ex['reps']} ({weight})\n"
        else:
            exercises_text += f"{i}. {ex['name']}: {ex['duration']} мин, {ex['distance']} км\n"
    if len(exercises) > 5:
        exercises_text += f"... и ещё {len(exercises)-5}\n"
    
    text = (
        f"✏️ *Редактирование*\n\n"
        f"📌 *{template['name']}*\n"
        f"📊 Упражнений: {len(exercises)}\n\n"
        f"{exercises_text}\n"
        f"Что хотите изменить?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 НАЧАТЬ ТРЕНИРОВКУ", callback_data=f"start_template:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📝 ИЗМЕНИТЬ НАЗВАНИЕ", callback_data=f"template_edit_name:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ РЕДАКТИРОВАТЬ УПРАЖНЕНИЯ", callback_data=f"template_edit_exercises:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📋 ПРОСМОТРЕТЬ", callback_data=f"template_view:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📋 КОПИРОВАТЬ", callback_data=f"template_copy:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="📤 ОТПРАВИТЬ ДРУГУ", callback_data=f"template_share:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="❌ УДАЛИТЬ", callback_data=f"template_delete:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="template_edit_list")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ========== ИЗМЕНЕНИЕ НАЗВАНИЯ ==========

@router.callback_query(F.data.startswith("template_edit_name:"))
async def template_edit_name(callback: CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split(":")[1])
    await state.update_data(edit_template_id=template_id)
    
    await callback.message.edit_text(
        "📝 *Введите новое название программы:*"
    )
    await state.set_state(TemplateStates.waiting_edit_name)
    await callback.answer()

@router.message(TemplateStates.waiting_edit_name)
async def update_template_name(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    template_id = data['edit_template_id']
    
    await db.execute(
        "UPDATE workout_templates SET name = ? WHERE id = ?",
        (new_name, template_id)
    )
    
    await message.answer(
        f"✅ Название обновлено на «{new_name}»",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📚 В БИБЛИОТЕКУ", callback_data="templates")
        ).as_markup()
    )
    await state.clear()

# ========== УДАЛЕНИЕ ==========

@router.callback_query(F.data.startswith("template_delete:"))
async def template_delete_confirm(callback: CallbackQuery):
    template_id = int(callback.data.split(":")[1])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ ДА, УДАЛИТЬ", callback_data=f"template_delete_confirm:{template_id}"),
        InlineKeyboardButton(text="❌ НЕТ", callback_data="template_edit_list")
    )
    
    await callback.message.edit_text(
        "⚠️ *Вы уверены?*\n\nЭто действие нельзя отменить.",
        reply_markup=builder.as_markup()
    )
    await callback.answer()

@router.callback_query(F.data.startswith("template_delete_confirm:"))
async def template_delete_execute(callback: CallbackQuery):
    template_id = int(callback.data.split(":")[1])
    
    await db.execute(
        "DELETE FROM workout_templates WHERE id = ?",
        (template_id,)
    )
    
    await callback.message.edit_text(
        "✅ Программа удалена.",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📚 В БИБЛИОТЕКУ", callback_data="templates")
        ).as_markup()
    )
    await callback.answer()

# ========== ПРОСМОТР ==========

@router.callback_query(F.data.startswith("template_view:"))
async def template_view(callback: CallbackQuery):
    template_id = int(callback.data.split(":")[1])
    
    template = await db.fetch_one(
        "SELECT name, exercises FROM workout_templates WHERE id = ?",
        (template_id,)
    )
    
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    exercises = json.loads(template['exercises'])
    
    text = f"📋 *{template['name']}*\n\n"
    for i, ex in enumerate(exercises, 1):
        if ex['type'] == 'strength':
            weight = f"{ex['weight']} кг" if ex.get('weight') else "б/в"
            text += f"{i}. {ex['name']} — {ex['sets']}×{ex['reps']} ({weight})\n"
        else:
            text += f"{i}. {ex['name']} — {ex['duration']} мин, {ex['distance']} км\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 НАЧАТЬ ТРЕНИРОВКУ", callback_data=f"start_template:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="✏️ РЕДАКТИРОВАТЬ", callback_data=f"template_edit:{template_id}"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="templates")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ========== КОПИРОВАНИЕ ==========

@router.callback_query(F.data.startswith("template_copy:"))
async def template_copy(callback: CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split(":")[1])
    
    template = await db.fetch_one(
        "SELECT name, exercises FROM workout_templates WHERE id = ?",
        (template_id,)
    )
    
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    await state.update_data(original_template_id=template_id, exercises=template['exercises'])
    
    await callback.message.edit_text(
        f"📝 *Копирование шаблона*\n\n"
        f"Исходный: «{template['name']}»\n\n"
        f"Введите новое название для копии:"
    )
    await state.set_state(TemplateCopyStates.waiting_new_name)
    await callback.answer()

@router.message(TemplateCopyStates.waiting_new_name)
async def template_copy_save(message: Message, state: FSMContext):
    new_name = message.text.strip()
    data = await state.get_data()
    user_id = message.from_user.id
    
    await db.execute(
        "INSERT INTO workout_templates (user_id, name, exercises) VALUES (?, ?, ?)",
        (user_id, new_name, data['exercises'])
    )
    
    await message.answer(
        f"✅ Копия «{new_name}» создана!",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📚 В БИБЛИОТЕКУ", callback_data="templates")
        ).as_markup()
    )
    await state.clear()

# ========== ОТПРАВКА ДРУГУ ==========

@router.callback_query(F.data.startswith("template_share:"))
async def template_share_start(callback: CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split(":")[1])
    
    template = await db.fetch_one(
        "SELECT name FROM workout_templates WHERE id = ?",
        (template_id,)
    )
    
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    await state.update_data(share_template_id=template_id)
    
    await callback.message.edit_text(
        f"📤 *Отправка другу*\n\n"
        f"Шаблон: «{template['name']}»\n\n"
        f"Введите Telegram ID друга (число):"
    )
    await state.set_state(TemplateShareStates.waiting_friend_id)
    await callback.answer()

@router.message(TemplateShareStates.waiting_friend_id)
async def template_share_send(message: Message, state: FSMContext):
    try:
        friend_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный ID (только цифры)")
        return
    
    data = await state.get_data()
    template_id = data['share_template_id']
    user_id = message.from_user.id
    
    template = await db.fetch_one(
        "SELECT name, exercises FROM workout_templates WHERE id = ?",
        (template_id,)
    )
    
    if not template:
        await message.answer("❌ Шаблон не найден")
        await state.clear()
        return
    
    sender = await db.fetch_one(
        "SELECT first_name, username FROM users WHERE user_id = ?",
        (user_id,)
    )
    sender_name = sender['first_name'] or sender['username'] or f"ID{user_id}"
    
    exercises = json.loads(template['exercises'])
    text = f"📦 *Подарок от {sender_name}*\n\n📋 *{template['name']}*\n\n"
    for i, ex in enumerate(exercises, 1):
        if ex['type'] == 'strength':
            weight = f"{ex['weight']} кг" if ex.get('weight') else "б/в"
            text += f"{i}. {ex['name']} — {ex['sets']}×{ex['reps']} ({weight})\n"
        else:
            text += f"{i}. {ex['name']} — {ex['duration']} мин, {ex['distance']} км\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ ПРИНЯТЬ", callback_data=f"template_accept:{user_id}:{template_id}"),
        InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data="template_decline")
    )
    
    try:
        await message.bot.send_message(
            friend_id,
            text,
            reply_markup=builder.as_markup()
        )
        await message.answer("✅ Шаблон отправлен другу!")
    except Exception:
        await message.answer("❌ Не удалось отправить. Проверьте ID.")
    
    await state.clear()

@router.callback_query(F.data.startswith("template_accept:"))
async def template_accept(callback: CallbackQuery):
    parts = callback.data.split(":")
    template_id = int(parts[2])
    receiver_id = callback.from_user.id
    
    template = await db.fetch_one(
        "SELECT name, exercises FROM workout_templates WHERE id = ?",
        (template_id,)
    )
    
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    await db.execute(
        "INSERT INTO workout_templates (user_id, name, exercises) VALUES (?, ?, ?)",
        (receiver_id, template['name'], template['exercises'])
    )
    
    await callback.message.edit_text(
        "✅ Шаблон добавлен в вашу библиотеку!",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📚 В БИБЛИОТЕКУ", callback_data="templates")
        ).as_markup()
    )
    await callback.answer()

@router.callback_query(F.data == "template_decline")
async def template_decline(callback: CallbackQuery):
    await callback.message.edit_text("❌ Шаблон отклонён.")
    await callback.answer()

# ========== РЕДАКТИРОВАНИЕ УПРАЖНЕНИЙ ==========

@router.callback_query(F.data.startswith("template_edit_exercises:"))
async def template_edit_exercises_list(callback: CallbackQuery, state: FSMContext):
    template_id = int(callback.data.split(":")[1])
    
    template = await db.fetch_one(
        "SELECT name, exercises FROM workout_templates WHERE id = ?",
        (template_id,)
    )
    
    if not template:
        await callback.answer("❌ Шаблон не найден", show_alert=True)
        return
    
    exercises = json.loads(template['exercises'])
    await state.update_data(edit_template_id=template_id, exercises=exercises)
    
    text = f"✏️ *Редактирование упражнений*\n\n📌 {template['name']}\n\n"
    builder = InlineKeyboardBuilder()
    
    for i, ex in enumerate(exercises, 1):
        if ex['type'] == 'strength':
            weight = f"{ex['weight']} кг" if ex.get('weight') else "б/в"
            text += f"{i}. {ex['name']} — {ex['sets']}×{ex['reps']} ({weight})\n"
            builder.row(
                InlineKeyboardButton(
                    text=f"✏️ {i}",
                    callback_data=f"edit_ex_in_template:{template_id}:{i-1}"
                )
            )
        else:
            text += f"{i}. {ex['name']} — {ex['duration']} мин, {ex['distance']} км\n"
    
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data=f"template_edit:{template_id}")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("edit_ex_in_template:"))
async def edit_exercise_in_template(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split(":")
    template_id = int(parts[1])
    ex_index = int(parts[2])
    
    data = await state.get_data()
    exercises = data.get('exercises', [])
    
    if ex_index >= len(exercises):
        await callback.answer("❌ Упражнение не найдено", show_alert=True)
        return
    
    ex = exercises[ex_index]
    await state.update_data(edit_template_id=template_id, edit_ex_index=ex_index)
    
    text = (
        f"✏️ *Редактирование*\n\n"
        f"📌 {ex['name']}\n"
        f"📊 {ex['sets']}×{ex['reps']} | {ex.get('weight', 'б/в')} кг\n\n"
        f"Что изменить?"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 Название", callback_data="edit_ex_field:name"),
        InlineKeyboardButton(text="📊 Подходы", callback_data="edit_ex_field:sets")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Повторения", callback_data="edit_ex_field:reps"),
        InlineKeyboardButton(text="⚖️ Вес", callback_data="edit_ex_field:weight")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data=f"template_edit_exercises:{template_id}")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("edit_ex_field:"))
async def edit_exercise_field(callback: CallbackQuery, state: FSMContext):
    field = callback.data.split(":")[1]
    
    field_names = {
        "name": "новое название",
        "sets": "новое количество подходов",
        "reps": "новое количество повторений",
        "weight": "новый вес (кг) или «-»"
    }
    
    await state.update_data(edit_field=field)
    await callback.message.edit_text(
        f"✏️ Введите {field_names[field]}:"
    )
    await state.set_state(TemplateEditStates.waiting_new_exercise_name)
    await callback.answer()

@router.message(TemplateEditStates.waiting_new_exercise_name)
async def update_exercise_field(message: Message, state: FSMContext):
    data = await state.get_data()
    template_id = data['edit_template_id']
    ex_index = data['edit_ex_index']
    field = data['edit_field']
    exercises = data.get('exercises', [])
    
    ex = exercises[ex_index]
    
    try:
        if field == "name":
            ex['name'] = message.text.strip()
        elif field == "sets":
            ex['sets'] = int(message.text)
        elif field == "reps":
            ex['reps'] = int(message.text)
        elif field == "weight":
            ex['weight'] = None if message.text == '-' else float(message.text)
    except ValueError:
        await message.answer("❌ Неверный формат. Попробуйте ещё раз.")
        return
    
    await db.execute(
        "UPDATE workout_templates SET exercises = ? WHERE id = ?",
        (json.dumps(exercises, ensure_ascii=False), template_id)
    )
    
    await message.answer(
        "✅ Упражнение обновлено!",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(
                text="↩️ К СПИСКУ",
                callback_data=f"template_edit_exercises:{template_id}"
            )
        ).as_markup()
    )
    await state.clear()


@router.callback_query(F.data.startswith("template_open:"))
async def template_open(callback: CallbackQuery):
    template_id = int(callback.data.split(":")[1])
    template = await db.fetch_one(
        "SELECT id, name, exercises FROM workout_templates WHERE id = ? AND user_id = ?",
        (template_id, callback.from_user.id),
    )
    if not template:
        await callback.answer("❌ Программа не найдена", show_alert=True)
        return
    exercises = json.loads(template["exercises"])
    text = (
        f"📌 *{template['name']}*\n\n"
        f"{format_template_exercises(exercises) or 'Пока нет упражнений.'}\n\n"
        "Можно сразу начать тренировку по этой программе или поправить упражнения."
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🚀 НАЧАТЬ ТРЕНИРОВКУ", callback_data=f"start_template:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="➕ В ТЕКУЩУЮ", callback_data=f"apply_template:{template_id}"),
        InlineKeyboardButton(text="✏️ ИЗМЕНИТЬ", callback_data=f"template_edit:{template_id}")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ К СПИСКУ", callback_data="templates")
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "template_import_paste")
async def template_import_paste(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "📥 *Вставьте программу текстом*\n\n"
        "Скопируйте из заметок или с сайта и отправьте одним сообщением.\n\n"
        "Примеры строк:\n"
        "`Присед 4x8 100`\n"
        "`Румынская тяга 3×10`\n"
        "`Разгибание ног — 4 подхода по 12`\n\n"
        "Строки без подходов бот пропустит."
    )
    await state.set_state(TemplateImportStates.waiting_paste)
    await callback.answer()


@router.message(TemplateImportStates.waiting_paste)
async def template_import_parse(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пришлите программу текстом.")
        return
    exercises = parse_program_text(message.text)
    if not exercises:
        await message.answer(
            "❌ Не удалось разобрать упражнения.\n"
            "Каждая строка должна быть вида «Присед 4x8 100»."
        )
        return
    suggested = suggested_program_name(message.text) or "Моя программа"
    await state.update_data(import_exercises=exercises, pending_template_name=suggested)
    await message.answer(
        "📋 *Программа распознана*\n\n"
        f"{format_template_exercises(exercises)}\n\n"
        f"Название: «{suggested}».\n"
        "Отправьте другое название или нажмите сохранить.",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="💾 СОХРАНИТЬ", callback_data="template_import_save")
        ).as_markup(),
    )
    await state.set_state(TemplateImportStates.waiting_import_name)


@router.message(TemplateImportStates.waiting_import_name)
async def template_import_name(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Пришлите название текстом.")
        return
    data = await state.get_data()
    exercises = data.get("import_exercises") or []
    if not exercises:
        await message.answer("❌ Сначала вставьте программу.")
        return
    await _save_user_template(message.from_user.id, message.text, exercises)
    await state.clear()
    await message.answer(
        f"✅ Программа «{message.text.strip()[:60]}» сохранена.",
        reply_markup=_saved_template_markup(),
    )


@router.callback_query(F.data == "template_import_save")
async def template_import_save(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    exercises = data.get("import_exercises") or []
    name = data.get("pending_template_name") or "Моя программа"
    if not exercises:
        await callback.answer("❌ Сначала вставьте программу", show_alert=True)
        return
    await _save_user_template(callback.from_user.id, name, exercises)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Программа «{name}» сохранена.",
        reply_markup=_saved_template_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "template_ai_create")
async def template_ai_create(callback: CallbackQuery, state: FSMContext):
    if not await has_premium_access(callback.from_user.id):
        await callback.message.edit_text(
            build_teaser_paywall(
                "🤖 *Программа с ИИ*",
                ["Опишите цель и опыт — бот соберёт программу и сохранит её в библиотеку."],
                ["Персональная программа под зал или дом", "Сразу можно начать тренировку"],
            ),
            reply_markup=premium_cta_markup("templates"),
        )
        await callback.answer()
        return
    if not openai_service.enabled:
        await callback.answer("AI сейчас недоступен. Вставьте программу текстом.", show_alert=True)
        return
    await callback.message.edit_text(
        "🤖 *Создание программы с ИИ*\n\n"
        "Напишите, какая программа нужна. Например:\n"
        "«3 дня в зале, набор массы, средний уровень, есть штанга и тренажёры, 60 минут»."
    )
    await state.set_state(TemplateImportStates.waiting_ai_prompt)
    await callback.answer()


@router.message(TemplateImportStates.waiting_ai_prompt)
async def template_ai_generate(message: Message, state: FSMContext):
    if not message.text:
        await message.answer("❌ Опишите программу текстом.")
        return
    wait = await message.answer("🤔 Составляю программу...")
    user = await db.fetch_one(
        "SELECT first_name FROM users WHERE user_id = ?",
        (message.from_user.id,),
    )
    result = await openai_service.generate_training_program(
        message.text.strip(),
        {"first_name": (user or {}).get("first_name")},
    )
    if not result or not result.get("exercises"):
        await wait.edit_text(
            "❌ Не удалось составить программу. Попробуйте описать цель иначе "
            "или вставьте готовую программу текстом."
        )
        return
    name = result.get("name") or "Программа ИИ"
    exercises = result["exercises"]
    await state.update_data(import_exercises=exercises, pending_template_name=name)
    await wait.edit_text(
        f"🤖 *Черновик программы «{name}»*\n\n"
        f"{format_template_exercises(exercises)}\n\n"
        "Можно сохранить как есть или прислать другое название.",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="💾 СОХРАНИТЬ", callback_data="template_import_save")
        ).as_markup(),
    )
    await state.set_state(TemplateImportStates.waiting_import_name)