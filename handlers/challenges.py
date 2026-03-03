from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database.base import db
from config import ADMIN_ID

router = Router()

# ================ ПРОВЕРКА ПРЕМИУМ ================

async def check_premium_access(user_id: int) -> bool:
    """Проверка доступа к премиум-функциям"""
    if user_id == ADMIN_ID:
        return True
    
    user = await db.fetch_one(
        "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    if user and user['is_subscribed'] and user['subscription_until']:
        until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
        if datetime.now() <= until:
            return True
    
    return False

# ================ МЕНЮ ЧЕЛЛЕНДЖЕЙ ================

@router.callback_query(F.data == "challenges_menu")
async def challenges_menu(callback: CallbackQuery):
    """Меню челленджей"""
    user_id = callback.from_user.id
    
    # Проверка премиум-доступа
    if not await check_premium_access(user_id):
        await callback.answer("❌ Премиум-функция!", show_alert=True)
        return
    
    # Получаем активные челленджи пользователя
    active_challenges = await db.fetch_all("""
        SELECT * FROM challenges 
        WHERE (user1_id = ? OR user2_id = ?) AND status = 'active'
        ORDER BY created_at DESC
    """, (user_id, user_id))
    
    text = "🏆 *Челленджи*\n\n"
    
    if active_challenges:
        text += "*Активные челленджи:*\n"
        for c in active_challenges:
            # Определяем противника
            opponent_id = c['user2_id'] if c['user1_id'] == user_id else c['user1_id']
            opponent = await db.fetch_one(
                "SELECT username, first_name FROM users WHERE user_id = ?",
                (opponent_id,)
            )
            opponent_name = opponent['username'] or opponent['first_name'] or f"ID{opponent_id}"
            
            text += f"• {c['name']} против @{opponent_name}\n"
            text += f"  Прогресс: {c['user1_progress']}/{c['goal']} : {c['user2_progress']}/{c['goal']}\n"
    else:
        text += "У вас нет активных челленджей.\n\n"
        text += "Создайте челлендж с другом, чтобы соревноваться!"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="⚔️ СОЗДАТЬ ЧЕЛЛЕНДЖ", callback_data="create_challenge")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="friends_menu")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "create_challenge")
async def create_challenge(callback: CallbackQuery):
    """Создание челленджа"""
    user_id = callback.from_user.id
    
    # Получаем список друзей
    friends = await db.fetch_all("""
        SELECT u.user_id, u.username, u.first_name
        FROM friends f
        JOIN users u ON f.friend_id = u.user_id
        WHERE f.user_id = ? AND f.status = 'accepted'
        UNION
        SELECT u.user_id, u.username, u.first_name
        FROM friends f
        JOIN users u ON f.user_id = u.user_id
        WHERE f.friend_id = ? AND f.status = 'accepted'
    """, (user_id, user_id))
    
    if not friends:
        await callback.message.edit_text(
            "❌ У вас нет друзей.\n\nСначала добавьте друга, чтобы создать челлендж!",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="↩️ НАЗАД", callback_data="challenges_menu")
            ).as_markup()
        )
        await callback.answer()
        return
    
    text = "⚔️ *Создание челленджа*\n\nВыберите друга:"
    
    builder = InlineKeyboardBuilder()
    for friend in friends:
        name = friend['username'] or friend['first_name'] or f"ID{friend['user_id']}"
        builder.row(
            InlineKeyboardButton(
                text=f"👤 @{name}",
                callback_data=f"challenge_friend:{friend['user_id']}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="challenges_menu")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()