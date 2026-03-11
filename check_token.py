import asyncio
import sys
from aiogram import Bot

# ВСТАВЬТЕ СЮДА НОВЫЙ ТОКЕН НАПРЯМУЮ
TOKEN = "8391767389:AAE76LxI2ckpN1FAWcmL7YusfHRVmNRVLoA"  # Замените на ваш новый токен

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