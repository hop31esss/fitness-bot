"""Single source of truth for Premium access."""

from datetime import datetime

from config import ADMIN_IDS
from database.base import db


def _parse_expiration(value: object) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _is_expired(expiration: datetime) -> bool:
    now = datetime.now(expiration.tzinfo) if expiration.tzinfo else datetime.now()
    return now > expiration


async def has_premium_access(user_id: int) -> bool:
    """Return active DB subscription status; configured admins always pass."""
    if user_id in ADMIN_IDS:
        return True

    user = await db.fetch_one(
        "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
        (user_id,),
    )
    if not user or not user["is_subscribed"]:
        return False

    expiration = _parse_expiration(user["subscription_until"])
    if expiration is not None and not _is_expired(expiration):
        return True

    # Keep the persisted flag honest for missing, invalid, and expired dates.
    await db.execute(
        "UPDATE users SET is_subscribed = FALSE WHERE user_id = ?",
        (user_id,),
    )
    return False
