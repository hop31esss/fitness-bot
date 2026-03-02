import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram.filters import Command

from config import BOT_TOKEN

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    await message.answer(
        f"👋 Привет!\n\n"
        f"Твой РЕАЛЬНЫЙ пользовательский ID: `{user_id}`\n"
        f"Username: @{message.from_user.username}\n"
        f"Имя: {message.from_user.first_name}\n\n"
        f"Добавь этот ID в админ-панель!"
    )

async def main():
    print("🚀 Запускаем бота для получения REAL ID...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())