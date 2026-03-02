from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Any, Awaitable, Callable, Dict
from database.base import db
from config import ADMIN_IDS, PREMIUM_FRIENDS
from datetime import datetime

class PremiumCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message | CallbackQuery,
        data: Dict[str, Any]
    ) -> Any:
        
        # Список премиум-функций
        premium_features = [
            "one_rep_max",
            "calorie_tracker",
            "friends_menu",
            "challenges_menu",
            "premium_stats",
            "export_data",
            "advanced_stats"
        ]
        
        # Проверяем, является ли событие callback_query
        if isinstance(event, CallbackQuery):
            callback_data = event.data
            
            # Проверяем, содержит ли callback_data премиум-функцию
            is_premium_feature = any(feature in callback_data for feature in premium_features)
            
            if is_premium_feature:
                user_id = event.from_user.id
                
                # Проверяем доступ
                has_access = False
                
                # 1. Админы имеют доступ
                if user_id in ADMIN_IDS:
                    has_access = True
                
                # 2. Друзья из списка имеют доступ
                elif user_id in PREMIUM_FRIENDS:
                    has_access = True
                
                # 3. Проверяем платную подписку
                else:
                    user = await db.fetch_one(
                        "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
                        (user_id,)
                    )
                    
                    if user and user['is_subscribed'] and user['subscription_until']:
                        until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
                        if datetime.now() <= until:
                            has_access = True
                
                if not has_access:
                    # Если нет доступа, показываем предложение купить
                    await event.answer("❌ Это премиум-функция!", show_alert=True)
                    
                    builder = InlineKeyboardBuilder()
                    builder.row(
                        InlineKeyboardButton(text="👑 Узнать о премиум", callback_data="show_premium_info")
                    )
                    
                    await event.message.answer(
                        "👑 *Премиум-доступ*\n\n"
                        "Эта функция доступна только с премиум-подпиской!\n\n"
                        "💰 *Стоимость:* 299₽/месяц\n\n"
                        "Нажмите кнопку ниже, чтобы узнать подробности:",
                        reply_markup=builder.as_markup()
                    )
                    return
        
        return await handler(event, data)