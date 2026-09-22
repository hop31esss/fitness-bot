from services.program_import import (
    format_template_exercises,
    parse_program_text,
    suggested_program_name,
)
from utils.clock import normalize_hhmm, same_hhmm
from handlers.workout_session import planned_to_live_exercise
from services.progress_analytics import format_exercise_history_line


def test_parse_common_paste_formats():
    text = """
    Ноги тяжёлые
    День 1
    1. Присед 4x8 100
    Румынская тяга 3×10
    Разгибание 4 подхода по 12
    Гиперэкстензия 3x12
    """
    exercises = parse_program_text(text)
    assert [item["name"] for item in exercises] == [
        "Присед",
        "Румынская тяга",
        "Разгибание",
        "Гиперэкстензия",
    ]
    assert exercises[0]["sets"] == 4
    assert exercises[0]["reps"] == 8
    assert exercises[0]["weight"] == 100
    assert suggested_program_name(text) == "Ноги тяжёлые"
    rendered = format_template_exercises(exercises)
    assert "4×8" in rendered
    assert "100 кг" in rendered


def test_parse_json_program():
    exercises = parse_program_text(
        '{"name": "Push", "exercises": [{"name": "Жим лежа", "sets": 5, "reps": 5, "weight": 80}]}'
    )
    assert exercises == [
        {"name": "Жим лежа", "type": "strength", "sets": 5, "reps": 5, "weight": 80.0}
    ]


def test_planned_to_live_has_integer_set_data():
    live = planned_to_live_exercise({"name": "Присед", "sets": 3, "reps": 8, "weight": 100})
    assert live["set_data"] == [
        {"reps": 8, "weight": 100.0, "weight_done": True}
    ] * 3
    assert live["reps_display"] == "8"


def test_history_line_uses_sets_not_average():
    assert format_exercise_history_line("Присед", [8, 10, 8], 3, 8.666) == "Присед 8/10/8"
    assert format_exercise_history_line("Гиперэкстензия", [12, 12, 12], 3, 12) == "Гиперэкстензия 3×12"
    assert format_exercise_history_line("Разгибание", [], 4, 12.75) == "Разгибание 4×13"


def test_time_normalization():
    assert normalize_hhmm("9:5") == "09:05"
    assert same_hhmm("9:00", "09:00")
    assert not same_hhmm("18:00", "18:01")
