from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from handlers import start as start_handlers


def _fake_callback(data: str, user_id: int = 1001, first_name: str = "Test"):
    message = SimpleNamespace(edit_text=AsyncMock())
    callback = SimpleNamespace(
        data=data,
        from_user=SimpleNamespace(id=user_id, first_name=first_name),
        message=message,
        answer=AsyncMock(),
    )
    return callback


@pytest.mark.asyncio
async def test_start_payload_has_open_full_menu_button(monkeypatch):
    async def fake_fetch_one(query, params):
        if "COUNT" in query:
            return {"cnt": 0}
        return {"current_streak": 5}

    monkeypatch.setattr(start_handlers.db, "fetch_one", fake_fetch_one)

    text, markup = await start_handlers.build_start_payload(1, "Ivan")
    assert "Сегодня" in text
    buttons = [b.text for row in markup.inline_keyboard for b in row]
    assert "📋 Открыть всё меню" in buttons


@pytest.mark.asyncio
async def test_open_full_menu_shows_4_items_and_back():
    callback = _fake_callback("back_to_main")
    await start_handlers.back_to_main(callback)

    callback.answer.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    _, kwargs = callback.message.edit_text.await_args
    labels = [b.text for row in kwargs["reply_markup"].inline_keyboard for b in row]
    assert "📘 Журнал тренировок" in labels
    assert "📔 Дневник тренировок" in labels
    assert "📚 Мои программы" in labels
    assert "💪 Упражнения" in labels
    assert labels[-1] == "🔙 Назад"


@pytest.mark.asyncio
async def test_open_sub_menu_from_full_menu():
    callback = _fake_callback("full_menu_open_sub")
    await start_handlers.full_menu_open_sub(callback)

    callback.message.edit_text.assert_awaited_once()
    _, kwargs = callback.message.edit_text.await_args
    assert "Разделы" in kwargs["text"]
    labels = [b.text for row in kwargs["reply_markup"].inline_keyboard for b in row]
    assert labels[-1] == "🔙 Назад"


@pytest.mark.asyncio
async def test_open_journal_section_and_back_button_present():
    callback = _fake_callback("full_section_journal")
    await start_handlers.full_section_journal(callback)

    callback.message.edit_text.assert_awaited_once()
    _, kwargs = callback.message.edit_text.await_args
    labels = [b.text for row in kwargs["reply_markup"].inline_keyboard for b in row]
    assert labels == ["🔙 Назад"]


@pytest.mark.asyncio
async def test_back_to_start_edits_message(monkeypatch):
    callback = _fake_callback("full_menu_back_to_start")

    async def fake_build_start_payload(user_id, first_name):
        markup = start_handlers.build_section_back_menu().as_markup()
        return "START SCREEN", markup

    monkeypatch.setattr(start_handlers, "build_start_payload", fake_build_start_payload)
    await start_handlers.full_menu_back_to_start(callback)

    callback.message.edit_text.assert_awaited_once()
    args, _ = callback.message.edit_text.await_args
    assert args[0] == "START SCREEN"

