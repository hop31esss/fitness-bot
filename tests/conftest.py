import pytest
import sys
from pathlib import Path
from aiogram import Bot

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def bot() -> Bot:
    """Test bot fixture with a non-real token."""
    return Bot(token="1234567890:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghi")

