"""Server-local time helpers. Workout logs and reminders use this zone."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone as dt_timezone
from typing import Any

from config import SERVER_TIMEZONE

UTC = dt_timezone.utc
_MOSCOW = dt_timezone(timedelta(hours=3))
_FIXED_OFFSETS = {
    "UTC": UTC,
    "Etc/UTC": UTC,
    "Europe/Moscow": _MOSCOW,
    "Europe/Kirov": _MOSCOW,
    "Europe/Volgograd": _MOSCOW,
    "Europe/Simferopol": _MOSCOW,
}


def zone() -> Any:
    name = (SERVER_TIMEZONE or "Europe/Moscow").strip() or "Europe/Moscow"
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        pass
    try:
        import pytz
        return pytz.timezone(name)
    except Exception:
        pass
    return _FIXED_OFFSETS.get(name, _MOSCOW)


def now() -> datetime:
    return datetime.now(zone())


def today() -> date:
    return now().date()


def today_iso() -> str:
    return today().isoformat()


def now_hm() -> str:
    return now().strftime("%H:%M")


def normalize_hhmm(value: str | None, default: str = "18:00") -> str:
    raw = (value or default).strip()
    try:
        hours, minutes = raw.split(":", 1)
        return f"{int(hours):02d}:{int(minutes):02d}"
    except (TypeError, ValueError):
        return default


def same_hhmm(left: str | None, right: str | None) -> bool:
    return normalize_hhmm(left, default="") == normalize_hhmm(right, default="")
