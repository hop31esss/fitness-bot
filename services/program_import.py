"""Parse a pasted workout program into template exercises."""
from __future__ import annotations

import json
import re
from typing import Any

_LINE = re.compile(
    r"""
    ^\s*
    (?:\d+[\.\)\:]\s*)?
    (?P<name>[^0-9\n][^:\n]*?)
    \s*[:\-–]?\s*
    (?P<sets>\d{1,2})
    \s*[xх×*]+\s*
    (?P<reps>\d{1,3})
    (?:\s*[-–/]\s*\d{1,3})?
    (?:\s*(?:повт(?:орен(?:ий|ия))?|reps?))?
    (?:\s*(?:@|по)?\s*(?P<weight>\d+(?:[.,]\d+)?)(?:\s*кг|kg)?)?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

_ALT = re.compile(
    r"""
    ^\s*(?:\d+[\.\)\:]\s*)?
    (?P<name>.+?)\s+
    (?P<sets>\d{1,2})\s*(?:подход(?:а|ов)?|sets?)\s+
    (?:по\s+)?(?P<reps>\d{1,3})
    (?:\s*[-–/]\s*\d{1,3})?
    (?:\s*(?:повт(?:орен(?:ий|ия))?|reps?))?
    (?:\s*(?P<weight>\d+(?:[.,]\d+)?)(?:\s*кг|kg)?)?
    \s*$
    """,
    re.IGNORECASE | re.VERBOSE,
)

_SKIP = re.compile(
    r"^(?:день|day|тренировка|разминка|заминка|warmup|cooldown)\b",
    re.IGNORECASE,
)


def _clean_name(name: str) -> str:
    return re.sub(r"\s+", " ", name).strip(" :-–—\t")


def _item(name: str, sets: Any, reps: Any, weight: Any) -> dict[str, Any] | None:
    cleaned = _clean_name(str(name or ""))
    if not cleaned or len(cleaned) < 2:
        return None
    try:
        set_count = int(sets)
        rep_count = int(float(str(reps).replace(",", ".")))
    except (TypeError, ValueError):
        return None
    if set_count <= 0 or rep_count <= 0:
        return None
    parsed_weight = None
    if weight not in (None, "", "-"):
        try:
            parsed_weight = float(str(weight).replace(",", "."))
        except (TypeError, ValueError):
            parsed_weight = None
    return {
        "name": cleaned[:80],
        "type": "strength",
        "sets": set_count,
        "reps": rep_count,
        "weight": parsed_weight,
    }


def _from_json(text: str) -> list[dict[str, Any]]:
    payload = json.loads(text)
    raw_items = payload
    if isinstance(payload, dict):
        raw_items = payload.get("exercises") or payload.get("program") or []
    if not isinstance(raw_items, list):
        return []
    exercises = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        parsed = _item(
            item.get("name") or item.get("exercise"),
            item.get("sets"),
            item.get("reps"),
            item.get("weight"),
        )
        if parsed:
            exercises.append(parsed)
    return exercises


def suggested_program_name(text: str) -> str | None:
    for raw in (text or "").splitlines():
        line = raw.strip().strip("#*")
        if not line:
            continue
        if _LINE.match(line) or _ALT.match(line) or _SKIP.match(line):
            continue
        if re.fullmatch(r"[-*=~_]{3,}", line):
            continue
        return line[:60]
    return None


def parse_program_text(text: str) -> list[dict[str, Any]]:
    raw = (text or "").strip()
    if not raw:
        return []
    if raw.startswith(("{", "[")):
        try:
            parsed = _from_json(raw)
            if parsed:
                return parsed
        except json.JSONDecodeError:
            pass

    exercises: list[dict[str, Any]] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith(("#", "//")):
            continue
        if re.fullmatch(r"[-*=~_]{3,}", stripped) or _SKIP.match(stripped):
            continue
        match = _LINE.match(stripped) or _ALT.match(stripped)
        if not match:
            continue
        parsed = _item(
            match.group("name"),
            match.group("sets"),
            match.group("reps"),
            match.groupdict().get("weight"),
        )
        if parsed:
            exercises.append(parsed)
    return exercises


def format_template_exercises(exercises: list[dict[str, Any]]) -> str:
    lines = []
    for index, item in enumerate(exercises, 1):
        if item.get("type") != "strength":
            lines.append(f"{index}. {item.get('name')}")
            continue
        weight = item.get("weight")
        weight_text = f"{weight:g} кг" if weight else "б/в"
        lines.append(
            f"{index}. {item.get('name')} — {int(item.get('sets') or 0)}×{int(item.get('reps') or 0)} ({weight_text})"
        )
    return "\n".join(lines)
