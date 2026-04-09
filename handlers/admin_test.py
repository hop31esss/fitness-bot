from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()

@router.message(Command("admin"))
async def admin_test(message: Message):
    """Тестовая админ-команда"""
    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!\n\n"
        f"Твой ID: `{message.from_user.id}`\n"
        f"Username: @{message.from_user.username}\n\n"
        f"Это тестовая команда. Если ты это видишь - роутер работает!"
    )