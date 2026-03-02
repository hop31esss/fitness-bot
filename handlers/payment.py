from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import uuid
import logging

from database.base import db
from config import ADMIN_ID, STARS_PRICE, SUBSCRIPTION_DAYS

router = Router()
logger = logging.getLogger(__name__)

# ================ КОМАНДА ПОКУПКИ ================

@router.message(Command("buy"))
async def cmd_buy(message: Message):
    """Команда для покупки премиум-подписки"""
    # Отправляем счет напрямую через message.answer_invoice
    await show_payment_options(message.from_user.id, message.bot, message.chat.id)

@router.callback_query(F.data == "buy_premium")
async def buy_premium_callback(callback: CallbackQuery):
    """Покупка премиум из меню"""
    # Используем callback.bot и callback.message.chat.id
    await show_payment_options(callback.from_user.id, callback.bot, callback.message.chat.id)
    await callback.answer()

async def show_payment_options(user_id: int, bot, chat_id: int):
    """Показать варианты оплаты (исправленная версия)"""
    text = (
        "💫 *Оплата премиум-подписки*\n\n"
        f"💰 *Стоимость:* {STARS_PRICE} Telegram Stars\n"
        f"⏱️ *Длительность:* {SUBSCRIPTION_DAYS} дней\n\n"
        "Telegram Stars — это внутренняя валюта Telegram.\n"
        "Купить Stars можно в настройках Telegram.\n\n"
        "Нажмите кнопку ниже для оплаты:"
    )
    
    # Отправляем информационное сообщение
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💫 Оплатить Stars", callback_data="start_payment")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="show_premium_info")
    )
    
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=builder.as_markup()
    )

@router.callback_query(F.data == "start_payment")
async def start_payment(callback: CallbackQuery):
    """Начать процесс оплаты"""
    user_id = callback.from_user.id
    
    # Создаем счет на оплату
    prices = [LabeledPrice(label="Премиум подписка", amount=STARS_PRICE)]
    
    # Генерируем уникальный payload для этого платежа
    payload = f"premium_{user_id}_{uuid.uuid4()}"
    
    try:
        # Отправляем invoice
        await callback.bot.send_invoice(
            chat_id=user_id,  # Отправляем самому пользователю
            title="Премиум подписка FitnessBot",
            description=f"Доступ ко всем премиум-функциям на {SUBSCRIPTION_DAYS} дней",
            payload=payload,
            provider_token="",  # Для Stars оставляем пустым
            currency="XTR",  # XTR = Telegram Stars
            prices=prices,
            start_parameter="premium-subscription"
        )
    except Exception as e:
        logger.error(f"Error sending invoice: {e}")
        await callback.message.answer(
            "❌ Не удалось создать счет для оплаты. Попробуйте позже."
        )
    
    await callback.answer()

# ================ ОБРАБОТКА ПЛАТЕЖЕЙ ================

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Проверка перед оплатой (всегда разрешаем)"""
    await pre_checkout_query.bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True
    )
    logger.info(f"Pre-checkout ok for user {pre_checkout_query.from_user.id}")

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Обработка успешной оплаты"""
    user_id = message.from_user.id
    payment = message.successful_payment
    
    # Рассчитываем дату окончания подписки
    now = datetime.now()
    until = now + timedelta(days=SUBSCRIPTION_DAYS)
    
    # Получаем текущую подписку пользователя
    current_sub = await db.fetch_one(
        "SELECT subscription_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    # Если есть активная подписка, продлеваем её
    if current_sub and current_sub['subscription_until']:
        try:
            current_until = datetime.fromisoformat(current_sub['subscription_until'].replace('Z', '+00:00'))
            if current_until > now:
                # Продлеваем существующую подписку
                until = current_until + timedelta(days=SUBSCRIPTION_DAYS)
        except:
            pass
    
    # Сохраняем информацию о подписке
    await db.execute(
        """UPDATE users SET 
        is_subscribed = TRUE, 
        subscription_until = ? 
        WHERE user_id = ?""",
        (until.isoformat(), user_id)
    )
    
    # Сохраняем информацию о платеже
    await db.execute(
        """INSERT INTO payments 
        (user_id, amount, currency, payload, date) 
        VALUES (?, ?, ?, ?, ?)""",
        (user_id, payment.total_amount, payment.currency, payment.invoice_payload, now.isoformat())
    )
    
    # Формируем сообщение об успехе
    text = (
        "🎉 *Поздравляем с покупкой!*\n\n"
        f"✅ Премиум-подписка активирована!\n"
        f"📅 Действует до: {until.strftime('%d.%m.%Y')}\n\n"
        "*Теперь вам доступно:*\n"
        "• 🏋️ Калькулятор 1ПМ\n"
        "• 🔥 Полный трекер калорий\n"
        "• 👥 Друзья и челленджи\n"
        "• 📊 Расширенная статистика\n"
        "• 📤 Экспорт данных\n\n"
        "Спасибо за поддержку! 💪"
    )
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ Премиум функции", callback_data="show_premium_info"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())
    
    # Уведомление админа
    try:
        await message.bot.send_message(
            ADMIN_ID,
            f"💰 *Новая оплата!*\n\n"
            f"Пользователь: @{message.from_user.username or message.from_user.first_name}\n"
            f"ID: `{user_id}`\n"
            f"Сумма: {payment.total_amount} Stars\n"
            f"Действует до: {until.strftime('%d.%m.%Y')}"
        )
    except:
        pass
    
    logger.info(f"User {user_id} purchased premium until {until.isoformat()}")

# ================ ПРОВЕРКА СТАТУСА ПОДПИСКИ ================

@router.message(Command("status"))
async def subscription_status(message: Message):
    """Проверка статуса подписки"""
    user_id = message.from_user.id
    
    user = await db.fetch_one(
        "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    if not user or not user['is_subscribed'] or not user['subscription_until']:
        await message.answer(
            "❌ *У вас нет активной подписки*\n\n"
            f"Приобрести премиум можно за {STARS_PRICE} Stars",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="💫 Купить", callback_data="buy_premium")
            ).as_markup()
        )
        return
    
    try:
        until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
        now = datetime.now()
        
        if now > until:
            # Подписка истекла
            await db.execute(
                "UPDATE users SET is_subscribed = FALSE WHERE user_id = ?",
                (user_id,)
            )
            await message.answer(
                "❌ *Срок подписки истек*\n\n"
                f"Последний день: {until.strftime('%d.%m.%Y')}\n"
                f"Приобрести новую подписку можно за {STARS_PRICE} Stars",
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="💫 Купить", callback_data="buy_premium")
                ).as_markup()
            )
        else:
            days_left = (until - now).days
            await message.answer(
                f"✅ *Подписка активна*\n\n"
                f"📅 Действует до: {until.strftime('%d.%m.%Y')}\n"
                f"⏳ Осталось дней: {days_left}",
                reply_markup=InlineKeyboardBuilder().row(
                    InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
                ).as_markup()
            )
    except Exception as e:
        await message.answer("❌ Ошибка при проверке статуса")

# ================ ВОЗВРАТ В ПРЕМИУМ-МЕНЮ ================

@router.callback_query(F.data == "show_premium_info")
async def show_premium_info(callback: CallbackQuery):
    """Показать информацию о премиум"""
    user_id = callback.from_user.id
    
    # Проверяем статус подписки
    user = await db.fetch_one(
        "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    is_premium = False
    until_text = ""
    
    if user and user['is_subscribed'] and user['subscription_until']:
        try:
            until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
            if datetime.now() <= until:
                is_premium = True
                until_text = until.strftime('%d.%m.%Y')
        except:
            pass
    
    if is_premium or user_id == ADMIN_ID:
        # Для админа или премиум-пользователей
        status = "👑 Администратор" if user_id == ADMIN_ID else "⭐ Премиум пользователь"
        text = (
            f"👑 *Премиум статус*\n\n"
            f"*Статус:* {status}\n"
            f"*Действует до:* {until_text if until_text else 'бессрочно'}\n\n"
            "*Доступные функции:*\n"
            "• 🏋️ Калькулятор 1ПМ\n"
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
            InlineKeyboardButton(text="👥 Друзья", callback_data="friends_menu"),
            InlineKeyboardButton(text="↩️ В меню", callback_data="back_to_main")
        )
        
    else:
        # Для обычных пользователей
        text = (
            "👑 *Премиум подписка*\n\n"
            f"💰 *Стоимость:* {STARS_PRICE} Telegram Stars\n"
            f"⏱️ *Длительность:* {SUBSCRIPTION_DAYS} дней\n\n"
            "*Премиум-функции:*\n"
            "• 🏋️ Калькулятор 1ПМ с историей\n"
            "• 🔥 Полный трекер калорий с базой продуктов\n"
            "• 👥 Друзья и челленджи\n"
            "• 📊 Расширенная статистика с графиками\n"
            "• 📤 Экспорт данных в Excel\n\n"
            "Нажмите кнопку ниже для покупки:"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="💫 Купить за Stars", callback_data="buy_premium")
        )
        builder.row(
            InlineKeyboardButton(text="↩️ В меню", callback_data="back_to_main")
        )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()