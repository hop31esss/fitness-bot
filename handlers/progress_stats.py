from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging

from database.base import db
from handlers.subscription import has_premium_access
from services.progress_analytics import (
    fetch_free_progress_block,
    fetch_premium_analytics,
    format_muscle_percentages,
    format_ppl_percentages,
)
from services.openai_service import openai_service
from services.premium_triggers import (
    build_open_pro_markup,
    maybe_send_progress_banner_after_view,
)

router = Router()
logger = logging.getLogger(__name__)

MAX_AI_LEN = 3500


def _build_free_text(free: dict, *, show_pro_hint: bool = True) -> str:
    lines = [
        "📈 *Прогресс*",
        "",
        f"▫️ Тренировок (сессий): *{free['total_sessions']}*",
        f"▫️ Дней с тренировками: *{free['active_days']}*",
        f"▫️ Примерный суммарный объём: *{free['total_volume']:,.0f}* кг·повтор",
        "",
    ]
    if free["recent_exercises"]:
        lines.append("*Последние упражнения:*")
        lines.extend(free["recent_exercises"])
    else:
        lines.append("_Пока нет записанных упражнений — начните тренировку!_")
    if show_pro_hint:
        lines.extend(
            [
                "",
                "👑 *PRO:* графики, рекорды по весу, баланс push/pull, разбор мышц,",
                "тоннаж по неделям, серии и AI-анализ — всё в этом разделе.",
            ]
        )
    return "\n".join(lines)


def _build_premium_extra_text(p: dict) -> str:
    blocks = [
        "",
        "⭐️ *PRO — детали*",
        "",
        f"🔥 Серия: *{p['current_streak']}* дн. · рекорд серии: *{p['longest_streak']}* дн.",
        f"📅 За 4 недели недель с тренировками: *{p['weeks_with_workouts']}* / 4",
        f"⚖️ Тоннаж за 7 дней: *{p['week_volume']:,.0f}* кг·повтор",
        "",
        "*Рекорды по весу (топ):*",
    ]
    if p["pr_list"]:
        for pr in p["pr_list"][:6]:
            blocks.append(f"▫️ {pr['name'][:40]} — *{pr['weight']:.1f}* кг")
    else:
        blocks.append("_Добавьте вес в упражнениях — появятся PR._")
    blocks.append("")
    blocks.append("*Баланс нагрузки (по объёму с весом):*")
    blocks.append(
        format_ppl_percentages(
            p["push_v"], p["pull_v"], p["legs_v"], p["other_v"], p["ppl_total"]
        )
    )
    blocks.append("")
    blocks.append("*Группы мышц (доля объёма):*")
    blocks.append(format_muscle_percentages(p["muscle_vol"]))
    return "\n".join(blocks)


async def _send_progress_screen(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    premium = await has_premium_access(user_id)

    free = await fetch_free_progress_block(user_id)
    text = _build_free_text(free, show_pro_hint=not premium)

    if premium:
        extra = await fetch_premium_analytics(user_id)
        text = text + "\n" + _build_premium_extra_text(extra)

    builder = InlineKeyboardBuilder()
    if premium:
        builder.row(
            InlineKeyboardButton(text="📊 Графики", callback_data="progress_charts"),
            InlineKeyboardButton(text="🤖 AI-анализ", callback_data="progress_ai_insight"),
        )
        builder.row(
            InlineKeyboardButton(text="📅 Календарь", callback_data="calendar"),
            InlineKeyboardButton(text="🏆 Лидеры", callback_data="global_leaderboard"),
        )
        builder.row(
            InlineKeyboardButton(text="📋 Детальная статистика", callback_data="stats"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="📅 Календарь", callback_data="calendar"),
            InlineKeyboardButton(text="🏆 Лидеры", callback_data="global_leaderboard"),
        )
        builder.row(
            InlineKeyboardButton(text="📋 Общая статистика", callback_data="stats"),
        )
        builder.row(
            InlineKeyboardButton(text="👑 Открыть PRO", callback_data="show_premium_info"),
        )
    builder.row(InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_main"))

    if len(text) > 4090:
        text = text[:4080] + "…"

    await callback.message.edit_text(text, reply_markup=builder.as_markup())

    if not premium:
        await maybe_send_progress_banner_after_view(callback)


@router.callback_query(F.data == "progress_stats")
async def progress_stats_menu(callback: CallbackQuery):
    """Меню прогресса: базовые метрики для всех, расширение для PRO."""
    try:
        await _send_progress_screen(callback)
    except Exception as e:
        logger.error("Ошибка в progress_stats: %s", e)
        await callback.message.answer("❌ Ошибка загрузки статистики")
    await callback.answer()


@router.callback_query(F.data == "advanced_stats")
async def advanced_stats_entry(callback: CallbackQuery):
    """Точка входа из меню премиум — тот же экран прогресса."""
    try:
        await _send_progress_screen(callback)
    except Exception as e:
        logger.error("Ошибка advanced_stats: %s", e)
        await callback.message.answer("❌ Ошибка загрузки")
    await callback.answer()


@router.callback_query(F.data == "progress_ai_insight")
async def progress_ai_insight(callback: CallbackQuery):
    """Короткий AI-разбор прогресса для PRO (внутри раздела «Прогресс»)."""
    user_id = callback.from_user.id
    if not await has_premium_access(user_id):
        await callback.answer("Доступно в PRO", show_alert=True)
        await callback.message.answer(
            "👑 *AI-анализ прогресса* доступен в подписке PRO.",
            reply_markup=build_open_pro_markup("progress_stats"),
        )
        return

    await callback.answer()
    await callback.message.answer("🤖 *Готовлю анализ…*")

    history = await db.fetch_all(
        """
        SELECT ws.date, we.exercise_name, we.sets, we.reps, we.weight
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ?
        ORDER BY ws.date DESC
        LIMIT 40
        """,
        (user_id,),
    )
    user = await db.fetch_one(
        "SELECT first_name FROM users WHERE user_id = ?",
        (user_id,),
    )
    user_data = {"first_name": user["first_name"] if user else "Атлет"}
    analysis = await openai_service.analyze_progress(user_data, history)

    if analysis:
        body = analysis.strip()
        if len(body) > MAX_AI_LEN:
            body = body[:MAX_AI_LEN] + "…"
        text = f"🤖 *AI — разбор прогресса*\n\n{body}"
    else:
        text = (
            "❌ Не удалось получить AI-анализ. Проверьте ключ API или попробуйте позже.\n\n"
            "Графики и цифры по-прежнему в разделе «Прогресс» и «Графики»."
        )

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Ещё раз", callback_data="progress_ai_insight"),
        InlineKeyboardButton(text="📈 К прогрессу", callback_data="progress_stats"),
    )

    await callback.message.answer(text, reply_markup=builder.as_markup())
