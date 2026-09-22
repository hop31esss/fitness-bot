from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from handlers import start as start_handlers
from keyboards.main import get_main_keyboard


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
async def test_start_payload_has_open_hubs_button(monkeypatch):
    async def fake_fetch_one(query, params):
        if "COUNT" in query:
            return {"cnt": 0}
        return {"current_streak": 5}

    monkeypatch.setattr(start_handlers.db, "fetch_one", fake_fetch_one)

    text, markup = await start_handlers.build_start_payload(1, "Ivan")
    assert "Сегодня" in text
    buttons = [b.text for row in markup.inline_keyboard for b in row]
    assert "📋 Открыть разделы" in buttons
    assert "📊 Прогресс" in buttons


@pytest.mark.asyncio
async def test_open_full_menu_shows_hub_keyboard():
    callback = _fake_callback("back_to_main")
    await start_handlers.back_to_main(callback)

    callback.answer.assert_awaited_once()
    callback.message.edit_text.assert_awaited_once()
    _, kwargs = callback.message.edit_text.await_args
    labels = [b.text for row in kwargs["reply_markup"].inline_keyboard for b in row]
    assert "🏋️ ТРЕНИРОВКИ" in labels
    assert "📊 ПРОГРЕСС" in labels
    assert "🤖 AI-СОВЕТЫ" in labels
    assert "👤 ПРОФИЛЬ" in labels
    assert "💳 ПЛАТЕЖИ" not in labels
    assert "👑 ПРЕМИУМ" not in labels


def test_main_keyboard_has_four_hubs_only():
    labels = [b.text for row in get_main_keyboard().inline_keyboard for b in row]
    assert labels == ["🏋️ ТРЕНИРОВКИ", "📊 ПРОГРЕСС", "🤖 AI-СОВЕТЫ", "👤 ПРОФИЛЬ"]


@pytest.mark.asyncio
async def test_open_training_hub_from_legacy_callback():
    callback = _fake_callback("full_menu_open_sub")
    await start_handlers.menu_training(callback)

    callback.message.edit_text.assert_awaited_once()
    args, kwargs = callback.message.edit_text.await_args
    assert "Тренировки" in args[0]
    labels = [b.text for row in kwargs["reply_markup"].inline_keyboard for b in row]
    assert "🏋️ Начать тренировку" in labels
    assert "📔 Дневник" in labels
    assert "◀️ Разделы" in labels


@pytest.mark.asyncio
async def test_profile_hub_nests_monetization():
    callback = _fake_callback("menu_profile")
    await start_handlers.menu_profile(callback)
    _, kwargs = callback.message.edit_text.await_args
    labels = [b.text for row in kwargs["reply_markup"].inline_keyboard for b in row]
    assert "👑 Premium" in labels
    assert "💳 Оплата" in labels
    assert "🤝 Рефералы" in labels
    assert "⚙️ Настройки" in labels


@pytest.mark.asyncio
async def test_open_journal_section_delegates_to_training(monkeypatch):
    callback = _fake_callback("full_section_journal")

    async def fake_journal(cb):
        await cb.message.edit_text("JOURNAL", reply_markup=start_handlers.build_section_back_menu().as_markup())
        await cb.answer()

    monkeypatch.setattr("handlers.training.training_journal", fake_journal)
    await start_handlers.full_section_journal(callback)

    callback.message.edit_text.assert_awaited_once()
    args, _ = callback.message.edit_text.await_args
    assert args[0] == "JOURNAL"


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
