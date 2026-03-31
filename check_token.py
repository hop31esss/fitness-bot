import asyncio
import sys
import os
from dotenv import load_dotenv
from aiogram import Bot

# Загружаем переменные окружения
load_dotenv(override=True)

# Получаем токен из переменных окружения
TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    print("❌ Ошибка: BOT_TOKEN не найден в переменных окружения!")
    print("💡 Создайте .env файл и добавьте BOT_TOKEN=your_token_here")
    sys.exit(1)

async def check():
    print(f"🔍 Проверяю токен: {TOKEN[:15]}...")
    try:
        bot = Bot(token=TOKEN)
        me = await bot.get_me()
        print(f"✅ УСПЕХ!")
        print(f"   Бот: @{me.username}")
        print(f"   ID: {me.id}")
        print(f"   Имя: {me.full_name}")
        await bot.session.close()
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(check())