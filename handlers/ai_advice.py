from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db
from handlers.premium import build_teaser_paywall, premium_cta_markup
from services.openai_service import openai_service
from services.premium_access import has_premium_access
from services.progress_analytics import fetch_premium_analytics
from utils.clock import today_iso

router = Router()

class AIStates(StatesGroup):
    waiting_question = State()

async def _ai_paywall(callback: CallbackQuery) -> bool:
    if await has_premium_access(callback.from_user.id):
        return False
    await callback.message.edit_text(
        build_teaser_paywall(
            "🤖 *AI-советы*",
            [
                "Раздел открыт всем. Глубокий разбор тренировок, план и персональные ответы — в Premium.",
            ],
            [
                "Совет на сегодня по вашим подходам",
                "План тренировки",
                "Анализ прогресса по цифрам",
                "Ответы на вопросы о тренировках",
            ],
        ),
        reply_markup=premium_cta_markup("ai_advice"),
    )
    await callback.answer()
    return True


@router.callback_query(F.data.in_({"ai_advice", "menu_ai"}))
async def ai_advice_menu(callback: CallbackQuery):
    """AI hub is visible to everyone; deep actions are Premium."""
    user_id = callback.from_user.id
    premium = await has_premium_access(user_id)
    today = today_iso()
    today_workouts = await db.fetch_one(
        """
        SELECT COUNT(*) as cnt
        FROM workout_sessions
        WHERE user_id = ? AND date = ? AND end_time IS NOT NULL
        """,
        (user_id, today),
    )
    stats = await db.fetch_one(
        "SELECT current_streak FROM user_stats WHERE user_id = ?",
        (user_id,),
    )
    today_status = "тренировка выполнена ✅" if (today_workouts and today_workouts["cnt"] > 0) else "тренировки сегодня ещё не было ⏳"
    streak = stats["current_streak"] if stats else 0
    access = "Premium-разбор доступен" if premium else "Базовый доступ: меню открыто, разбор — в Premium"

    text = (
        "🤖 *AI-ассистент*\n\n"
        "*Сегодня:*\n"
        f"• {today_status}\n"
        f"• Стрик: {streak} дн.\n"
        f"• {access}\n\n"
        "Выберите действие:"
    )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💡 Совет на сегодня", callback_data="ai_daily_tip"),
        InlineKeyboardButton(text="📋 План тренировки", callback_data="ai_workout_plan")
    )
    builder.row(
        InlineKeyboardButton(text="📈 Анализ прогресса", callback_data="ai_analyze"),
        InlineKeyboardButton(text="❓ Задать вопрос", callback_data="ai_ask")
    )
    if not premium:
        builder.row(InlineKeyboardButton(text="👑 Оформить Premium", callback_data="payment"))
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
    
    if await _ai_paywall(callback):
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
    if await _ai_paywall(callback):
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
    
    if await _ai_paywall(callback):
        return
    
    await callback.message.edit_text("🤔 *Анализирую ваш прогресс...*")
    
    analytics = await fetch_premium_analytics(user_id, 30)
    user = await db.fetch_one(
        "SELECT first_name FROM users WHERE user_id = ?",
        (user_id,)
    )
    user_data = {
        "first_name": user["first_name"] if user else "Пользователь",
        "analytics": {
            "volume": analytics["volume"],
            "regularity": analytics["regularity"],
            "strength": analytics["strength"][:5],
            "muscle_load": analytics["muscle_load"][:6],
        },
    }
    analysis = await openai_service.analyze_progress(user_data, analytics.get("history") or [])
    
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
    if await _ai_paywall(callback):
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

    if not await has_premium_access(user_id):
        await message.answer(
            build_teaser_paywall(
                "🤖 *AI-советы*",
                ["Вопросы к AI доступны в Premium."],
            ),
            reply_markup=premium_cta_markup("ai_advice"),
        )
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