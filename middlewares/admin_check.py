from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Any, Awaitable, Callable, Dict

class AdminCheckMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: list):
        self.admin_ids = admin_ids
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Добавляем флаг is_admin в данные
        user_id = event.from_user.id
        data['is_admin'] = user_id in self.admin_ids
        return await handler(event, data)