import logging
from typing import Any, Mapping


logger = logging.getLogger("fitness_bot")


def _configure_logger(target_logger: logging.Logger) -> None:
    if target_logger.handlers:
        return
    handler = logging.FileHandler("bot.log", encoding="utf-8", mode="a")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    target_logger.addHandler(handler)
    target_logger.setLevel(logging.INFO)


_configure_logger(logger)


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

