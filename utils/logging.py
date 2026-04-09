import logging
from typing import Any, Mapping


logger = logging.getLogger("fitness_bot")
if not logger.handlers:
    handler = logging.FileHandler("bot.log", encoding="utf-8", mode="a")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def log_action(user_id: int, action: str, extra: Mapping[str, Any] | None = None) -> None:
    """
    Универсальная запись действия пользователя.
    :param user_id: Telegram-ID пользователя.
    :param action: Краткое название действия (например, "open_menu", "add_exercise").
    :param extra: Дополнительные данные.
    """
    msg = f"user={user_id} action={action}"
    if extra:
        msg += f" extra={extra!r}"
    logger.info(msg)

