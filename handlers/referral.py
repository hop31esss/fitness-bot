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
    """Генерирует уникальный код на основе user_id"""
    # Берём первые 4 буквы имени и добавляем случайные цифры
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
    
    # Считаем сколько из них купили премиум
    premium_referrals = await db.fetch_one("""
        SELECT COUNT(*) as count FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ? AND u.is_subscribed = TRUE
    """, (user_id,))
    
    text = (
        "🤝 *Реферальная программа*\n\n"
        "Приглашайте друзей и получайте бонусы!\n\n"
        f"📊 *Ваша статистика:*\n"
        f"• Приглашено друзей: {referrals_count['count'] if referrals_count else 0}\n"
        f"• Из них купили премиум: {premium_referrals['count'] if premium_referrals else 0}\n\n"
        
        "🎁 *Бонусы:*\n"
        "• За каждого друга, купившего премиум → **1 месяц премиума в подарок**\n"
        "• Другу при регистрации → **3 дня премиума**\n\n"
        
        "🔗 *Ваша реферальная ссылка:*\n"
        f"`https://t.me/{(await message.bot.get_me()).username}?start={code}`\n\n"
        
        "📤 *Как использовать:*\n"
        "1. Отправьте эту ссылку другу\n"
        "2. Друг переходит по ссылке и запускает бота\n"
        "3. Вы получаете бонус, когда друг покупает премиум"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📤 ПОДЕЛИТЬСЯ", callback_data="share_referral"),
        InlineKeyboardButton(text="📊 РЕЙТИНГ", callback_data="referral_leaderboard")
    )
    builder.row(
        InlineKeyboardButton(text="🎁 МОИ БОНУСЫ", callback_data="referral_bonuses"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

# ========== ОБРАБОТКА РЕФЕРАЛЬНЫХ ПЕРЕХОДОВ ==========

@router.message(Command("start"))
async def referral_start(message: Message):
    """Обработка команды /start с реферальным кодом"""
    user_id = message.from_user.id
    args = message.text.split()
    
    # Регистрируем пользователя в любом случае
    await db.execute(
        """INSERT OR IGNORE INTO users (user_id, username, first_name, last_name) 
        VALUES (?, ?, ?, ?)""",
        (user_id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    )
    
    # Проверяем, есть ли реферальный код
    if len(args) > 1 and args[1].startswith('ref_'):
        code = args[1].replace('ref_', '')
        
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
                
                # Даём бонус новому пользователю (3 дня премиума)
                bonus_until = (datetime.now() + timedelta(days=3)).isoformat()
                await db.execute("""
                    UPDATE users SET is_subscribed = TRUE, subscription_until = ? 
                    WHERE user_id = ?
                """, (bonus_until, user_id))
                
                # Уведомляем пригласившего
                try:
                    await message.bot.send_message(
                        referrer['user_id'],
                        f"🎉 *Новый друг!*\n\n"
                        f"Пользователь {message.from_user.first_name} присоединился по вашей ссылке!\n"
                        f"Когда он купит премиум, вы получите месяц в подарок!"
                    )
                except:
                    pass
                
                await message.answer(
                    "🎁 *Вам начислен бонус!*\n\n"
                    "За переход по реферальной ссылке вы получили **3 дня премиума**!\n"
                    "Приглашайте друзей и получайте ещё больше бонусов."
                )
    
    # Показываем обычное приветствие
    await show_referral_menu(message)

# ========== ОБРАБОТКА ПОКУПКИ ПРЕМИУМА ==========

async def check_referral_bonus(user_id: int, bot):
    """Проверяет, нужно ли дать бонус пригласившему после покупки премиума"""
    # Находим, кто пригласил этого пользователя
    referral = await db.fetch_one(
        "SELECT referrer_id FROM referrals WHERE referred_id = ? AND premium_granted = FALSE",
        (user_id,)
    )
    
    if referral:
        # Даём месяц премиума пригласившему
        referrer = await db.fetch_one(
            "SELECT subscription_until FROM users WHERE user_id = ?",
            (referral['referrer_id'],)
        )
        
        now = datetime.now()
        if referrer and referrer['subscription_until']:
            try:
                current_until = datetime.fromisoformat(referrer['subscription_until'].replace('Z', '+00:00'))
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
            (new_until.isoformat(), referral['referrer_id'])
        )
        
        # Отмечаем, что бонус выдан
        await db.execute(
            "UPDATE referrals SET premium_granted = TRUE WHERE referred_id = ?",
            (user_id,)
        )
        
        # Уведомляем
        try:
            user = await db.fetch_one(
                "SELECT first_name FROM users WHERE user_id = ?",
                (user_id,)
            )
            await bot.send_message(
                referral['referrer_id'],
                f"🎁 *Вам начислен бонус!*\n\n"
                f"Пользователь {user['first_name']} купил премиум!\n"
                f"Вы получили **+30 дней премиума** в подарок! 🎉"
            )
        except:
            pass

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
        f"`https://t.me/{bot_username}?start=ref_{code}`\n\n"
        "Или нажмите кнопку ниже, чтобы скопировать."
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📋 КОПИРОВАТЬ", callback_data=f"copy_ref_{code}"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="referral")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("copy_ref_"))
async def copy_referral(callback: CallbackQuery):
    """Подтверждение копирования"""
    await callback.answer("✅ Ссылка скопирована!", show_alert=True)

@router.callback_query(F.data == "referral_leaderboard")
async def referral_leaderboard(callback: CallbackQuery):
    """Рейтинг пригласивших"""
    top_referrers = await db.fetch_all("""
        SELECT 
            u.first_name,
            COUNT(r.id) as referrals_count,
            SUM(CASE WHEN u2.is_subscribed THEN 1 ELSE 0 END) as premium_count
        FROM users u
        LEFT JOIN referrals r ON u.user_id = r.referrer_id
        LEFT JOIN users u2 ON r.referred_id = u2.user_id
        GROUP BY u.user_id
        HAVING referrals_count > 0
        ORDER BY premium_count DESC, referrals_count DESC
        LIMIT 10
    """)
    
    text = "🏆 *Рейтинг пригласивших*\n\n"
    
    if top_referrers:
        for i, ref in enumerate(top_referrers, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {ref['first_name']}: {ref['referrals_count']} друзей ({ref['premium_count']} премиум)\n"
    else:
        text += "Пока никто не приглашал друзей.\n\nБудьте первыми! 🚀"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="referral")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "referral_bonuses")
async def referral_bonuses(callback: CallbackQuery):
    """Информация о полученных бонусах"""
    user_id = callback.from_user.id
    
    # Список приглашённых, кто купил премиум
    premium_friends = await db.fetch_all("""
        SELECT u.first_name, u.username, r.created_at
        FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ? AND u.is_subscribed = TRUE
        ORDER BY r.created_at DESC
    """, (user_id,))
    
    text = "🎁 *Мои бонусы*\n\n"
    
    if premium_friends:
        text += "Вы получили премиум за этих друзей:\n\n"
        for f in premium_friends:
            name = f['username'] or f['first_name']
            date = f['created_at'][:10] if f['created_at'] else ""
            text += f"• @{name} — {date}\n"
    else:
        text += "Пока нет друзей, купивших премиум.\n\n"
        text += "Приглашайте друзей и получайте бонусы! 🚀"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="referral")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()