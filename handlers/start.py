from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart

from database.base import db
from keyboards.main import get_main_keyboard
from services.analytics import update_user_stats

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обработчик команды /start с поддержкой рефералов"""
    user_id = message.from_user.id
    args = message.text.split()
    
    # Регистрируем пользователя
    await db.execute(
        """INSERT OR REPLACE INTO users 
        (user_id, username, first_name, last_name) 
        VALUES (?, ?, ?, ?)""",
        (user_id, message.from_user.username, 
         message.from_user.first_name, message.from_user.last_name)
    )
    
    # Проверяем реферальный код
    if len(args) > 1:
        code = args[1]
        
        # Находим пригласившего
        referrer = await db.fetch_one(
            "SELECT user_id FROM referral_codes WHERE code = ?",
            (code,)
        )
        
        if referrer and referrer['user_id'] != user_id:
            # Проверяем, не был ли уже приглашён
            existing = await db.fetch_one(
                "SELECT id FROM referrals WHERE referred_id = ?",
                (user_id,)
            )
            
            if not existing:
                # Сохраняем приглашение
                await db.execute("""
                    INSERT INTO referrals (referrer_id, referred_id, code) 
                    VALUES (?, ?, ?)
                """, (referrer['user_id'], user_id, code))
                
                # Даём месяц премиума пригласившему
                from handlers.referral import add_premium_month
                await add_premium_month(referrer['user_id'])
                
                # Уведомляем пригласившего
                try:
                    await message.bot.send_message(
                        referrer['user_id'],
                        f"🎉 *Новый друг!*\n\n"
                        f"{message.from_user.first_name} присоединился по вашей ссылке!\n"
                        f"✅ Вы получили +30 дней премиума!"
                    )
                except:
                    pass
    
    # Показываем главное меню
    user = await db.fetch_one(
        "SELECT is_subscribed FROM users WHERE user_id = ?",
        (user_id,)
    )
    is_premium = user and user['is_subscribed'] if user else False
    
    welcome_text = (
        f"🌟 *Добро пожаловать, {message.from_user.first_name}!*\n\n"
        "Я ваш персональный фитнес-помощник.\n\n"
        "▫️ Записывайте тренировки\n"
        "▫️ Отслеживайте прогресс\n"
        "▫️ Приглашайте друзей и получайте премиум!\n\n"
        "👇 *Выберите действие:*"
    )
    
    keyboard = get_main_keyboard(user_id, is_premium)
    await message.answer(welcome_text, reply_markup=keyboard)

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    user_id = callback.from_user.id
    
    # Проверяем премиум
    user = await db.fetch_one(
        "SELECT is_subscribed FROM users WHERE user_id = ?",
        (user_id,)
    )
    is_premium = user and user['is_subscribed'] if user else False
    
    keyboard = get_main_keyboard(user_id, is_premium)
    
    # Используем edit_text вместо edit_caption
    await callback.message.edit_text(
        text="🌟 *Главное меню*\n\nВыберите действие:",
        reply_markup=keyboard
    )
    await callback.answer()