import json
import sqlite3
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database.base import db

import os

# === ПРИНУДИТЕЛЬНОЕ СОЗДАНИЕ ТАБЛИЦЫ С ОТЛАДКОЙ ===
def ensure_templates_table():
    try:
        # Проверяем, существует ли файл БД
        db_path = 'fitness_bot.db'
        if os.path.exists(db_path):
            print(f"✅ Файл БД найден: {db_path}, размер: {os.path.getsize(db_path)} байт")
        else:
            print(f"❌ Файл БД НЕ найден: {db_path}")
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем существующие таблицы
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f"📊 Существующие таблицы: {[t[0] for t in tables]}")
        
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
        
        # Проверяем, создалась ли
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='workout_templates'")
        if cursor.fetchone():
            print("✅ Таблица workout_templates успешно создана")
        else:
            print("❌ Таблица workout_templates НЕ создалась")
        
        conn.close()
    except Exception as e:
        print(f"❌ Ошибка создания таблицы: {e}")
        import traceback
        traceback.print_exc()

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

class TemplateCopyStates(StatesGroup):
    waiting_new_name = State()

class TemplateShareStates(StatesGroup):
    waiting_friend_id = State()

# ========== ГЛАВНОЕ МЕНЮ ШАБЛОНОВ ==========

@router.callback_query(F.data == "templates")
async def templates_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    templates = await db.fetch_all(
        "SELECT id, name FROM workout_templates WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    
    text = "📚 *Библиотека тренировок*\n\n"
    if templates:
        text += "Ваши сохранённые программы:\n\n"
        for t in templates:
            text += f"📌 {t['name']}\n"
    else:
        text += "У вас пока нет сохранённых программ.\n\nСоздайте первую из сегодняшней тренировки!"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ СОЗДАТЬ ИЗ ТЕКУЩЕЙ", callback_data="template_create_from_current")
    )
    if templates:
        builder.row(
            InlineKeyboardButton(text="📋 ВЫБРАТЬ", callback_data="template_list")
        )
        builder.row(
            InlineKeyboardButton(text="✏️ РЕДАКТИРОВАТЬ", callback_data="template_edit_list")
        )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ========== СОЗДАНИЕ ШАБЛОНА ИЗ ТЕКУЩЕЙ ТРЕНИРОВКИ ==========

@router.callback_query(F.data == "template_create_from_current")
async def create_template_from_current(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    exercises = data.get('exercises', [])
    
    if not exercises:
        await callback.answer("❌ Сначала начните тренировку", show_alert=True)
        return
    
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
    exercises = data.get('exercises', [])
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

# ========== ПРИМЕНЕНИЕ ШАБЛОНА ==========

@router.callback_query(F.data == "template_list")
async def template_list(callback: CallbackQuery):
    user_id = callback.from_user.id
    
    templates = await db.fetch_all(
        "SELECT id, name FROM workout_templates WHERE user_id = ? ORDER BY created_at DESC",
        (user_id,)
    )
    
    builder = InlineKeyboardBuilder()
    for t in templates:
        builder.row(
            InlineKeyboardButton(
                text=f"📌 {t['name']}",
                callback_data=f"apply_template:{t['id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="templates")
    )
    
    await callback.message.edit_text(
        "Выберите программу для добавления в текущую тренировку:",
        reply_markup=builder.as_markup()
    )
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
    
    exercises = json.loads(template['exercises'])
    
    data = await state.get_data()
    current_exercises = data.get('exercises', [])
    current_exercises.extend(exercises)
    await state.update_data(exercises=current_exercises)
    
    await callback.answer(f"✅ Программа «{template['name']}» добавлена")
    from handlers.workout_session import show_workout_menu
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
        InlineKeyboardButton(text="📋 ВЫБРАТЬ ДРУГОЙ", callback_data="template_list"),
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
    sender_id = int(parts[1])
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