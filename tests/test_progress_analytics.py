from datetime import date, timedelta

import pytest

from database import base
from handlers import workout_session
from services import progress_analytics as analytics


@pytest.fixture
async def isolated_db(tmp_path, monkeypatch):
    database = base.Database()
    database.db_path = str(tmp_path / "analytics.sqlite3")
    monkeypatch.setattr(base, "db", database)
    monkeypatch.setattr(analytics, "db", database)
    monkeypatch.setattr(workout_session, "db", database)
    await database.connect()
    await base.create_tables()
    yield database
    await database.close()


async def _user(db, user_id=1):
    await db.execute("INSERT INTO users (user_id) VALUES (?)", (user_id,))
    await db.execute(
        "INSERT INTO user_settings (user_id, weekly_workout_goal) VALUES (?, ?)",
        (user_id, 3),
    )


@pytest.mark.asyncio
async def test_exact_sets_beat_aggregates_without_double_count(isolated_db):
    await _user(isolated_db)
    today = date.today().isoformat()
    cursor = await isolated_db.execute(
        "INSERT INTO workout_sessions (user_id, date) VALUES (?, ?)",
        (1, today),
    )
    session_id = cursor.lastrowid
    await workout_session.persist_session_exercises_from_state(
        session_id,
        [
            {
                "name": "Жим лёжа",
                "type": "strength",
                "sets": 2,
                "set_data": [
                    {"reps": 5, "weight": 100},
                    {"reps": 5, "weight": 100},
                ],
            }
        ],
    )
    history = await analytics.fetch_canonical_history(1, 30)
    assert sum(row["volume"] for row in history) == 1000
    assert {row["source"] for row in history} == {"exact"}


@pytest.mark.asyncio
async def test_aggregate_fallback_and_legacy_not_duplicated(isolated_db):
    await _user(isolated_db, 42)
    created = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d 10:00:00")
    await isolated_db.execute(
        """
        INSERT INTO workouts
            (user_id, exercise_name, sets, reps, weight, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (42, "Неизвестное движение", 3, 10, 50, created),
    )
    await base.migrate_legacy_workouts()
    await base.migrate_legacy_workouts()
    history = await analytics.fetch_canonical_history(42, 30)
    assert len(history) == 1
    assert history[0]["source"] == "aggregate"
    assert history[0]["volume"] == 1500
    sets = await isolated_db.fetch_all("SELECT * FROM workout_sets")
    assert sets == []


@pytest.mark.asyncio
async def test_unknown_exercise_maps_to_undefined(isolated_db):
    await _user(isolated_db)
    today = date.today().isoformat()
    cursor = await isolated_db.execute(
        "INSERT INTO workout_sessions (user_id, date) VALUES (?, ?)",
        (1, today),
    )
    await workout_session.persist_session_exercises_from_state(
        cursor.lastrowid,
        [
            {
                "name": "Совсем новое упражнение",
                "type": "strength",
                "sets": 1,
                "set_data": [{"reps": 8, "weight": 40}],
            }
        ],
    )
    data = await analytics.fetch_premium_analytics(1, 30)
    names = {item["name"] for item in data["muscle_load"]}
    assert names == {analytics.UNDEFINED_MUSCLE}


@pytest.mark.asyncio
async def test_catalog_maps_bench_and_1rm_formula(isolated_db):
    await _user(isolated_db)
    today = date.today().isoformat()
    cursor = await isolated_db.execute(
        "INSERT INTO workout_sessions (user_id, date) VALUES (?, ?)",
        (1, today),
    )
    await workout_session.persist_session_exercises_from_state(
        cursor.lastrowid,
        [
            {
                "name": "Жим лежа",
                "type": "strength",
                "sets": 1,
                "set_data": [{"reps": 6, "weight": 100}],
            }
        ],
    )
    data = await analytics.fetch_premium_analytics(1, 30)
    assert data["strength"][0]["estimated_1rm"] == pytest.approx(120)
    assert analytics.estimated_1rm(100, 6) == pytest.approx(120)
    muscle_names = {item["name"] for item in data["muscle_load"]}
    assert "Грудь" in muscle_names
    assert analytics.UNDEFINED_MUSCLE not in muscle_names


@pytest.mark.asyncio
async def test_weekly_goal_defaults_to_three(isolated_db):
    await isolated_db.execute("INSERT INTO users (user_id) VALUES (?)", (9,))
    data = await analytics.fetch_premium_analytics(9, 30)
    assert data["regularity"]["weekly_goal"] == 3


@pytest.mark.asyncio
async def test_bodyweight_zero_has_no_volume(isolated_db):
    await _user(isolated_db)
    today = date.today().isoformat()
    cursor = await isolated_db.execute(
        "INSERT INTO workout_sessions (user_id, date) VALUES (?, ?)",
        (1, today),
    )
    await workout_session.persist_session_exercises_from_state(
        cursor.lastrowid,
        [
            {
                "name": "Подтягивания",
                "type": "strength",
                "sets": 3,
                "set_data": [{"reps": 8, "weight": 0}] * 3,
            }
        ],
    )
    free = await analytics.fetch_free_progress_block(1)
    assert free["total_volume"] == 0
    assert free["exercise_count"] == 1


@pytest.mark.asyncio
async def test_lbs_converted_to_kg_on_write(isolated_db):
    await _user(isolated_db)
    await isolated_db.execute(
        "UPDATE user_settings SET units = 'lbs' WHERE user_id = ?",
        (1,),
    )
    today = date.today().isoformat()
    cursor = await isolated_db.execute(
        "INSERT INTO workout_sessions (user_id, date) VALUES (?, ?)",
        (1, today),
    )
    await workout_session.persist_session_exercises_from_state(
        cursor.lastrowid,
        [
            {
                "name": "Жим лежа",
                "type": "strength",
                "sets": 1,
                "set_data": [{"reps": 1, "weight": 100}],
            }
        ],
    )
    row = await isolated_db.fetch_one("SELECT weight FROM workout_sets")
    assert row["weight"] == pytest.approx(45.359237)
