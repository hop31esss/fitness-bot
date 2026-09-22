import pytest

from database import base
from handlers import workout_session


@pytest.fixture
async def isolated_db(tmp_path, monkeypatch):
    database = base.Database()
    database.db_path = str(tmp_path / "workouts.sqlite3")
    monkeypatch.setattr(base, "db", database)
    monkeypatch.setattr(workout_session, "db", database)
    await database.connect()
    yield database
    await database.close()


@pytest.mark.asyncio
async def test_schema_and_legacy_migration_are_idempotent(isolated_db):
    await base.create_tables()
    await isolated_db.execute(
        "INSERT INTO users (user_id) VALUES (?)",
        (42,),
    )
    await isolated_db.execute(
        """
        INSERT INTO workouts
            (user_id, exercise_name, sets, reps, weight, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (42, "Подтягивания", 3, 8, None, "2026-09-20 10:30:00"),
    )

    await base.create_tables()
    await base.create_tables()

    settings_columns = await isolated_db.fetch_all("PRAGMA table_info(user_settings)")
    weekly_goal = next(row for row in settings_columns if row["name"] == "weekly_workout_goal")
    assert weekly_goal["dflt_value"] == "3"
    assert base.canonical_muscle_slug("дельтовидные") == "shoulders"
    assert base.canonical_muscle_slug("not in catalog") == "undefined"

    sessions = await isolated_db.fetch_all(
        "SELECT * FROM workout_sessions WHERE source_table = 'workouts'"
    )
    exercises = await isolated_db.fetch_all(
        "SELECT * FROM workout_exercises WHERE source_table = 'workouts'"
    )
    sets = await isolated_db.fetch_all("SELECT * FROM workout_sets")
    assert len(sessions) == len(exercises) == 1
    assert sets == []
    assert exercises[0]["weight"] == 0.0


@pytest.mark.asyncio
async def test_exact_sets_survive_rewrite_and_aggregate_fallback(isolated_db):
    await base.create_tables()
    await isolated_db.execute("INSERT INTO users (user_id) VALUES (?)", (7,))
    cursor = await isolated_db.execute(
        "INSERT INTO workout_sessions (user_id, date) VALUES (?, ?)",
        (7, "2026-09-22"),
    )
    session_id = cursor.lastrowid
    exercises = [
        {
            "name": "Жим лёжа",
            "type": "strength",
            "sets": 3,
            "set_data": [
                {"reps": 10, "weight": 40},
                {"reps": 8, "weight": 45},
                {"reps": 6, "weight": 0},
            ],
        }
    ]

    await workout_session.persist_session_exercises_from_state(session_id, exercises)
    await workout_session.persist_session_exercises_from_state(session_id, exercises)

    rows = await isolated_db.fetch_all(
        """
        SELECT ws.set_number, ws.reps, ws.weight
        FROM workout_sets ws
        JOIN workout_exercises we ON we.id = ws.workout_exercise_id
        WHERE we.session_id = ?
        ORDER BY ws.set_number
        """,
        (session_id,),
    )
    aggregate = await isolated_db.fetch_one(
        "SELECT sets, reps, weight FROM workout_exercises WHERE session_id = ?",
        (session_id,),
    )
    assert [(row["reps"], row["weight"]) for row in rows] == [
        (10, 40.0),
        (8, 45.0),
        (6, 0.0),
    ]
    assert aggregate == {"sets": 3, "reps": 8, "weight": pytest.approx(85 / 3)}
