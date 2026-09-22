import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from handlers.premium import build_teaser_paywall, premium_cta_markup
from handlers.subscription import has_premium_access
from services.openai_service import openai_service
from services.premium_triggers import maybe_send_progress_banner_after_view
from services.progress_analytics import (
    VALID_PERIODS,
    fetch_free_progress_block,
    fetch_premium_analytics,
    format_kg,
    progress_bar,
)

router = Router()
logger = logging.getLogger(__name__)

MAX_AI_LEN = 3500
BLOCKS = (
    ("strength", "🏋️ Сила"),
    ("volume", "📦 Объём"),
    ("muscles", "💪 Мышцы"),
    ("regularity", "🔥 Регулярность"),
    ("prs", "🏆 Рекорды"),
)


def _period_buttons(days: int, premium: bool) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    if premium:
        row = []
        for value in VALID_PERIODS:
            mark = "•" if value == days else ""
            row.append(
                InlineKeyboardButton(
                    text=f"{mark}{value} дн.",
                    callback_data=f"progress_period:{value}",
                )
            )
        builder.row(*row)
        first = [InlineKeyboardButton(text=label, callback_data=f"progress_block:{key}:{days}")
                 for key, label in BLOCKS[:3]]
        builder.row(*first)
        builder.row(
            *[
                InlineKeyboardButton(text=label, callback_data=f"progress_block:{key}:{days}")
                for key, label in BLOCKS[3:]
            ]
        )
        builder.row(
            InlineKeyboardButton(text="🤖 AI-анализ", callback_data=f"progress_ai_insight:{days}")
        )
    else:
        builder.row(InlineKeyboardButton(text="👑 Оформить Premium", callback_data="payment"))
    builder.row(
        InlineKeyboardButton(text="📅 Календарь", callback_data="calendar"),
        InlineKeyboardButton(text="↩️ В прогресс", callback_data="menu_progress"),
    )
    return builder


def _format_date(value: str | None) -> str:
    if not value:
        return ""
    try:
        _year, month, day = value[:10].split("-")
        months = (
            "января", "февраля", "марта", "апреля", "мая", "июня",
            "июля", "августа", "сентября", "октября", "ноября", "декабря",
        )
        return f"{int(day)} {months[int(month) - 1]}"
    except (TypeError, ValueError, IndexError):
        return value


def _build_free_text(free: dict, *, premium: bool) -> str:
    latest = free.get("latest_workout")
    latest_text = (
        f"{latest['label']}\n{_format_date(latest['date'])}"
        if latest else "Пока нет завершённых тренировок"
    )
    lines = [
        "📊 *ТВОЙ ПРОГРЕСС*",
        "",
        "За последние 30 дней:",
        "",
        f"🏋️ Тренировок: {free['total_sessions']}",
        f"🔥 Серия: {free['current_streak']}",
        f"⏱ Средняя длительность: {free['average_duration']} мин",
        f"💪 Упражнений выполнено: {free['exercise_count']}",
        f"📦 Общий объём: {format_kg(free['total_volume'])} кг",
        "",
        "Последняя тренировка:",
        latest_text,
    ]
    if not premium:
        lines.extend(
            [
                "",
                "────────────────",
                "",
                "💎 *В PREMIUM:*",
                "📈 Динамика силы",
                "💪 Распределение нагрузки по мышцам",
                "🏆 Личные рекорды",
                "📊 Подробная статистика за 90 дней",
                "📤 Экспорт данных",
            ]
        )
    return "\n".join(lines)


def _build_strength_text(data: dict) -> str:
    lines = [f"🏋️ *СИЛА* · {data['period_days']} дн.", ""]
    if not data["strength"]:
        return "\n".join(lines + ["Недостаточно данных с весом."])
    for item in data["strength"][:8]:
        lines.append(f"*{item['name']}*")
        lines.append(f"Лучший результат: {format_kg(item['weight'], 1)} кг × {int(item['reps'])}")
        if item["estimated_1rm"]:
            lines.append(f"Расчётный 1ПМ: {format_kg(item['estimated_1rm'], 1)} кг")
        if item["previous_max"]:
            sign = "+" if item["change"] >= 0 else ""
            lines.append(f"За период: {sign}{format_kg(item['change'], 1)} кг")
        lines.append(f"Выполнений: {item['times']}")
        if item["is_pr"]:
            lines.append("🏆 Новый личный рекорд")
        lines.append("")
    return "\n".join(lines).rstrip()


def _build_volume_text(data: dict) -> str:
    volume = data["volume"]
    change = volume["change_pct"]
    change_text = f"{change:+.1f}%" if change is not None else "нет базы для сравнения"
    lines = [
        f"📦 *ОБЪЁМ* · {data['period_days']} дн.",
        "",
        f"Этот период: {format_kg(volume['current'])} кг",
        f"Прошлый: {format_kg(volume['previous'])} кг",
        f"Изменение: {change_text}",
        "",
    ]
    by_muscle = volume.get("by_muscle") or {}
    if by_muscle:
        for name, value in sorted(by_muscle.items(), key=lambda item: item[1], reverse=True)[:8]:
            lines.append(f"{name}: {format_kg(value)} кг")
    else:
        lines.append("Нет данных с весом для разбивки.")
    return "\n".join(lines)


def _build_muscles_text(data: dict) -> str:
    lines = [f"💪 *НАГРУЗКА ПО МЫШЦАМ* · {data['period_days']} дн.", ""]
    if not data["muscle_load"]:
        return "\n".join(lines + ["Недостаточно данных."])
    for item in data["muscle_load"]:
        lines.append(f"{item['name']:<12} {progress_bar(item['pct'])}  {item['pct']:.0f}%")
    if data.get("muscle_insight"):
        lines.extend(["", f"⚠️ {data['muscle_insight']}"])
    return "\n".join(lines)


def _build_regularity_text(data: dict) -> str:
    regular = data["regularity"]
    goal = f"{regular['goal_pct']:.0f}%" if regular["goal_pct"] is not None else "—"
    lines = [
        f"🔥 *РЕГУЛЯРНОСТЬ* · {data['period_days']} дн.",
        "",
        f"Серия: {regular['current_streak']}",
        f"Тренировок: {regular['sessions']}",
        f"Выполнение плана: {goal} (цель {regular['weekly_goal']}/нед.)",
        "",
    ]
    for month in regular.get("months") or []:
        lines.append(f"{month['name']:<10} {progress_bar(month['pct'])} {month['pct']:.0f}%")
    if regular.get("average_pct") is not None:
        lines.append(f"\nСреднее: {regular['average_pct']:.0f}%")
    if regular.get("best_week"):
        lines.append(f"Самая стабильная неделя: {regular['best_week']}")
    if regular.get("avg_gap_days") is not None:
        lines.append(f"Средний перерыв: {regular['avg_gap_days']} дн.")
    return "\n".join(lines)


def _build_prs_text(data: dict) -> str:
    lines = [f"🏆 *ЛИЧНЫЕ РЕКОРДЫ* · {data['period_days']} дн.", ""]
    if not data["prs"]:
        return "\n".join(lines + ["Добавьте вес в упражнениях — появятся рекорды."])
    for item in data["prs"]:
        lines.append(f"{item['name']}")
        lines.append(f"{item['display']}")
        if item.get("date"):
            lines.append(_format_date(item["date"]))
        lines.append("")
    last = data.get("last_pr")
    if last:
        lines.append(f"Последний PR: {last['name']} — {_format_date(last['date'])}")
    return "\n".join(lines).rstrip()


BLOCK_BUILDERS = {
    "strength": _build_strength_text,
    "volume": _build_volume_text,
    "muscles": _build_muscles_text,
    "regularity": _build_regularity_text,
    "prs": _build_prs_text,
}


def _parse_days(raw: str | None) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 30
    return value if value in VALID_PERIODS else 30


async def _send_progress_screen(callback: CallbackQuery, days: int = 30) -> None:
    user_id = callback.from_user.id
    premium = await has_premium_access(user_id)
    free = await fetch_free_progress_block(user_id)
    text = _build_free_text(free, premium=premium)
    if premium:
        text += (
            f"\n\n💎 *РАСШИРЕННАЯ СТАТИСТИКА*\n"
            f"Период: {days} дн. Выберите раздел:"
        )
    if len(text) > 4090:
        text = text[:4080] + "…"
    await callback.message.edit_text(text, reply_markup=_period_buttons(days, premium).as_markup())
    if not premium:
        await maybe_send_progress_banner_after_view(callback)


@router.callback_query(F.data.in_({"progress_stats", "advanced_stats"}))
async def progress_stats_menu(callback: CallbackQuery):
    try:
        await _send_progress_screen(callback)
    except Exception as exc:
        logger.error("Ошибка в progress_stats: %s", exc)
        await callback.message.answer("❌ Ошибка загрузки статистики")
    await callback.answer()


@router.callback_query(F.data.startswith("progress_period:"))
async def progress_period(callback: CallbackQuery):
    days = _parse_days(callback.data.split(":")[1])
    if not await has_premium_access(callback.from_user.id):
        await callback.message.edit_text(
            build_teaser_paywall(
                "📊 *ТВОЙ ПРОГРЕСС*",
                ["Выбор периода 7/30/90 дней доступен в Premium."],
            ),
            reply_markup=premium_cta_markup("progress_stats"),
        )
        await callback.answer()
        return
    await _send_progress_screen(callback, days)
    await callback.answer()


@router.callback_query(F.data.startswith("progress_block:"))
async def progress_block(callback: CallbackQuery):
    parts = callback.data.split(":")
    key = parts[1] if len(parts) > 1 else "strength"
    days = _parse_days(parts[2] if len(parts) > 2 else "30")
    if not await has_premium_access(callback.from_user.id):
        await callback.message.edit_text(
            build_teaser_paywall(
                "💎 *РАСШИРЕННАЯ СТАТИСТИКА*",
                ["Базовый обзор за 30 дней уже на экране «Прогресс»."],
            ),
            reply_markup=premium_cta_markup("progress_stats"),
        )
        await callback.answer()
        return
    builder_fn = BLOCK_BUILDERS.get(key)
    if builder_fn is None:
        await callback.answer("Раздел не найден", show_alert=True)
        return
    data = await fetch_premium_analytics(callback.from_user.id, days)
    text = builder_fn(data)
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ К разделам", callback_data=f"progress_period:{days}")
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("progress_ai_insight"))
async def progress_ai_insight(callback: CallbackQuery):
    user_id = callback.from_user.id
    days = _parse_days(callback.data.split(":")[1] if ":" in callback.data else "30")
    if not await has_premium_access(user_id):
        await callback.message.edit_text(
            build_teaser_paywall(
                "🤖 *AI-анализ прогресса*",
                ["Цифры остаются в «Прогресс». AI объясняет, что они значат."],
            ),
            reply_markup=premium_cta_markup("progress_stats"),
        )
        await callback.answer()
        return

    await callback.answer()
    await callback.message.edit_text("🤖 *Готовлю анализ…*")
    analytics = await fetch_premium_analytics(user_id, days)
    user = None
    try:
        from database.base import db

        user = await db.fetch_one(
            "SELECT first_name FROM users WHERE user_id = ?",
            (user_id,),
        )
    except Exception:
        user = None
    summary = {
        "period_days": analytics["period_days"],
        "volume": analytics["volume"],
        "regularity": analytics["regularity"],
        "strength": analytics["strength"][:5],
        "muscle_load": analytics["muscle_load"][:6],
        "prs": analytics["prs"][:5],
        "insight": analytics.get("muscle_insight"),
    }
    analysis = await openai_service.analyze_progress(
        {"first_name": user["first_name"] if user else "Атлет", "analytics": summary},
        analytics.get("history") or [],
    )
    if analysis:
        body = analysis.strip()
        if len(body) > MAX_AI_LEN:
            body = body[:MAX_AI_LEN] + "…"
        text = f"🤖 *AI — разбор прогресса*\n\n{body}"
    else:
        text = (
            "❌ Не удалось получить AI-анализ. Проверьте ключ API или попробуйте позже.\n\n"
            "Цифры по блокам силы, объёма и мышц по-прежнему доступны."
        )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Ещё раз", callback_data=f"progress_ai_insight:{days}"),
        InlineKeyboardButton(text="📈 К прогрессу", callback_data="progress_stats"),
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
