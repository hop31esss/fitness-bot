from unittest.mock import MagicMock

from utils import logging as logging_utils


def test_configure_logger_adds_handler(monkeypatch):
    fake_logger = MagicMock()
    fake_logger.handlers = []

    fake_handler = MagicMock()
    monkeypatch.setattr(logging_utils.logging, "FileHandler", lambda *args, **kwargs: fake_handler)

    logging_utils._configure_logger(fake_logger)

    fake_logger.addHandler.assert_called_once_with(fake_handler)
    fake_logger.setLevel.assert_called_once()


def test_configure_logger_skips_when_handlers_present():
    fake_logger = MagicMock()
    fake_logger.handlers = [object()]

    logging_utils._configure_logger(fake_logger)

    fake_logger.addHandler.assert_not_called()


def test_log_action_without_extra(monkeypatch):
    mock_logger = MagicMock()
    monkeypatch.setattr(logging_utils, "logger", mock_logger)

    logging_utils.log_action(user_id=123, action="open_menu")

    mock_logger.info.assert_called_once_with("user=123 action=open_menu")


def test_log_action_with_extra(monkeypatch):
    mock_logger = MagicMock()
    monkeypatch.setattr(logging_utils, "logger", mock_logger)

    logging_utils.log_action(user_id=321, action="save", extra={"sets": 3})

    mock_logger.info.assert_called_once()
    sent = mock_logger.info.call_args[0][0]
    assert "user=321 action=save" in sent
    assert "extra={'sets': 3}" in sent
