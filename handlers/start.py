from datetime import date

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db
from handlers.referral import handle_referral_join
from keyboards.main import get_main_keyboard
from utils.logging import log_action

router = Router()


def _add_hub_parent_buttons(builder: InlineKeyboardBuilder) -> None:
    builder.row(
        InlineKeyboardButton(text="◀️ Разделы", callback_data="back_to_main"),
        InlineKeyboardButton(text="🏠 Домой", callback_data="full_menu_back_to_start"),
    )


def build_training_menu() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🏋️ Начать тренировку", callback_data="start_workout"))
    builder.row(
        InlineKeyboardButton(text="📋 Журнал и история", callback_data="training_journal"),
        InlineKeyboardButton(text="📔 Дневник", callback_data="workout_journal"),
    )
    builder.row(
        InlineKeyboardButton(text="📚 Мои программы", callback_data="templates"),
        InlineKeyboardButton(text="💪 Упражнения", callback_data="exercises"),
    )
    _add_hub_parent_buttons(builder)
    return builder


def build_progress_menu() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📈 Обзор и статистика", callback_data="progress_stats"))
    builder.row(
        InlineKeyboardButton(text="📅 Календарь", callback_data="calendar"),
        InlineKeyboardButton(text="🏅 Достижения", callback_data="achievements"),
    )
    builder.row(InlineKeyboardButton(text="🏆 Лидерборд", callback_data="global_leaderboard"))
    _add_hub_parent_buttons(builder)
    return builder


def build_profile_menu() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 Мой профиль", callback_data="profile"))
    builder.row(
        InlineKeyboardButton(text="👑 Premium", callback_data="show_premium_info"),
        InlineKeyboardButton(text="💳 Оплата", callback_data="payment"),
    )
    builder.row(
        InlineKeyboardButton(text="🤝 Рефералы", callback_data="referral"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="settings"),
    )
    builder.row(InlineKeyboardButton(text="🎯 Недельная цель", callback_data="weekly_goal"))
    _add_hub_parent_buttons(builder)
    return builder


# Legacy builders remain import-compatible with existing tests/messages.
def build_full_main_menu() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for row in get_main_keyboard().inline_keyboard:
        builder.row(*row)
    return builder


def build_full_sub_menu() -> InlineKeyboardBuilder:
    return build_training_menu()


def build_section_back_menu() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu_training"))
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
    quick.row(InlineKeyboardButton(text="📋 Открыть разделы", callback_data="back_to_main"))
    return welcome_text, quick.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Домашний экран с быстрыми действиями и поддержкой рефералов."""
    user_id = message.from_user.id
    log_action(user_id, "start_command")
    await db.execute(
        """INSERT INTO users (user_id, username, first_name, last_name)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             username = excluded.username,
             first_name = excluded.first_name,
             last_name = excluded.last_name""",
        (
            user_id,
            message.from_user.username,
            message.from_user.first_name,
            message.from_user.last_name,
        ),
    )
    await handle_referral_join(message)
    welcome_text, quick_markup = await build_start_payload(user_id, message.from_user.first_name)
    await message.answer(welcome_text, reply_markup=quick_markup)


@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Открыть корень из четырёх разделов."""
    log_action(callback.from_user.id, "open_main_hubs")
    await callback.message.edit_text(
        "Выберите раздел:",
        reply_markup=get_main_keyboard(callback.from_user.id),
    )
    await callback.answer()


@router.callback_query(F.data == "full_menu_back_to_start")
async def full_menu_back_to_start(callback: CallbackQuery):
    """Вернуться на домашний экран `/start` без повторной регистрации."""
    log_action(callback.from_user.id, "back_to_home")
    welcome_text, quick_markup = await build_start_payload(
        callback.from_user.id, callback.from_user.first_name
    )
    await callback.message.edit_text(welcome_text, reply_markup=quick_markup)
    await callback.answer()


@router.callback_query(F.data.in_({"menu_training", "full_menu_open_sub"}))
async def menu_training(callback: CallbackQuery):
    log_action(callback.from_user.id, "menu_training")
    await callback.message.edit_text(
        "🏋️ *Тренировки*\n\nВыберите действие:",
        reply_markup=build_training_menu().as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu_progress")
async def menu_progress(callback: CallbackQuery):
    log_action(callback.from_user.id, "menu_progress")
    await callback.message.edit_text(
        "📊 *Прогресс*\n\nРезультаты, регулярность и достижения:",
        reply_markup=build_progress_menu().as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "menu_ai")
async def menu_ai(callback: CallbackQuery):
    log_action(callback.from_user.id, "menu_ai")
    from handlers.ai_advice import ai_advice_menu

    await ai_advice_menu(callback)


@router.callback_query(F.data == "menu_profile")
async def menu_profile(callback: CallbackQuery):
    log_action(callback.from_user.id, "menu_profile")
    await callback.message.edit_text(
        "👤 *Профиль*\n\nАккаунт, подписка и настройки:",
        reply_markup=build_profile_menu().as_markup(),
    )
    await callback.answer()


@router.callback_query(F.data == "full_section_journal")
async def full_section_journal(callback: CallbackQuery):
    from handlers.training import training_journal

    await training_journal(callback)


@router.callback_query(F.data == "full_section_diary")
async def full_section_diary(callback: CallbackQuery):
    from handlers.workout_journal import workout_journal_menu

    await workout_journal_menu(callback)


@router.callback_query(F.data == "full_section_programs")
async def full_section_programs(callback: CallbackQuery):
    from handlers.workout_templates import templates_menu

    await templates_menu(callback)


@router.callback_query(F.data == "full_section_exercises")
async def full_section_exercises(callback: CallbackQuery):
    from handlers.exercises import exercises_main_menu

    await exercises_main_menu(callback)
