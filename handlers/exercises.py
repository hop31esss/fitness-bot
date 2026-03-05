from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db

router = Router()

class ManageExerciseStates(StatesGroup):
    waiting_delete_confirmation = State()
    waiting_edit_choice = State()
    waiting_new_name = State()
    waiting_new_alias = State()

@router.callback_query(F.data == "exercises")
async def exercises_main_menu(callback: CallbackQuery):
    """Главное меню управления упражнениями"""
    user_id = callback.from_user.id
    
    # Получаем статистику упражнений
    exercises_count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM exercises WHERE user_id = ?",
        (user_id,)
    )
    count = exercises_count['count'] if exercises_count else 0
    
    text = (
        "💪 *Управление упражнениями*\n\n"
        f"📊 Всего упражнений: {count}\n\n"
        "Выберите действие:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 МОИ УПРАЖНЕНИЯ", callback_data="my_exercises"),
        InlineKeyboardButton(text="➕ ДОБАВИТЬ", callback_data="add_exercise")
    )
    builder.row(
        InlineKeyboardButton(text="🔤 АЛИАСЫ", callback_data="exercise_aliases"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "manage_exercises")
async def manage_exercises(callback: CallbackQuery):
    """Управление упражнениями - главное меню"""
    user_id = callback.from_user.id
    
    # Получаем упражнения
    exercises = await db.fetch_all(
        "SELECT id, name, alias FROM exercises WHERE user_id = ? ORDER BY name",
        (user_id,)
    )
    
    if not exercises:
        text = "📝 *Управление упражнениями*\n\nУ вас пока нет сохраненных упражнений."
    else:
        text = "📝 *Управление упражнениями*\n\n"
        text += "*Ваши упражнения:*\n"
        
        for exercise in exercises:
            alias_text = f" ({exercise['alias']})" if exercise['alias'] else ""
            text += f"• {exercise['name']}{alias_text}\n"
        
        text += f"\nВсего: {len(exercises)} упражнений"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить", callback_data="add_exercise"),
        InlineKeyboardButton(text="✏️ Редактировать", callback_data="edit_exercises_list")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_exercises_list"),
        InlineKeyboardButton(text="🔤 Алиасы", callback_data="exercise_aliases")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "edit_exercises_list")
async def edit_exercises_list(callback: CallbackQuery):
    """Список упражнений для редактирования"""
    user_id = callback.from_user.id
    
    exercises = await db.fetch_all(
        "SELECT id, name, alias FROM exercises WHERE user_id = ? ORDER BY name",
        (user_id,)
    )
    
    if not exercises:
        text = "Нет упражнений для редактирования."
    else:
        text = "✏️ *Выберите упражнение для редактирования:*\n\n"
        
        for exercise in exercises:
            alias_text = f" ({exercise['alias']})" if exercise['alias'] else ""
            text += f"• {exercise['name']}{alias_text}\n"
    
    # Клавиатура с упражнениями для редактирования
    builder = InlineKeyboardBuilder()
    for exercise in exercises:
        builder.row(
            InlineKeyboardButton(
                text=f"✏️ {exercise['name'][:15]}...",
                callback_data=f"edit_exercise:{exercise['id']}"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="manage_exercises")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("edit_exercise:"))
async def edit_exercise(callback: CallbackQuery, state: FSMContext):
    """Редактирование конкретного упражнения"""
    exercise_id = int(callback.data.split(":")[1])
    
    # Получаем упражнение
    exercise = await db.fetch_one(
        "SELECT id, name, alias FROM exercises WHERE id = ?",
        (exercise_id,)
    )
    
    if not exercise:
        await callback.answer("Упражнение не найдено")
        return
    
    await state.update_data(editing_exercise_id=exercise_id)
    
    text = f"✏️ *Редактирование упражнения*\n\n"
    text += f"Текущее название: {exercise['name']}\n"
    text += f"Текущий алиас: {exercise['alias'] or 'нет'}\n\n"
    text += "Что вы хотите изменить?"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📝 Изменить название", callback_data="edit_exercise_name"),
        InlineKeyboardButton(text="🔤 Изменить алиас", callback_data="edit_exercise_alias")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ Удалить это упражнение", callback_data=f"delete_exercise:{exercise_id}"),
        InlineKeyboardButton(text="↩️ Отмена", callback_data="manage_exercises")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()