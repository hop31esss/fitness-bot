"""PRO paywall triggers: banners after progress, workout milestones, shared keyboards."""

from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db
from handlers.subscription import has_premium_access

SHOW_PREMIUM_CALLBACK = "show_premium_info"

# Считаем «милестоун» после N завершённых сессий (включительно), в духе плана 3–5.
WORKOUT_MILESTONE_MIN = 3
WORKOUT_MILESTONE_MAX = 5


def build_open_pro_markup(back_callback: str | None = "progress_stats"):
    """Клавиатура с [Открыть PRO] и опционально «Назад»."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👑 Открыть PRO", callback_data=SHOW_PREMIUM_CALLBACK)
    )
    if back_callback:
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback))
    return builder.as_markup()


async def send_blocked_pro_message(
    message: Message,
    *,
    title: str,
    body: str,
    back_callback: str = "progress_stats",
) -> None:
    """Отдельное сообщение для заблокированного PRO-контента."""
    text = f"{title}\n\n{body}"
    await message.answer(text, reply_markup=build_open_pro_markup(back_callback))


async def maybe_send_progress_banner_after_view(callback: CallbackQuery) -> None:
    """
    Одноразовый баннер после просмотра экрана «Прогресс» (только без PRO).
    Отправляется отдельным сообщением после edit основного экрана.
    """
    user_id = callback.from_user.id
    if await has_premium_access(user_id):
        return

    row = await db.fetch_one(
        """
        SELECT COALESCE(pro_banner_shown_after_progress, 0) AS b
        FROM users WHERE user_id = ?
        """,
        (user_id,),
    )
    if not row or row["b"]:
        return

    text = (
        "👑 *Хочешь увидеть больше?*\n\n"
        "Рост силы по упражнениям, слабые мышцы, рекомендации и тренировочный объём — "
        "всё это в подписке PRO."
    )
    await callback.message.answer(
        text, reply_markup=build_open_pro_markup("progress_stats")
    )
    await db.execute(
        "UPDATE users SET pro_banner_shown_after_progress = 1 WHERE user_id = ?",
        (user_id,),
    )


async def maybe_send_workout_milestone_prompt(message: Message, user_id: int) -> None:
    """
    Одноразовое напоминание после 3–5 завершённых тренировок (по счётчику сессий).
    Пользователей с уже большим числом сессий помечаем без показа, чтобы не спамить.
    """
    if await has_premium_access(user_id):
        return

    row = await db.fetch_one(
        """
        SELECT COALESCE(pro_workout_milestone_prompt_shown, 0) AS m
        FROM users WHERE user_id = ?
        """,
        (user_id,),
    )
    if not row or row["m"]:
        return

    cnt_row = await db.fetch_one(
        "SELECT COUNT(*) AS c FROM workout_sessions WHERE user_id = ?",
        (user_id,),
    )
    c = int(cnt_row["c"]) if cnt_row else 0

    if c > WORKOUT_MILESTONE_MAX:
        await db.execute(
            "UPDATE users SET pro_workout_milestone_prompt_shown = 1 WHERE user_id = ?",
            (user_id,),
        )
        return

    if WORKOUT_MILESTONE_MIN <= c <= WORKOUT_MILESTONE_MAX:
        text = (
            "👑 *Уже несколько тренировок в записи!*\n\n"
            "Расширенная статистика, графики и AI-разбор — в PRO. "
            "Подключи, когда будешь готов усилить прогресс."
        )
        await message.answer(
            text, reply_markup=build_open_pro_markup("back_to_main")
        )
        await db.execute(
            "UPDATE users SET pro_workout_milestone_prompt_shown = 1 WHERE user_id = ?",
            (user_id,),
        )
