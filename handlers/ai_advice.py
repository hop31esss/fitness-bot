from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database.base import db
from services.openai_service import openai_service
from config import ADMIN_ID

router = Router()

class AIStates(StatesGroup):
    waiting_question = State()

# ================ ПРОВЕРКА ПРЕМИУМ ================

async def check_premium_access(user_id: int) -> bool:
    """Проверка доступа к премиум-функциям"""
    if user_id == ADMIN_ID:
        return True
    
    user = await db.fetch_one(
        "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    if user and user['is_subscribed'] and user['subscription_until']:
        until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
        if datetime.now() <= until:
            return True
    
    return False

# ================ МЕНЮ AI-СОВЕТОВ ================

@router.callback_query(F.data == "ai_advice")
async def ai_advice_menu(callback: CallbackQuery):
    """Меню AI-советов"""
    user_id = callback.from_user.id
    
    # Проверка премиум-доступа
    if not await check_premium_access(user_id):
        await callback.answer("❌ Только для премиум!", show_alert=True)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="👑 Премиум", callback_data="show_premium_info")
        )
        
        await callback.message.answer(
            "🤖 *AI-советы*\n\n"
            "Эта функция доступна только с премиум-подпиской!\n\n"
            "💰 299₽/месяц",
            reply_markup=builder.as_markup()
        )
        return
    
    text = (
        "🤖 *AI-тренер*\n\n"
        "Нейросеть поможет вам с тренировками:\n\n"
        "1️⃣ **Совет на сегодня** - персональная рекомендация\n"
        "2️⃣ **План тренировки** - сгенерирую программу\n"
        "3️⃣ **Анализ прогресса** - разберу ваши результаты\n"
        "4️⃣ **Задать вопрос** - спросите что угодно о фитнесе"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1️⃣ Совет на сегодня", callback_data="ai_daily_tip"),
        InlineKeyboardButton(text="2️⃣ План тренировки", callback_data="ai_workout_plan")
    )
    builder.row(
        InlineKeyboardButton(text="3️⃣ Анализ прогресса", callback_data="ai_analyze"),
        InlineKeyboardButton(text="4️⃣ Задать вопрос", callback_data="ai_ask")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ СОВЕТ НА СЕГОДНЯ ================

@router.callback_query(F.data == "ai_daily_tip")
async def ai_daily_tip(callback: CallbackQuery):
    """Получить совет на сегодня"""
    user_id = callback.from_user.id
    
    if not await check_premium_access(user_id):
        return
    
    await callback.message.edit_text("🤔 *Думаю...* Анализирую ваши тренировки...")
    
    # Получаем данные пользователя
    user = await db.fetch_one(
        "SELECT first_name, username FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    stats = await db.fetch_one(
        "SELECT total_workouts, current_streak FROM user_stats WHERE user_id = ?",
        (user_id,)
    )
    
    # Получаем последние тренировки
    last_workouts = await db.fetch_all("""
        SELECT we.exercise_name, we.sets, we.reps, we.weight
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ?
        ORDER BY ws.date DESC
        LIMIT 5
    """, (user_id,))
    
    user_data = {
        'first_name': user['first_name'] if user else 'Пользователь',
        'total_workouts': stats['total_workouts'] if stats else 0,
        'current_streak': stats['current_streak'] if stats else 0
    }
    
    # Получаем совет
    advice = await openai_service.get_daily_tip(user_data, last_workouts)
    
    if advice:
        text = (
            f"🤖 *Совет на сегодня*\n\n"
            f"{advice}\n\n"
            f"💪 Хорошей тренировки!"
        )
    else:
        text = (
            "❌ *Не удалось получить совет*\n\n"
            "Попробуйте позже или проверьте API ключ в настройках."
        )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Ещё совет", callback_data="ai_daily_tip"),
        InlineKeyboardButton(text="📋 В меню", callback_data="ai_advice")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ПЛАН ТРЕНИРОВКИ ================

@router.callback_query(F.data == "ai_workout_plan")
async def ai_workout_plan(callback: CallbackQuery):
    """Сгенерировать план тренировки"""
    user_id = callback.from_user.id
    
    if not await check_premium_access(user_id):
        return
    
    await callback.message.edit_text("🤔 *Составляю план тренировки...*")
    
    # Данные пользователя
    user_data = {
        'experience': 'intermediate',
        'goal': 'общая физическая подготовка',
        'time': '60 минут',
        'equipment': 'тренажерный зал'
    }
    
    plan = await openai_service.get_workout_plan(user_data)
    
    if plan:
        text = f"🤖 *План тренировки*\n\n{plan}\n\n💪 Удачи!"
    else:
        text = "❌ Не удалось сгенерировать план"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Другой план", callback_data="ai_workout_plan"),
        InlineKeyboardButton(text="📋 В меню", callback_data="ai_advice")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ АНАЛИЗ ПРОГРЕССА ================

@router.callback_query(F.data == "ai_analyze")
async def ai_analyze(callback: CallbackQuery):
    """Анализ прогресса"""
    user_id = callback.from_user.id
    
    if not await check_premium_access(user_id):
        return
    
    await callback.message.edit_text("🤔 *Анализирую ваш прогресс...*")
    
    # Получаем историю тренировок
    history = await db.fetch_all("""
        SELECT 
            ws.date,
            we.exercise_name,
            we.sets,
            we.reps,
            we.weight
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ?
        ORDER BY ws.date DESC
        LIMIT 30
    """, (user_id,))
    
    user = await db.fetch_one(
        "SELECT first_name FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    user_data = {
        'first_name': user['first_name'] if user else 'Пользователь'
    }
    
    analysis = await openai_service.analyze_progress(user_data, history)
    
    if analysis:
        text = f"🤖 *Анализ прогресса*\n\n{analysis}"
    else:
        text = "❌ Не удалось проанализировать прогресс"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="ai_analyze"),
        InlineKeyboardButton(text="📋 В меню", callback_data="ai_advice")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ЗАДАТЬ ВОПРОС ================

@router.callback_query(F.data == "ai_ask")
async def ai_ask(callback: CallbackQuery, state: FSMContext):
    """Задать вопрос AI"""
    user_id = callback.from_user.id
    
    if not await check_premium_access(user_id):
        return
    
    await callback.message.edit_text(
        "🤖 *Задайте вопрос*\n\n"
        "Напишите ваш вопрос о тренировках, питании или восстановлении.\n\n"
        "Например:\n"
        "• Как улучшить жим лежа?\n"
        "• Что есть после тренировки?\n"
        "• Сколько нужно отдыхать между подходами?\n\n"
        "Или отправьте /cancel для отмены."
    )
    
    await state.set_state(AIStates.waiting_question)
    await callback.answer()

@router.message(AIStates.waiting_question)
async def process_ai_question(message: Message, state: FSMContext):
    """Обработка вопроса к AI"""
    user_id = message.from_user.id
    
    if message.text == "/cancel":
        await message.answer("❌ Вопрос отменен.")
        await state.clear()
        return
    
    await message.answer("🤔 *Думаю...* Ищу ответ на ваш вопрос...")
    
    user = await db.fetch_one(
        "SELECT first_name FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    user_data = {
        'first_name': user['first_name'] if user else 'Пользователь',
        'experience': 'intermediate'
    }
    
    answer = await openai_service.answer_question(message.text, user_data)
    
    if answer:
        text = f"🤖 *Ответ:*\n\n{answer}"
    else:
        text = "❌ Не удалось получить ответ"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❓ Ещё вопрос", callback_data="ai_ask"),
        InlineKeyboardButton(text="📋 В меню", callback_data="ai_advice")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())
    await state.clear()