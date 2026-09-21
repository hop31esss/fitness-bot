import asyncio
import os
import sys

from aiogram import Bot
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv(override=True)

# Получаем токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("ERROR: BOT_TOKEN is missing.")
    print("Create .env and add BOT_TOKEN=your_token_here")
    sys.exit(1)


async def check():
    print("Checking BOT_TOKEN (value is not printed)...")
    bot = Bot(token=TOKEN)
    try:
        me = await bot.get_me()
        print("SUCCESS")
        print(f"   Bot: @{me.username}")
        print(f"   ID: {me.id}")
        print(f"   Name: {me.full_name}")
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        return False
    finally:
        await bot.session.close()


if __name__ == "__main__":
    raise SystemExit(0 if asyncio.run(check()) else 1)