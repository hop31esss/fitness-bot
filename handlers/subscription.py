from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database.base import db
from config import ADMIN_IDS

router = Router()

# ================ ПРОВЕРКА ПРЕМИУМ-ДОСТУПА ================

async def has_premium_access(user_id: int) -> bool:
    """Проверка доступа к премиум-функциям"""
    
    # 1. Админы имеют доступ всегда
    if user_id in ADMIN_IDS:
        return True
    
    # 2. Проверяем платную подписку
    user = await db.fetch_one(
        "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    if user and user['is_subscribed'] and user['subscription_until']:
        until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
        if datetime.now() <= until:
            return True
        else:
            # Подписка истекла
            await db.execute(
                "UPDATE users SET is_subscribed = FALSE WHERE user_id = ?",
                (user_id,)
            )
    
    return False

# ================ ГЛАВНОЕ МЕНЮ ПРЕМИУМ ================

@router.callback_query(F.data == "show_premium_info")
async def show_premium_info(callback: CallbackQuery):
    """Показать информацию о премиум-подписке"""
    user_id = callback.from_user.id
    has_access = await has_premium_access(user_id)
    
    if has_access:
        # Для админов показываем статус
        text = (
            "👑 *Премиум доступ*\n\n"
            "✅ У вас есть доступ ко всем премиум-функциям!\n\n"
            "*Доступные функции:*\n"
            "• 🏋️ Калькулятор 1ПМ с историей\n"
            "• 🔥 Полный трекер калорий\n"
            "• 👥 Друзья и челленджи\n"
            "• 📊 Расширенная статистика\n"
            "• 📤 Экспорт данных\n\n"
            "Наслаждайтесь! 💪"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🏋️ Калькулятор 1ПМ", callback_data="one_rep_max"),
            InlineKeyboardButton(text="🔥 Трекер калорий", callback_data="calorie_tracker")
        )
        builder.row(
            InlineKeyboardButton(text="↩️ В меню", callback_data="back_to_main")
        )
        
    else:
        text = (
            "👑 *Премиум подписка*\n\n"
            "Получите доступ к расширенным функциям:\n\n"
            "✨ *Премиум-функции:*\n"
            "• 🏋️ **Калькулятор 1ПМ** с историей прогресса\n"
            "• 🔥 **Трекер калорий** с базой продуктов\n"
            "• 👥 **Друзья и челленджи** для мотивации\n"
            "• 📊 **Расширенная статистика** с графиками\n"
            "• 📤 **Экспорт данных** в Excel/CSV\n\n"
            "💰 *Стоимость:* 299₽/месяц\n\n"
            "Скоро здесь будет возможность оплаты через Telegram Stars!"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="💰 Купить премиум", callback_data="buy_premium_soon"),
            InlineKeyboardButton(text="↩️ В меню", callback_data="back_to_main")
        )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "buy_premium_soon")
async def buy_premium_soon(callback: CallbackQuery):
    """Временная заглушка для покупки"""
    await callback.message.edit_text(
        "💳 *Оплата премиум*\n\n"
        "Функция оплаты появится в ближайшее время!\n\n"
        "Следите за обновлениями бота. 🚀",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="↩️ Назад", callback_data="show_premium_info")
        ).as_markup()
    )
    await callback.answer()

@router.message(Command("premium"))
async def cmd_premium(message: Message):
    """Команда для вызова премиум-меню"""
    # Создаем фиктивный callback
    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
            self.answer = lambda x: None
    
    fake_callback = FakeCallback(message)
    await show_premium_info(fake_callback)