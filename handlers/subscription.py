"""Backward-compatible import location for Premium access checks.

The Premium UI lives in ``handlers.premium``. Existing modules importing
``handlers.subscription.has_premium_access`` continue to use the shared
DB-backed implementation.
"""

from services.premium_access import has_premium_access

__all__ = ["has_premium_access"]
