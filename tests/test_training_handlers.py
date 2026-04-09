from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from handlers import training as training_handlers


class FakeState:
    def __init__(self):
        self.data = {}
        self.state = None

    async def set_state(self, state):
        self.state = state

    async def update_data(self, **kwargs):
        self.data.update(kwargs)

    async def get_data(self):
        return self.data

    async def clear(self):
        self.data = {}
        self.state = None


def _message(text: str, user_id: int = 10):
    return SimpleNamespace(
        text=text,
        from_user=SimpleNamespace(id=user_id),
        answer=AsyncMock(),
    )


def _callback(data: str, user_id: int = 10):
    return SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
    )


@pytest.mark.asyncio
async def test_training_journal_menu():
    callback = _callback("training_journal")
    await training_handlers.training_journal(callback)
    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_exercise_name_cancel():
    state = FakeState()
    message = _message("/cancel")
    await training_handlers.process_exercise_name(message, state)
    message.answer.assert_awaited_once()
    assert state.state is None


@pytest.mark.asyncio
async def test_process_exercise_name_success():
    state = FakeState()
    message = _message("Жим лежа")
    await training_handlers.process_exercise_name(message, state)
    assert state.data["exercise_name"] == "Жим лежа"


@pytest.mark.asyncio
async def test_my_exercises_with_data(monkeypatch):
    async def fake_fetch_all(query, params):
        return [{"name": "Жим лежа", "alias": "Жим"}]

    monkeypatch.setattr(training_handlers.db, "fetch_all", fake_fetch_all)
    callback = _callback("my_exercises")
    await training_handlers.my_exercises(callback)
    callback.message.edit_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_sets_invalid_then_valid():
    state = FakeState()
    bad = _message("abc")
    await training_handlers.process_sets(bad, state)
    bad.answer.assert_awaited_once()

    good = _message("3")
    await training_handlers.process_sets(good, state)
    assert state.data["sets"] == 3


@pytest.mark.asyncio
async def test_process_exercise_alias_skip_and_save(monkeypatch):
    calls = []

    async def fake_execute(query, params):
        calls.append((query, params))

    monkeypatch.setattr(training_handlers.db, "execute", fake_execute)

    state = FakeState()
    await state.update_data(exercise_name="Присед")
    message = _message("-")

    await training_handlers.process_exercise_alias(message, state)

    assert calls
    assert state.state is None
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_reps_invalid_then_valid():
    state = FakeState()
    bad = _message("NaN")
    await training_handlers.process_reps(bad, state)
    bad.answer.assert_awaited_once()

    good = _message("12")
    await training_handlers.process_reps(good, state)
    assert state.data["reps"] == 12


@pytest.mark.asyncio
async def test_process_weight_saves_workout(monkeypatch):
    calls = []

    async def fake_execute(query, params):
        calls.append((query, params))

    monkeypatch.setattr(training_handlers.db, "execute", fake_execute)

    state = FakeState()
    await state.update_data(exercise="Жим", sets=3, reps=10)
    message = _message("-", user_id=77)

    await training_handlers.process_weight(message, state)

    assert calls
    assert calls[0][1][0] == 77
    assert state.state is None
    message.answer.assert_awaited_once()


@pytest.mark.asyncio
async def test_workout_history_empty(monkeypatch):
    async def fake_fetch_all(query, params):
        return []

    monkeypatch.setattr(training_handlers.db, "fetch_all", fake_fetch_all)
    callback = _callback("workout_history")

    await training_handlers.workout_history(callback)
    callback.message.edit_text.assert_awaited_once()

