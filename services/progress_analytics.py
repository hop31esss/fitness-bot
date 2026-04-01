"""
Расчёты для экрана «Прогресс»: базовые метрики (free) и аналитика PRO.
Классификация упражнений — эвристика по ключевым словам в названии.
"""
from __future__ import annotations

from typing import Any, Dict, List

from database.base import db


def _norm(name: str) -> str:
    return (name or "").lower()


def exercise_push_pull_legs(name: str) -> str:
    """Грубая категория для баланса push/pull/legs."""
    n = _norm(name)
    leg_kw = (
        "присед", "жим ног", "выпад", "сгибан", "разгибан", "ног", "икр",
        "squat", "leg press", "lunge", "rdl", "румын", "deadlift", "смит",
    )
    if any(k in n for k in leg_kw):
        return "legs"
    pull_kw = (
        "тяга", "подтягиван", "pull", "row", "шраг", "бицепс", "сгибан",
        "curl", "face pull", "пуловер", "пулл", "верхний блок", "нижний блок",
    )
    push_kw = (
        "жим", "bench", "press", "отжиман", "push", "разгибан", "трицепс",
        "махи", "флай", "fly", "raise", "кроссовер",
    )
    if any(k in n for k in pull_kw):
        return "pull"
    if any(k in n for k in push_kw):
        return "push"
    return "other"


def exercise_muscle_group(name: str) -> str:
    """Группа мышц для распределения объёма (проценты)."""
    n = _norm(name)
    if any(k in n for k in ("присед", "жим ног", "выпад", "ног", "икр", "squat", "leg")):
        return "Ноги"
    if any(k in n for k in ("грудь", "жим л", "жим лёжа", "bench", "отжиман", "fly")):
        return "Грудь"
    if any(k in n for k in ("спина", "тяга", "подтягиван", "шраг", "row", "пуловер")):
        return "Спина"
    if any(k in n for k in ("плеч", "дельт", "shoulder", "махи", "армейск")):
        return "Плечи"
    if any(k in n for k in ("бицепс", "трицепс", "предплеч", "curl", "разгибан")):
        return "Руки"
    return "Другое"


def _row_volume(sets: Any, reps: Any, weight: Any) -> float:
    try:
        s = int(sets or 0)
        r = int(reps or 0)
        w = float(weight or 0)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, float(s * r * w))


async def fetch_free_progress_block(user_id: int) -> Dict[str, Any]:
    """Базовые метрики для free: сессии, дни активности, объём, последние упражнения."""
    sessions_row = await db.fetch_one(
        "SELECT COUNT(*) AS c FROM workout_sessions WHERE user_id = ?",
        (user_id,),
    )
    total_sessions = int(sessions_row["c"] or 0) if sessions_row else 0

    days_row = await db.fetch_one(
        """
        SELECT COUNT(DISTINCT date) AS d
        FROM workout_sessions
        WHERE user_id = ?
        """,
        (user_id,),
    )
    active_days = int(days_row["d"] or 0) if days_row else 0

    vol_row = await db.fetch_one(
        """
        SELECT COALESCE(SUM(
            COALESCE(we.sets, 0) * COALESCE(we.reps, 0) * COALESCE(we.weight, 0)
        ), 0) AS v
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ?
        """,
        (user_id,),
    )
    total_volume = float(vol_row["v"] or 0) if vol_row else 0.0

    recent = await db.fetch_all(
        """
        SELECT we.exercise_name, ws.date
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ?
        ORDER BY ws.date DESC, we.id DESC
        LIMIT 25
        """,
        (user_id,),
    )
    seen: set = set()
    recent_lines: List[str] = []
    for row in recent:
        name = row["exercise_name"]
        if name in seen:
            continue
        seen.add(name)
        d = (row["date"] or "")[:10]
        recent_lines.append(f"• {name} ({d})")
        if len(recent_lines) >= 5:
            break

    return {
        "total_sessions": total_sessions,
        "active_days": active_days,
        "total_volume": total_volume,
        "recent_exercises": recent_lines,
    }


async def fetch_premium_analytics(user_id: int) -> Dict[str, Any]:
    """PR, push/pull/legs, группы мышц, тоннаж за 7 дней, недели с тренировками."""
    streak_row = await db.fetch_one(
        "SELECT current_streak, longest_streak FROM user_stats WHERE user_id = ?",
        (user_id,),
    )
    current_streak = int(streak_row["current_streak"] or 0) if streak_row else 0
    longest_streak = int(streak_row["longest_streak"] or 0) if streak_row else 0

    pr_rows = await db.fetch_all(
        """
        SELECT we.exercise_name, MAX(we.weight) AS max_w
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ? AND we.weight IS NOT NULL AND we.weight > 0
        GROUP BY we.exercise_name
        ORDER BY max_w DESC
        LIMIT 8
        """,
        (user_id,),
    )
    pr_list = [
        {"name": r["exercise_name"], "weight": float(r["max_w"])}
        for r in pr_rows
    ]

    vol_rows = await db.fetch_all(
        """
        SELECT we.exercise_name,
               we.sets, we.reps, we.weight
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ?
        """,
        (user_id,),
    )

    push_v = pull_v = legs_v = other_v = 0.0
    muscle_vol: Dict[str, float] = {}
    for r in vol_rows:
        v = _row_volume(r["sets"], r["reps"], r["weight"])
        if v <= 0:
            continue
        cat = exercise_push_pull_legs(r["exercise_name"])
        if cat == "push":
            push_v += v
        elif cat == "pull":
            pull_v += v
        elif cat == "legs":
            legs_v += v
        else:
            other_v += v
        mg = exercise_muscle_group(r["exercise_name"])
        muscle_vol[mg] = muscle_vol.get(mg, 0.0) + v

    ppl_total = push_v + pull_v + legs_v + other_v

    week_row = await db.fetch_one(
        """
        SELECT COALESCE(SUM(
            COALESCE(we.sets, 0) * COALESCE(we.reps, 0) * COALESCE(we.weight, 0)
        ), 0) AS v
        FROM workout_exercises we
        JOIN workout_sessions ws ON we.session_id = ws.id
        WHERE ws.user_id = ?
          AND ws.date >= date('now', '-7 days')
        """,
        (user_id,),
    )
    week_volume = float(week_row["v"] or 0) if week_row else 0.0

    weeks_row = await db.fetch_one(
        """
        SELECT COUNT(DISTINCT strftime('%Y-%W', date)) AS w
        FROM workout_sessions
        WHERE user_id = ?
          AND date >= date('now', '-28 days')
        """,
        (user_id,),
    )
    weeks_with_workouts = int(weeks_row["w"] or 0) if weeks_row else 0

    return {
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "pr_list": pr_list,
        "push_v": push_v,
        "pull_v": pull_v,
        "legs_v": legs_v,
        "other_v": other_v,
        "ppl_total": ppl_total,
        "muscle_vol": muscle_vol,
        "week_volume": week_volume,
        "weeks_with_workouts": weeks_with_workouts,
    }


def format_ppl_percentages(push_v: float, pull_v: float, legs_v: float, other_v: float, total: float) -> str:
    if total <= 0:
        return "Недостаточно данных с весом для баланса push/pull."
    lines = []
    for label, val in (
        ("Push", push_v),
        ("Pull", pull_v),
        ("Ноги", legs_v),
        ("Прочее", other_v),
    ):
        pct = 100.0 * val / total
        lines.append(f"▫️ {label}: *{pct:.0f}%*")
    return "\n".join(lines)


def format_muscle_percentages(muscle_vol: Dict[str, float]) -> str:
    total = sum(muscle_vol.values())
    if total <= 0:
        return "Недостаточно данных для разбивки по мышцам."
    order = ["Грудь", "Спина", "Ноги", "Плечи", "Руки", "Другое"]
    lines = []
    for key in order:
        if key not in muscle_vol:
            continue
        pct = 100.0 * muscle_vol[key] / total
        lines.append(f"▫️ {key}: *{pct:.0f}%*")
    for k, v in muscle_vol.items():
        if k not in order:
            pct = 100.0 * v / total
            lines.append(f"▫️ {k}: *{pct:.0f}%*")
    return "\n".join(lines) if lines else "—"
