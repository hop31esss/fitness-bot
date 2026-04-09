from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Any, Awaitable, Callable, Dict
from utils.logging import log_action

class AdminMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: list):
        self.admin_ids = admin_ids
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        user = getattr(event, "from_user", None)
        user_id = getattr(user, "id", None)
        data["is_admin"] = bool(user_id in self.admin_ids if user_id is not None else False)
        if user_id is not None:
            log_action(user_id, "middleware_admin_check", {"is_admin": data["is_admin"]})
        return await handler(event, data)