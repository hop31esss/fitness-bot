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

