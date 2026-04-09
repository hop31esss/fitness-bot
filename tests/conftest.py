import pytest
from aiogram import Bot


@pytest.fixture
def bot() -> Bot:
    """Test bot fixture with a non-real token."""
    return Bot(token="1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")

