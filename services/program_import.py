"""Parse a pasted workout program into template exercises."""
from __future__ import annotations

import json
import re
from typing import Any

_SKIP = re.compile(
    r"^(?:день|day|тренировка|разминка|заминка|warmup|cooldown)\b",
    re.IGNORECASE,
)
_BULLET = re.compile(r"^(?:[\s•·▪◦●\-–—*]+|\d+[\.\)\:]\s*)+")
_STATS = re.compile(
    r"(?P<sets>\d{1,2})\s*[xх×*]\s*(?P<reps>\d{1,3})"
    r"(?:\s*[-–—/]\s*(?P<reps_max>\d{1,3}))?",
    re.IGNORECASE,
)
_ALT_STATS = re.compile(
    r"(?P<sets>\d{1,2})\s*(?:подход(?:а|ов)?|sets?)\s+"
    r"(?:по\s+)?(?P<reps>\d{1,3})"
    r"(?:\s*[-–—/]\s*(?P<reps_max>\d{1,3}))?",
    re.IGNORECASE,
)
_WEIGHT = re.compile(
    r"(?:по\s+)?(?P<weight>\d+(?:[.,]\d+)?)\s*(?:кг|kg)\b",
    re.IGNORECASE,
)
_WEIGHT_BARE = re.compile(r"(?:@|по)?\s*(?P<weight>\d+(?:[.,]\d+)?)\s*$")


def _clean_name(name: str) -> str:
    cleaned = _BULLET.sub("", str(name or ""))
    return re.sub(r"\s+", " ", cleaned).strip(" :-–—\t•·▪◦●*")


def _item(name: str, sets: Any, reps: Any, weight: Any, reps_max: Any = None) -> dict[str, Any] | None:
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
    item = {
        "name": cleaned[:80],
        "type": "strength",
        "sets": set_count,
        "reps": rep_count,
        "weight": parsed_weight,
    }
    try:
        max_reps = int(reps_max) if reps_max not in (None, "") else None
    except (TypeError, ValueError):
        max_reps = None
    if max_reps and max_reps != rep_count:
        item["reps_max"] = max_reps
    return item


def _weight_from(text: str) -> str | None:
    match = _WEIGHT.search(text or "")
    if match:
        return match.group("weight")
    match = _WEIGHT_BARE.search((text or "").strip())
    return match.group("weight") if match else None


def parse_program_line(line: str) -> dict[str, Any] | None:
    stripped = (line or "").strip()
    if not stripped or stripped.startswith(("#", "//")):
        return None
    if re.fullmatch(r"[-*=~_]{3,}", stripped) or _SKIP.match(_clean_name(stripped) or stripped):
        return None
    prepared = _BULLET.sub("", stripped).strip()
    match = _STATS.search(prepared) or _ALT_STATS.search(prepared)
    if not match:
        return None
    name = prepared[: match.start()]
    rest = prepared[match.end() :]
    return _item(
        name,
        match.group("sets"),
        match.group("reps"),
        _weight_from(rest) or _weight_from(prepared),
        match.groupdict().get("reps_max"),
    )


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
            item.get("reps_max"),
        )
        if parsed:
            exercises.append(parsed)
    return exercises


def suggested_program_name(text: str) -> str | None:
    for raw in (text or "").splitlines():
        line = _clean_name(raw)
        if not line:
            continue
        if parse_program_line(raw) or _SKIP.match(line):
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
        parsed = parse_program_line(line)
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
        reps = int(item.get("reps") or 0)
        reps_max = item.get("reps_max")
        try:
            reps_max = int(reps_max) if reps_max not in (None, "") else None
        except (TypeError, ValueError):
            reps_max = None
        reps_text = f"{reps}–{reps_max}" if reps_max and reps_max != reps else str(reps)
        lines.append(
            f"{index}. {item.get('name')} — {int(item.get('sets') or 0)}×{reps_text} ({weight_text})"
        )
    return "\n".join(lines)
