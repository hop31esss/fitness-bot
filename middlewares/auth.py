from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery
from typing import Any, Awaitable, Callable, Dict

class AdminMiddleware(BaseMiddleware):
    def __init__(self, admin_ids: list):
        self.admin_ids = admin_ids
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем, является ли пользователь админом
        user_id = event.from_user.id
        
        if user_id in self.admin_ids:
            data['is_admin'] = True
        else:
            data['is_admin'] = False
        
        return await handler(event, data)