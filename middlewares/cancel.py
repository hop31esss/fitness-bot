from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, TelegramObject

from keyboards.main import get_main_keyboard


class CancelMiddleware(BaseMiddleware):
    """Global /cancel: clear FSM before state-specific message handlers run."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        if isinstance(event, Message) and event.text:
            command = event.text.split()[0].split("@", 1)[0].lower()
            if command == "/cancel":
                state: FSMContext | None = data.get("state")
                if state is not None:
                    await state.clear()
                await event.answer("Отменено. Выберите действие:", reply_markup=get_main_keyboard())
                return None
        return await handler(event, data)
