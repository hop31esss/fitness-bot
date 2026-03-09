from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import random
import string
import logging

from database.base import db
from config import ADMIN_ID

router = Router()
logger = logging.getLogger(__name__)

# ========== ГЕНЕРАЦИЯ РЕФЕРАЛЬНОГО КОДА ==========

def generate_referral_code(user_id: int) -> str:
    """Генерирует уникальный код"""
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{random_part}"

async def get_or_create_referral_code(user_id: int) -> str:
    """Получить существующий код или создать новый"""
    code = await db.fetch_one(
        "SELECT code FROM referral_codes WHERE user_id = ?",
        (user_id,)
    )
    
    if code:
        return code['code']
    
    # Генерируем новый код
    new_code = generate_referral_code(user_id)
    
    # Проверяем уникальность
    while True:
        existing = await db.fetch_one(
            "SELECT id FROM referral_codes WHERE code = ?",
            (new_code,)
        )
        if not existing:
            break
        new_code = generate_referral_code(user_id)
    
    await db.execute(
        "INSERT INTO referral_codes (user_id, code) VALUES (?, ?)",
        (user_id, new_code)
    )
    
    return new_code

# ========== ГЛАВНОЕ МЕНЮ РЕФЕРАЛОВ ==========

@router.message(Command("referral"))
async def referral_command(message: Message):
    """Команда /referral - показать реферальную информацию"""
    await show_referral_menu(message)

@router.callback_query(F.data == "referral")
async def referral_menu(callback: CallbackQuery):
    """Меню реферальной системы"""
    await show_referral_menu(callback.message)
    await callback.answer()

async def show_referral_menu(message: Message):
    """Показать информацию о реферальной программе"""
    user_id = message.from_user.id
    
    # Получаем код пользователя
    code = await get_or_create_referral_code(user_id)
    
    # Считаем количество приглашённых
    referrals_count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM referrals WHERE referrer_id = ?",
        (user_id,)
    )
    count = referrals_count['count'] if referrals_count else 0
    
    # Получаем информацию о подписке
    user_sub = await db.fetch_one(
        "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    sub_text = ""
    if user_sub and user_sub['is_subscribed'] and user_sub['subscription_until']:
        until = datetime.fromisoformat(user_sub['subscription_until'].replace('Z', '+00:00'))
        sub_text = f"📅 Действует до: {until.strftime('%d.%m.%Y')}\n"
    
    text = (
        "🤝 *Реферальная программа*\n\n"
        "🎁 *За каждого приглашённого друга — 1 месяц премиума!*\n\n"
        f"📊 *Ваша статистика:*\n"
        f"• Приглашено друзей: {count}\n"
        f"{sub_text}\n"
        "🔗 *Ваша реферальная ссылка:*\n"
        f"`https://t.me/{(await message.bot.get_me()).username}?start={code}`\n\n"
        "📤 *Как это работает:*\n"
        "1. Отправьте эту ссылку другу\n"
        "2. Друг переходит по ссылке и запускает бота\n"
        "3. Вы сразу получаете +30 дней премиума\n"
        "4. Чем больше друзей — тем больше премиума!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📤 ПОДЕЛИТЬСЯ", callback_data="share_referral")
    )
    builder.row(
        InlineKeyboardButton(text="📊 МОИ ДРУЗЬЯ", callback_data="referral_friends"),
        InlineKeyboardButton(text="🏆 РЕЙТИНГ", callback_data="referral_leaderboard")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

# ========== ОБРАБОТКА РЕФЕРАЛЬНЫХ ПЕРЕХОДОВ ==========

@router.message(Command("start"))
async def referral_start(message: Message):
    """Обработка команды /start с реферальным кодом"""
    user_id = message.from_user.id
    args = message.text.split()
    
    # Регистрируем пользователя
    await db.execute(
        """INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) 
        VALUES (?, ?, ?, ?)""",
        (user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    )
    
    # Проверяем, есть ли реферальный код
    if len(args) > 1:
        code = args[1]
        
        # Находим, кто пригласил
        referrer = await db.fetch_one(
            "SELECT user_id FROM referral_codes WHERE code = ?",
            (code,)
        )
        
        if referrer and referrer['user_id'] != user_id:
            # Проверяем, не был ли этот пользователь уже приглашён
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
                
                # ДАЁМ МЕСЯЦ ПРЕМИУМА ПРИГЛАСИВШЕМУ
                await add_premium_month(referrer['user_id'])
                
                # Отправляем уведомление пригласившему
                try:
                    await message.bot.send_message(
                        referrer['user_id'],
                        f"🎉 *Поздравляем!*\n\n"
                        f"Пользователь {message.from_user.first_name} присоединился по вашей ссылке!\n"
                        f"✅ Вы получили +30 дней премиума!"
                    )
                except:
                    pass
                
                # Отправляем приветствие новому пользователю
                await message.answer(
                    "👋 *Добро пожаловать!*\n\n"
                    "Вы перешли по реферальной ссылке.\n"
                    "Приглашайте друзей и получайте премиум! 🎁"
                )
    
    # Показываем обычное приветствие
    await show_referral_menu(message)

async def add_premium_month(user_id: int):
    """Добавляет 30 дней премиума пользователю"""
    user = await db.fetch_one(
        "SELECT subscription_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    now = datetime.now()
    
    if user and user['subscription_until']:
        try:
            current_until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
            if current_until > now:
                new_until = current_until + timedelta(days=30)
            else:
                new_until = now + timedelta(days=30)
        except:
            new_until = now + timedelta(days=30)
    else:
        new_until = now + timedelta(days=30)
    
    await db.execute(
        "UPDATE users SET is_subscribed = TRUE, subscription_until = ? WHERE user_id = ?",
        (new_until.isoformat(), user_id)
    )

# ========== ДОПОЛНИТЕЛЬНЫЕ ФУНКЦИИ ==========

@router.callback_query(F.data == "share_referral")
async def share_referral(callback: CallbackQuery):
    """Поделиться реферальной ссылкой"""
    user_id = callback.from_user.id
    code = await get_or_create_referral_code(user_id)
    bot_username = (await callback.bot.get_me()).username
    
    text = (
        "📤 *Поделиться ссылкой*\n\n"
        "Отправьте эту ссылку друзьям:\n\n"
        f"`https://t.me/{bot_username}?start={code}`\n\n"
        "За каждого друга вы получите **+30 дней премиума**!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 КОПИРОВАТЬ", callback_data=f"copy_ref"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="referral")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "copy_ref")
async def copy_referral(callback: CallbackQuery):
    """Подтверждение копирования"""
    await callback.answer("✅ Ссылка скопирована! Отправьте её друзьям.", show_alert=True)

@router.callback_query(F.data == "referral_friends")
async def referral_friends(callback: CallbackQuery):
    """Список приглашённых друзей"""
    user_id = callback.from_user.id
    
    friends = await db.fetch_all("""
        SELECT u.first_name, u.username, r.created_at
        FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ?
        ORDER BY r.created_at DESC
    """, (user_id,))
    
    text = "📊 *Мои друзья*\n\n"
    
    if friends:
        for f in friends:
            name = f['username'] or f['first_name']
            date = f['created_at'][:10] if f['created_at'] else ""
            text += f"• @{name} — {date}\n"
    else:
        text += "У вас пока нет приглашённых друзей.\n\n"
        text += "Поделитесь ссылкой и получайте премиум! 🚀"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="referral")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "referral_leaderboard")
async def referral_leaderboard(callback: CallbackQuery):
    """Рейтинг пригласивших"""
    top_referrers = await db.fetch_all("""
        SELECT 
            u.first_name,
            COUNT(r.id) as referrals_count
        FROM users u
        LEFT JOIN referrals r ON u.user_id = r.referrer_id
        GROUP BY u.user_id
        HAVING referrals_count > 0
        ORDER BY referrals_count DESC
        LIMIT 10
    """)
    
    text = "🏆 *Рейтинг пригласивших*\n\n"
    
    if top_referrers:
        for i, ref in enumerate(top_referrers, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {ref['first_name']}: {ref['referrals_count']} друзей\n"
    else:
        text += "Пока никто не приглашал друзей.\n\nБудьте первыми! 🚀"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="referral")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()