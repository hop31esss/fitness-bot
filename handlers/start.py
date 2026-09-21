from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import date

from database.base import db
from handlers.referral import handle_referral_join
from keyboards.main import get_main_keyboard
from utils.logging import log_action

router = Router()


def build_full_main_menu() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for title in (
        "📘 Журнал тренировок",
        "📔 Дневник тренировок",
        "📚 Мои программы",
        "💪 Упражнения",
    ):
        builder.row(InlineKeyboardButton(text=title, callback_data="full_menu_open_sub"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="full_menu_back_to_start"))
    return builder


def build_full_sub_menu() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📘 Журнал тренировок", callback_data="full_section_journal"))
    builder.row(InlineKeyboardButton(text="📔 Дневник тренировок", callback_data="full_section_diary"))
    builder.row(InlineKeyboardButton(text="📚 Мои программы", callback_data="full_section_programs"))
    builder.row(InlineKeyboardButton(text="💪 Упражнения", callback_data="full_section_exercises"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_main"))
    return builder


def build_section_back_menu() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="full_menu_open_sub"))
    return builder


async def build_start_payload(user_id: int, first_name: str) -> tuple[str, object]:
    today = date.today().isoformat()
    today_sessions = await db.fetch_one(
        """
        SELECT COUNT(*) as cnt
        FROM workout_sessions
        WHERE user_id = ? AND date = ? AND end_time IS NOT NULL
        """,
        (user_id, today),
    )
    streak = await db.fetch_one(
        "SELECT current_streak FROM user_stats WHERE user_id = ?",
        (user_id,),
    )

    sessions_done = today_sessions["cnt"] if today_sessions else 0
    current_streak = streak["current_streak"] if streak else 0
    today_status = "✅ Уже тренировались сегодня" if sessions_done > 0 else "⏳ Сегодня тренировки ещё не было"

    welcome_text = (
        f"👋 *Привет, {first_name}!*\n\n"
        "*Сегодня:*\n"
        f"{today_status}\n"
        f"🔥 Стрик: {current_streak} дн.\n\n"
        "Что хотите сделать сейчас?"
    )

    quick = InlineKeyboardBuilder()
    quick.row(InlineKeyboardButton(text="🏋️ Начать тренировку", callback_data="start_workout"))
    quick.row(
        InlineKeyboardButton(text="✍️ Записать", callback_data="training_journal"),
        InlineKeyboardButton(text="📊 Прогресс", callback_data="progress_stats"),
    )
    quick.row(InlineKeyboardButton(text="📋 Открыть всё меню", callback_data="back_to_main"))
    return welcome_text, quick.as_markup()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start с поддержкой рефералов"""
    user_id = message.from_user.id
    log_action(user_id, "start_command")

    # Регистрируем пользователя
    await db.execute(
        """INSERT INTO users (user_id, username, first_name, last_name)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             username = excluded.username,
             first_name = excluded.first_name,
             last_name = excluded.last_name""",
        (user_id, message.from_user.username,
         message.from_user.first_name, message.from_user.last_name),
    )

    # Обрабатываем реферальный старт (7 дней другу сразу, бонус рефереру после удержания).
    await handle_referral_join(message)

    welcome_text, quick_markup = await build_start_payload(user_id, message.from_user.first_name)
    await message.answer(welcome_text, reply_markup=quick_markup)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в рабочее главное меню."""
    log_action(callback.from_user.id, "open_full_menu")
    await callback.message.edit_text(
        text="👋 Выбирай, что сделать:",
        reply_markup=get_main_keyboard(),
    )
    await callback.answer()


@router.callback_query(F.data == "full_menu_back_to_start")
async def full_menu_back_to_start(callback: CallbackQuery):
    """Возврат со страницы полного меню к стартовому экрану."""
    log_action(callback.from_user.id, "full_menu_back_to_start")
    welcome_text, quick_markup = await build_start_payload(
        callback.from_user.id, callback.from_user.first_name
    )
    await callback.message.edit_text(welcome_text, reply_markup=quick_markup)
    await callback.answer()


@router.callback_query(F.data == "full_menu_open_sub")
async def full_menu_open_sub(callback: CallbackQuery):
    """Единое под-меню с разделами."""
    log_action(callback.from_user.id, "full_menu_open_sub")
    keyboard = build_full_sub_menu().as_markup()
    await callback.message.edit_text(text="📂 *Разделы*\n\nВыберите, куда перейти:", reply_markup=keyboard)
    await callback.answer()


@router.callback_query(F.data == "full_section_journal")
async def full_section_journal(callback: CallbackQuery):
    log_action(callback.from_user.id, "full_section_journal")
    from handlers.training import training_journal
    await training_journal(callback)


@router.callback_query(F.data == "full_section_diary")
async def full_section_diary(callback: CallbackQuery):
    log_action(callback.from_user.id, "full_section_diary")
    from handlers.workout_journal import workout_journal_menu
    await workout_journal_menu(callback)


@router.callback_query(F.data == "full_section_programs")
async def full_section_programs(callback: CallbackQuery):
    log_action(callback.from_user.id, "full_section_programs")
    from handlers.workout_templates import templates_menu
    await templates_menu(callback)


@router.callback_query(F.data == "full_section_exercises")
async def full_section_exercises(callback: CallbackQuery):
    log_action(callback.from_user.id, "full_section_exercises")
    from handlers.exercises import exercises_main_menu
    await exercises_main_menu(callback)