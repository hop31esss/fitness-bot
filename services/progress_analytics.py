"""Canonical calculations for Progress, calendar, journal, and history.

Completed ``workout_sets`` rows are authoritative. Aggregate exercise columns
are used only when an exercise has no completed sets, so mixed old/new data is
never counted twice.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from datetime import date, datetime, timedelta
from typing import Any

from database.base import db
from utils.clock import today as local_today

VALID_PERIODS = (7, 30, 90)
DEFAULT_WEEKLY_GOAL = 3
UNDEFINED_MUSCLE = "Не определено"

EXERCISE_VOLUME_SQL = """
CASE WHEN EXISTS (
    SELECT 1 FROM workout_sets s
    WHERE s.workout_exercise_id = we.id AND s.completed = 1
) THEN (
    SELECT COALESCE(SUM(s.weight * s.reps), 0)
    FROM workout_sets s
    WHERE s.workout_exercise_id = we.id AND s.completed = 1
) ELSE COALESCE(we.sets, 0) * COALESCE(we.reps, 0) * COALESCE(we.weight, 0)
END
"""


def _norm(name: str) -> str:
    return " ".join((name or "").strip().casefold().replace("ё", "е").split())


def exercise_push_pull_legs(name: str) -> str:
    n = _norm(name)
    if any(k in n for k in (
        "присед", "жим ног", "выпад", "ног", "икр", "squat", "leg press",
        "lunge", "rdl", "румын", "deadlift", "смит",
    )):
        return "legs"
    if any(k in n for k in (
        "тяга", "подтягиван", "pull", "row", "шраг", "бицепс", "сгибан",
        "curl", "face pull", "пуловер", "пулл", "верхний блок", "нижний блок",
    )):
        return "pull"
    if any(k in n for k in (
        "жим", "bench", "press", "отжиман", "push", "разгибан", "трицепс",
        "махи", "флай", "fly", "raise", "кроссовер",
    )):
        return "push"
    return "other"


def estimated_1rm(weight: float, reps: float) -> float:
    """Epley: weight * (1 + reps / 30). A true single is used as-is."""
    w = _number(weight)
    r = _number(reps)
    if w <= 0 or r <= 0:
        return 0.0
    if r <= 1:
        return w
    return w * (1.0 + r / 30.0)


def format_kg(value: float, digits: int = 0) -> str:
    number = round(float(value or 0), digits)
    if digits == 0:
        rendered = f"{int(number):,}"
    else:
        rendered = f"{number:,.{digits}f}"
    return rendered.replace(",", " ")


def progress_bar(pct: float, width: int = 12) -> str:
    clamped = max(0.0, min(100.0, float(pct or 0)))
    filled = round(clamped / 100.0 * width)
    return "█" * filled + "░" * (width - filled)


def _number(value: Any) -> float:
    try:
        return max(0.0, float(value or 0))
    except (TypeError, ValueError):
        return 0.0


def _row_volume(sets: Any, reps: Any, weight: Any) -> float:
    return _number(sets) * _number(reps) * _number(weight)


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _duration_minutes(start: Any, end: Any) -> int:
    if not start or not end:
        return 0
    try:
        start_dt = datetime.strptime(str(start)[:5], "%H:%M")
        end_dt = datetime.strptime(str(end)[:5], "%H:%M")
        minutes = int((end_dt - start_dt).total_seconds() // 60)
        return minutes if minutes >= 0 else minutes + 24 * 60
    except (TypeError, ValueError):
        return 0


def _current_streak(days: Iterable[date], today: date | None = None) -> int:
    unique = set(days)
    if not unique:
        return 0
    cursor = today or local_today()
    if cursor not in unique:
        cursor -= timedelta(days=1)
    streak = 0
    while cursor in unique:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def _month_label(value: date) -> str:
    names = (
        "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    )
    return names[value.month - 1]


async def fetch_canonical_history(
    user_id: int,
    days: int | None = None,
    *,
    include_previous: bool = False,
    start: str | None = None,
    end: str | None = None,
) -> list[dict[str, Any]]:
    """Return one row per exact set, or one aggregate fallback exercise row."""
    clauses = ["ws.user_id = ?"]
    params: list[Any] = [user_id]
    if start and end:
        clauses.append("date(ws.date) BETWEEN date(?) AND date(?)")
        params.extend([start, end])
    elif days is not None:
        if days <= 0:
            raise ValueError("days must be positive")
        window = days * (2 if include_previous else 1)
        clauses.append("date(ws.date) >= date('now', ?)")
        params.append(f"-{window - 1} days")
    rows = await db.fetch_all(
        f"""
        SELECT ws.id AS session_id, ws.date, ws.start_time, ws.end_time,
               we.id AS workout_exercise_id, we.exercise_name, we.exercise_type,
               s.id AS set_id, s.set_number,
               CASE WHEN s.id IS NOT NULL THEN 1
                    ELSE COALESCE(we.sets, 0) END AS sets,
               CASE WHEN s.id IS NOT NULL THEN s.reps ELSE we.reps END AS reps,
               CASE WHEN s.id IS NOT NULL THEN s.weight ELSE we.weight END AS weight,
               CASE WHEN s.id IS NOT NULL THEN 'exact' ELSE 'aggregate' END AS source
        FROM workout_sessions ws
        JOIN workout_exercises we ON we.session_id = ws.id
        LEFT JOIN workout_sets s
          ON s.workout_exercise_id = we.id AND s.completed = 1
        WHERE {" AND ".join(clauses)}
          AND (
              s.id IS NOT NULL OR NOT EXISTS (
                  SELECT 1 FROM workout_sets sx
                  WHERE sx.workout_exercise_id = we.id AND sx.completed = 1
              )
          )
        ORDER BY date(ws.date), COALESCE(ws.start_time, ''), we.id,
                 COALESCE(s.set_number, 0), s.id
        """,
        tuple(params),
    )
    result: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["sets"] = int(_number(item.get("sets")))
        item["reps"] = _number(item.get("reps"))
        item["weight"] = _number(item.get("weight"))
        item["volume"] = _row_volume(item["sets"], item["reps"], item["weight"])
        item["estimated_1rm"] = estimated_1rm(item["weight"], item["reps"])
        result.append(item)
    return result


async def _fetch_sessions(
    user_id: int,
    days: int | None = None,
    start: str | None = None,
    end: str | None = None,
) -> list[dict[str, Any]]:
    clauses = ["user_id = ?"]
    params: list[Any] = [user_id]
    if start and end:
        clauses.append("date(date) BETWEEN date(?) AND date(?)")
        params.extend([start, end])
    elif days is not None:
        clauses.append("date(date) >= date('now', ?)")
        params.append(f"-{days - 1} days")
    return await db.fetch_all(
        f"""
        SELECT id, date, start_time, end_time, notes
        FROM workout_sessions
        WHERE {" AND ".join(clauses)}
        ORDER BY date(date), COALESCE(start_time, '')
        """,
        tuple(params),
    )


async def fetch_volume_by_date(
    user_id: int, start: str, end: str
) -> list[dict[str, Any]]:
    return await db.fetch_all(
        f"""
        SELECT ws.date AS workout_date,
               COUNT(DISTINCT ws.id) AS workout_count,
               COALESCE(SUM({EXERCISE_VOLUME_SQL}), 0) AS total_volume
        FROM workout_sessions ws
        LEFT JOIN workout_exercises we ON we.session_id = ws.id
        WHERE ws.user_id = ? AND date(ws.date) BETWEEN date(?) AND date(?)
        GROUP BY ws.date
        ORDER BY ws.date
        """,
        (user_id, start, end),
    )


async def fetch_range_totals(user_id: int, start: str, end: str) -> dict[str, Any]:
    row = await db.fetch_one(
        f"""
        SELECT COUNT(DISTINCT ws.id) AS count,
               COALESCE(SUM({EXERCISE_VOLUME_SQL}), 0) AS volume
        FROM workout_sessions ws
        LEFT JOIN workout_exercises we ON we.session_id = ws.id
        WHERE ws.user_id = ? AND date(ws.date) BETWEEN date(?) AND date(?)
        """,
        (user_id, start, end),
    )
    return {
        "count": int(_number(row["count"] if row else 0)),
        "volume": _number(row["volume"] if row else 0),
    }


async def fetch_day_exercises(user_id: int, day: str) -> list[dict[str, Any]]:
    rows = await db.fetch_all(
        f"""
        SELECT we.id, we.exercise_name, we.sets, we.reps, we.weight,
               we.completed, ws.start_time AS time, ws.id AS session_id,
               {EXERCISE_VOLUME_SQL} AS volume
        FROM workout_sessions ws
        JOIN workout_exercises we ON we.session_id = ws.id
        WHERE ws.user_id = ? AND date(ws.date) = date(?)
        ORDER BY ws.start_time, we.order_num, we.id
        """,
        (user_id, day),
    )
    result = []
    for row in rows:
        item = dict(row)
        item["volume"] = _number(item.get("volume"))
        item["sets"] = int(_number(item.get("sets")))
        item["reps"] = _number(item.get("reps"))
        item["weight"] = _number(item.get("weight"))
        result.append(item)
    return result


def format_exercise_history_line(
    name: str,
    set_reps: list[int],
    aggregate_sets: Any,
    aggregate_reps: Any,
) -> str:
    """Show integer reps; mixed sets are listed instead of a float average."""
    if set_reps:
        count = len(set_reps)
        if len(set(set_reps)) == 1:
            return f"{name} {count}×{set_reps[0]}"
        return f"{name} {'/'.join(str(value) for value in set_reps)}"
    sets = int(_number(aggregate_sets))
    reps = int(round(_number(aggregate_reps)))
    return f"{name} {sets}×{reps}"


async def fetch_session_history(user_id: int, limit: int = 10) -> list[dict[str, Any]]:
    sessions = await db.fetch_all(
        f"""
        SELECT ws.id, ws.date, ws.start_time,
               COALESCE(SUM({EXERCISE_VOLUME_SQL}), 0) AS volume
        FROM workout_sessions ws
        JOIN workout_exercises we ON we.session_id = ws.id
        WHERE ws.user_id = ?
        GROUP BY ws.id
        HAVING COUNT(we.id) > 0
        ORDER BY ws.date DESC, ws.start_time DESC, ws.id DESC
        LIMIT ?
        """,
        (user_id, limit),
    )
    if not sessions:
        return []

    session_ids = [row["id"] for row in sessions]
    placeholders = ",".join("?" * len(session_ids))
    exercises = await db.fetch_all(
        f"""
        SELECT id, session_id, exercise_name, sets, reps
        FROM workout_exercises
        WHERE session_id IN ({placeholders})
        ORDER BY order_num ASC, id ASC
        """,
        tuple(session_ids),
    )
    set_rows = await db.fetch_all(
        f"""
        SELECT s.workout_exercise_id, s.reps
        FROM workout_sets s
        JOIN workout_exercises we ON we.id = s.workout_exercise_id
        WHERE we.session_id IN ({placeholders})
        ORDER BY s.set_number ASC, s.id ASC
        """,
        tuple(session_ids),
    )
    reps_by_exercise: dict[int, list[int]] = defaultdict(list)
    for row in set_rows:
        reps_by_exercise[row["workout_exercise_id"]].append(int(row["reps"] or 0))

    lines_by_session: dict[int, list[str]] = defaultdict(list)
    for exercise in exercises:
        lines_by_session[exercise["session_id"]].append(
            format_exercise_history_line(
                exercise["exercise_name"],
                reps_by_exercise.get(exercise["id"], []),
                exercise.get("sets"),
                exercise.get("reps"),
            )
        )

    result = []
    for session in sessions:
        item = dict(session)
        item["exercises"] = "\n".join(lines_by_session.get(session["id"], []))
        item["volume"] = _number(item.get("volume"))
        result.append(item)
    return result


async def fetch_week_journal(user_id: int, start: str, end: str) -> list[dict[str, Any]]:
    return await db.fetch_all(
        f"""
        SELECT ws.date,
               COUNT(we.id) AS exercises_count,
               COALESCE(SUM({EXERCISE_VOLUME_SQL}), 0) AS total_volume,
               SUM(CASE WHEN we.completed = TRUE THEN 1 ELSE 0 END) AS completed_count
        FROM workout_sessions ws
        LEFT JOIN workout_exercises we ON we.session_id = ws.id
        WHERE ws.user_id = ? AND date(ws.date) BETWEEN date(?) AND date(?)
        GROUP BY ws.date
        ORDER BY ws.date DESC
        """,
        (user_id, start, end),
    )


async def _fetch_muscle_map() -> dict[str, list[tuple[str, float]]]:
    try:
        rows = await db.fetch_all(
            """
            SELECT em.exercise_name AS exercise_name, m.name AS muscle_name,
                   COALESCE(em.contribution, 1.0) AS factor
            FROM exercise_muscles em
            JOIN muscles m ON m.id = em.muscle_id
            """
        )
        alias_rows = await db.fetch_all(
            """
            SELECT e.alias AS exercise_name, m.name AS muscle_name,
                   COALESCE(em.contribution, 1.0) AS factor
            FROM exercises e
            JOIN exercise_muscles em
              ON lower(replace(e.name, 'ё', 'е')) = lower(replace(em.exercise_name, 'ё', 'е'))
            JOIN muscles m ON m.id = em.muscle_id
            WHERE e.alias IS NOT NULL AND trim(e.alias) != ''
            """
        )
    except Exception:
        return {}
    mapping: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for row in list(rows) + list(alias_rows):
        key = _norm(row.get("exercise_name", ""))
        if not key:
            continue
        mapping[key].append(
            (str(row.get("muscle_name") or UNDEFINED_MUSCLE), _number(row.get("factor")) or 1.0)
        )
    return dict(mapping)


def _muscles_for(name: str, muscle_map: dict[str, list[tuple[str, float]]]) -> list[tuple[str, float]]:
    return muscle_map.get(_norm(name)) or [(UNDEFINED_MUSCLE, 1.0)]


async def _weekly_goal(user_id: int) -> int:
    settings = await db.fetch_one(
        "SELECT weekly_workout_goal FROM user_settings WHERE user_id = ?",
        (user_id,),
    )
    goal = int(_number(settings.get("weekly_workout_goal") if settings else DEFAULT_WEEKLY_GOAL))
    return goal if goal > 0 else DEFAULT_WEEKLY_GOAL


async def fetch_free_progress_block(user_id: int) -> dict[str, Any]:
    """Free 30-day overview."""
    sessions = await _fetch_sessions(user_id, 30)
    history = await fetch_canonical_history(user_id, 30)
    muscle_map = await _fetch_muscle_map()
    activity_dates = [d for row in sessions if (d := _parse_date(row.get("date")))]
    durations = [
        value
        for row in sessions
        if (value := _duration_minutes(row.get("start_time"), row.get("end_time"))) > 0
    ]
    latest = sessions[-1] if sessions else None
    latest_history = [
        row for row in history if latest and row["session_id"] == latest["id"]
    ]
    latest_muscles = []
    for row in latest_history:
        for muscle, _factor in _muscles_for(row["exercise_name"], muscle_map):
            if muscle != UNDEFINED_MUSCLE and muscle not in latest_muscles:
                latest_muscles.append(muscle)
    if not latest_muscles:
        latest_muscles = list(dict.fromkeys(
            row["exercise_name"] for row in latest_history if row.get("exercise_name")
        ))
    return {
        "period_days": 30,
        "total_sessions": len({row["id"] for row in sessions}),
        "active_days": len(set(activity_dates)),
        "current_streak": _current_streak(activity_dates),
        "exercise_count": len({row["workout_exercise_id"] for row in history}),
        "total_volume": sum(row["volume"] for row in history),
        "average_duration": round(sum(durations) / len(durations)) if durations else 0,
        "latest_workout": {
            "date": str(latest["date"])[:10],
            "label": " + ".join(latest_muscles[:4]) or "Тренировка",
            "exercise_names": latest_muscles,
        } if latest else None,
        "recent_exercises": [
            f"• {row['exercise_name']} ({str(row['date'])[:10]})"
            for row in list({
                row["exercise_name"]: row
                for row in reversed(history)
                if row.get("exercise_name")
            }.values())[:5]
        ],
    }


def _best_sets(rows: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    best: dict[str, dict[str, Any]] = {}
    counts: dict[str, int] = defaultdict(int)
    seen_exercises: dict[str, set] = defaultdict(set)
    for row in rows:
        name = str(row.get("exercise_name") or "")
        if not name:
            continue
        exercise_id = row.get("workout_exercise_id")
        if exercise_id not in seen_exercises[name]:
            seen_exercises[name].add(exercise_id)
            counts[name] += 1
        candidate = {
            "name": name,
            "weight": _number(row.get("weight")),
            "reps": _number(row.get("reps")),
            "estimated_1rm": _number(row.get("estimated_1rm")),
            "date": str(row.get("date") or "")[:10],
            "volume": _number(row.get("volume")),
        }
        current = best.get(name)
        if current is None or (
            candidate["estimated_1rm"], candidate["weight"], candidate["reps"]
        ) > (current["estimated_1rm"], current["weight"], current["reps"]):
            best[name] = candidate
    for name, item in best.items():
        item["times"] = counts[name]
    return best


async def fetch_premium_analytics(user_id: int, days: int = 30) -> dict[str, Any]:
    """Build strength, volume, muscle, regularity, and PR blocks."""
    if days not in VALID_PERIODS:
        raise ValueError(f"period must be one of {VALID_PERIODS}")
    history = await fetch_canonical_history(user_id, days, include_previous=True)
    sessions = await _fetch_sessions(user_id, max(days * 2, 90))
    today = local_today()
    current_start = today - timedelta(days=days - 1)
    previous_start = current_start - timedelta(days=days)

    def in_range(value: Any, start: date, end: date) -> bool:
        parsed = _parse_date(value)
        return parsed is not None and start <= parsed <= end

    current = [r for r in history if in_range(r.get("date"), current_start, today)]
    previous = [
        r for r in history
        if in_range(r.get("date"), previous_start, current_start - timedelta(days=1))
    ]
    current_sessions = [
        row for row in sessions if in_range(row.get("date"), current_start, today)
    ]

    current_best = _best_sets(current)
    previous_best = _best_sets(previous)
    all_best = _best_sets(await fetch_canonical_history(user_id))
    strength = []
    for name, item in sorted(
        current_best.items(), key=lambda pair: pair[1]["estimated_1rm"], reverse=True
    ):
        previous_item = previous_best.get(name, {})
        previous_weight = _number(previous_item.get("weight"))
        lifetime = all_best.get(name, {})
        is_pr = bool(
            lifetime
            and item["weight"] >= _number(lifetime.get("weight"))
            and item["reps"] >= _number(lifetime.get("reps"))
            and item["date"] == lifetime.get("date")
        )
        strength.append(
            {
                "name": name,
                "weight": item["weight"],
                "reps": item["reps"],
                "max_weight": item["weight"],
                "estimated_1rm": item["estimated_1rm"],
                "previous_max": previous_weight,
                "change": item["weight"] - previous_weight,
                "times": item["times"],
                "date": item["date"],
                "is_pr": is_pr,
            }
        )

    current_volume = sum(r["volume"] for r in current)
    previous_volume = sum(r["volume"] for r in previous)
    volume_change_pct = (
        (current_volume - previous_volume) * 100.0 / previous_volume
        if previous_volume > 0 else None
    )

    muscle_map = await _fetch_muscle_map()
    muscle_vol: dict[str, float] = defaultdict(float)
    category_vol = defaultdict(float)
    for row in current:
        volume = row["volume"]
        if volume <= 0:
            continue
        category_vol[exercise_push_pull_legs(row["exercise_name"])] += volume
        mapped = _muscles_for(row["exercise_name"], muscle_map)
        factor_total = sum(factor for _, factor in mapped) or 1.0
        for muscle, factor in mapped:
            muscle_vol[muscle] += volume * factor / factor_total

    muscle_total = sum(muscle_vol.values())
    muscle_load = [
        {
            "name": name,
            "volume": volume,
            "pct": (volume * 100.0 / muscle_total) if muscle_total else 0.0,
        }
        for name, volume in sorted(muscle_vol.items(), key=lambda item: item[1], reverse=True)
    ]
    insight = None
    upper = sum(
        item["volume"] for item in muscle_load
        if item["name"] in {"Грудь", "Спина", "Плечи", "Бицепс", "Трицепс", "Предплечья"}
    )
    legs = sum(
        item["volume"] for item in muscle_load
        if item["name"] in {"Квадрицепс", "Бицепс бедра", "Ягодицы", "Икры"}
    )
    if muscle_total > 0 and days >= 21 and legs < muscle_total * 0.18 and upper > legs:
        insight = "За выбранный период ноги получают заметно меньше нагрузки, чем верх тела."

    weekly_goal = await _weekly_goal(user_id)
    session_dates = sorted({
        parsed for row in current_sessions
        if (parsed := _parse_date(row.get("date"))) is not None
    })
    average_per_week = len({row["id"] for row in current_sessions}) / max(1.0, days / 7.0)
    goal_pct = min(100.0, average_per_week * 100.0 / weekly_goal) if weekly_goal else None

    month_sessions: dict[tuple[int, int], set[date]] = defaultdict(set)
    lookback_sessions = [
        row for row in sessions
        if in_range(row.get("date"), today - timedelta(days=89), today)
    ]
    for row in lookback_sessions:
        parsed = _parse_date(row.get("date"))
        if parsed is None:
            continue
        month_sessions[(parsed.year, parsed.month)].add(parsed)
    months = []
    cursor = date(today.year, today.month, 1)
    for _ in range(3):
        key = (cursor.year, cursor.month)
        days_in_month = (
            (date(cursor.year + (cursor.month == 12), cursor.month % 12 + 1, 1) - timedelta(days=1)).day
        )
        weeks_in_month = max(1.0, days_in_month / 7.0)
        count = len(month_sessions.get(key, set()))
        pct = min(100.0, (count / weeks_in_month) * 100.0 / weekly_goal) if weekly_goal else 0.0
        months.append({"name": _month_label(cursor), "pct": pct, "count": count})
        cursor = date(cursor.year if cursor.month > 1 else cursor.year - 1,
                      cursor.month - 1 if cursor.month > 1 else 12, 1)
    months.reverse()

    week_buckets: dict[tuple[int, int], list[date]] = defaultdict(list)
    for day in session_dates:
        iso = day.isocalendar()
        week_buckets[(iso.year, iso.week)].append(day)
    best_week = None
    if week_buckets:
        (year, week), _days = max(week_buckets.items(), key=lambda item: len(item[1]))
        start = date.fromisocalendar(year, week, 1)
        end = start + timedelta(days=6)
        best_week = f"{start.day:02d}.{start.month:02d}–{end.day:02d}.{end.month:02d}"
    gaps = [
        (session_dates[index] - session_dates[index - 1]).days
        for index in range(1, len(session_dates))
    ]
    avg_gap = round(sum(gaps) / len(gaps), 1) if gaps else None

    pr_list = [
        {
            "name": item["name"],
            "weight": item["weight"],
            "reps": item["reps"],
            "date": item["date"],
            "display": f"{format_kg(item['weight'], 0)} × {int(item['reps'])}",
        }
        for item in strength[:8]
    ]
    last_pr = None
    dated = [item for item in strength if item["is_pr"] and item["date"]]
    if dated:
        latest = max(dated, key=lambda item: item["date"])
        last_pr = {"name": latest["name"], "date": latest["date"], "display": f"{format_kg(latest['weight'], 0)} × {int(latest['reps'])}"}

    ppl_total = sum(category_vol.values())
    streak = _current_streak(session_dates)
    return {
        "period_days": days,
        "strength": strength,
        "volume": {
            "current": current_volume,
            "previous": previous_volume,
            "change_pct": volume_change_pct,
            "by_muscle": dict(muscle_vol),
        },
        "muscle_load": muscle_load,
        "muscle_insight": insight,
        "regularity": {
            "sessions": len({row["id"] for row in current_sessions}),
            "active_days": len(set(session_dates)),
            "active_weeks": len(week_buckets),
            "average_per_week": average_per_week,
            "weekly_goal": weekly_goal,
            "goal_pct": goal_pct,
            "current_streak": streak,
            "months": months,
            "average_pct": (
                round(sum(item["pct"] for item in months) / len(months), 0) if months else 0
            ),
            "best_week": best_week,
            "avg_gap_days": avg_gap,
        },
        "prs": pr_list,
        "last_pr": last_pr,
        "history": current,
        "current_streak": streak,
        "longest_streak": streak,
        "pr_list": pr_list,
        "push_v": category_vol["push"],
        "pull_v": category_vol["pull"],
        "legs_v": category_vol["legs"],
        "other_v": category_vol["other"],
        "ppl_total": ppl_total,
        "muscle_vol": dict(muscle_vol),
        "week_volume": current_volume if days == 7 else 0.0,
        "weeks_with_workouts": len(week_buckets),
    }


def format_ppl_percentages(
    push_v: float, pull_v: float, legs_v: float, other_v: float, total: float
) -> str:
    if total <= 0:
        return "Недостаточно данных с весом для баланса нагрузки."
    return "\n".join(
        f"▫️ {label}: *{100.0 * value / total:.0f}%*"
        for label, value in (
            ("Push", push_v), ("Pull", pull_v), ("Ноги", legs_v), ("Прочее", other_v)
        )
    )


def format_muscle_percentages(muscle_vol: dict[str, float]) -> str:
    total = sum(muscle_vol.values())
    if total <= 0:
        return "Недостаточно данных для разбивки по мышцам."
    return "\n".join(
        f"{progress_bar(100.0 * volume / total)}  {100.0 * volume / total:.0f}%  {name}"
        for name, volume in sorted(muscle_vol.items(), key=lambda item: item[1], reverse=True)
    )
