from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Any, Awaitable, Callable, Dict
from database.base import db
from datetime import datetime
from utils.logging import log_action

class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
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
            if event.from_user:
                log_action(event.from_user.id, "middleware_subscription_check", {"data": callback_data})
            
            # Проверяем, содержит ли callback_data премиум-функцию
            if any(feature in callback_data for feature in premium_features):
                user_id = event.from_user.id
                
                # Проверяем подписку
                user = await db.fetch_one(
                    "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
                    (user_id,)
                )
                
                is_premium = False
                if user and user['is_subscribed']:
                    if user['subscription_until']:
                        until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
                        if datetime.now() <= until:
                            is_premium = True
                        else:
                            # Подписка истекла
                            await db.execute(
                                "UPDATE users SET is_subscribed = FALSE WHERE user_id = ?",
                                (user_id,)
                            )
                
                if not is_premium:
                    # Если нет подписки, показываем предложение купить
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