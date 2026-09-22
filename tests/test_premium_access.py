from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from handlers.premium import build_premium_screen, show_premium_info
from services import premium_access


@pytest.fixture
def access_db(monkeypatch):
    class FakeDB:
        def __init__(self):
            self.row = None
            self.updates = []

        async def fetch_one(self, query, params=()):
            return self.row

        async def execute(self, query, params=()):
            self.updates.append((query, params))

    db = FakeDB()
    monkeypatch.setattr(premium_access, "db", db)
    monkeypatch.setattr(premium_access, "ADMIN_IDS", [99])
    return db


@pytest.mark.asyncio
async def test_admin_always_has_access(access_db):
    assert await premium_access.has_premium_access(99) is True


@pytest.mark.asyncio
async def test_expired_subscription_is_cleared(access_db):
    access_db.row = {
        "is_subscribed": True,
        "subscription_until": (datetime.now() - timedelta(days=1)).isoformat(),
    }
    assert await premium_access.has_premium_access(5) is False
    assert access_db.updates


@pytest.mark.asyncio
async def test_active_subscription_passes(access_db):
    access_db.row = {
        "is_subscribed": True,
        "subscription_until": (datetime.now() + timedelta(days=10)).isoformat(),
    }
    assert await premium_access.has_premium_access(5) is True


@pytest.mark.asyncio
async def test_premium_screen_points_to_payment(monkeypatch):
    async def fake_access(user_id):
        return False

    monkeypatch.setattr("handlers.premium.has_premium_access", fake_access)
    text, markup = await build_premium_screen(10)
    labels = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert "payment" in labels
    assert "https://t.me/hop31esss" not in text
    assert all(getattr(button, "url", None) is None for row in markup.inline_keyboard for button in row)


@pytest.mark.asyncio
async def test_show_premium_info_edits_message(monkeypatch):
    monkeypatch.setattr(
        "handlers.premium.build_premium_screen",
        AsyncMock(return_value=("TEXT", SimpleNamespace())),
    )
    callback = SimpleNamespace(
        from_user=SimpleNamespace(id=1),
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
    )
    await show_premium_info(callback)
    callback.message.edit_text.assert_awaited_once()
