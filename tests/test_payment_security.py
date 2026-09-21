from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from handlers import payment as payment_handlers


def _callback(user_id: int = 1001):
    return SimpleNamespace(
        data="check_payment:payment-1",
        from_user=SimpleNamespace(id=user_id),
        message=SimpleNamespace(edit_text=AsyncMock()),
        answer=AsyncMock(),
        bot=SimpleNamespace(),
    )


@pytest.mark.asyncio
async def test_yookassa_rejects_wrong_amount(monkeypatch):
    callback = _callback()
    monkeypatch.setattr(
        payment_handlers.YooKassaService,
        "get_payment",
        AsyncMock(
            return_value={
                "id": "payment-1",
                "status": "succeeded",
                "user_id": "1001",
                "amount": "1.00",
                "currency": "RUB",
            }
        ),
    )
    claim = AsyncMock(return_value=True)
    activate = AsyncMock(return_value=True)
    monkeypatch.setattr(payment_handlers, "claim_payment", claim)
    monkeypatch.setattr(payment_handlers, "activate_premium", activate)

    await payment_handlers.check_payment(callback)

    claim.assert_not_awaited()
    activate.assert_not_awaited()
    callback.answer.assert_awaited_with(
        "Сумма или валюта платежа не совпадает.",
        show_alert=True,
    )


@pytest.mark.asyncio
async def test_failed_activation_releases_yookassa_claim(monkeypatch):
    callback = _callback()
    monkeypatch.setattr(
        payment_handlers.YooKassaService,
        "get_payment",
        AsyncMock(
            return_value={
                "id": "payment-1",
                "status": "succeeded",
                "user_id": "1001",
                "amount": str(payment_handlers.PREMIUM_PRICE),
                "currency": "RUB",
            }
        ),
    )
    monkeypatch.setattr(
        payment_handlers,
        "claim_payment",
        AsyncMock(return_value=True),
    )
    monkeypatch.setattr(
        payment_handlers,
        "activate_premium",
        AsyncMock(return_value=False),
    )
    release = AsyncMock()
    monkeypatch.setattr(payment_handlers, "release_payment", release)

    await payment_handlers.check_payment(callback)

    release.assert_awaited_once_with("payment-1", 1001)


@pytest.mark.asyncio
async def test_activate_premium_upserts_missing_user(monkeypatch):
    queries = []

    async def fake_fetch_one(query, params):
        if "subscription_until" in query:
            return None
        return {"username": None, "first_name": None}

    async def fake_execute(query, params):
        queries.append((query, params))

    monkeypatch.setattr(payment_handlers.db, "fetch_one", fake_fetch_one)
    monkeypatch.setattr(payment_handlers.db, "execute", fake_execute)
    bot = SimpleNamespace(send_message=AsyncMock())

    activated = await payment_handlers.activate_premium(1001, bot)

    assert activated is True
    assert "ON CONFLICT(user_id) DO UPDATE" in queries[0][0]
