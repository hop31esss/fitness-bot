from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
import uuid
import logging

from database.base import db
from config import ADMIN_ID
from services.yookassa_service import YooKassaService

router = Router()
logger = logging.getLogger(__name__)

# Цены
PREMIUM_PRICE = 150  # рублей (было 299)
PREMIUM_STARS_PRICE = 120  # Telegram Stars (было 25)
PREMIUM_MONTHS = 1

# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================

async def activate_premium(user_id: int, bot):
    """Активация премиум-подписки"""
    try:
        now = datetime.now()
        until = now + timedelta(days=30)
        
        # Получаем текущую подписку
        current = await db.fetch_one(
            "SELECT subscription_until FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        # Если есть активная подписка, продлеваем
        if current and current['subscription_until']:
            try:
                current_until = datetime.fromisoformat(current['subscription_until'].replace('Z', '+00:00'))
                if current_until > now:
                    until = current_until + timedelta(days=30)
            except Exception:
                pass
        
        # Сохраняем в БД
        await db.execute(
            "UPDATE users SET is_subscribed = TRUE, subscription_until = ? WHERE user_id = ?",
            (until.isoformat(), user_id)
        )
        
        logger.info(f"✅ Премиум активирован для пользователя {user_id} до {until}")
        
        # Отправляем уведомление админу
        try:
            user = await db.fetch_one(
                "SELECT username, first_name FROM users WHERE user_id = ?",
                (user_id,)
            )
            name = user['username'] or user['first_name'] or f"ID{user_id}"
            
            await bot.send_message(
                ADMIN_ID,
                f"💰 *Новая оплата!*\n\n"
                f"👤 Пользователь: {name}\n"
                f"🆔 ID: `{user_id}`\n"
                f"📅 Действует до: {until.strftime('%d.%m.%Y')}"
            )
        except Exception as e:
            logger.error(f"Ошибка уведомления админа: {e}")
            
    except Exception as e:
        logger.error(f"Ошибка активации премиум: {e}")

# ================ ГЛАВНОЕ МЕНЮ ПЛАТЕЖЕЙ ================

@router.message(Command("buy"))
async def cmd_buy(message: Message):
    """Команда для покупки премиум"""
    await show_payment_options(message)

@router.callback_query(F.data == "payment")
async def payment_menu(callback: CallbackQuery):
    """Меню платежей"""
    await show_payment_options(callback.message)
    await callback.answer()

async def show_payment_options(message: Message):
    """Показать варианты оплаты"""
    text = (
        "💳 *Премиум подписка*\n\n"
        f"💰 *Стоимость:*\n"
        f"• Карта РФ: {PREMIUM_PRICE} ₽/месяц\n"
        f"• Telegram Stars: {PREMIUM_STARS_PRICE} ⭐/месяц\n\n"
        f"✅ Доступ ко всем премиум-функциям\n"
        f"⏱️ Длительность: {PREMIUM_MONTHS} месяц\n\n"
        f"Выберите способ оплаты:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💳 Карта РФ (ЮKassa)", callback_data="pay_yookassa"),
        InlineKeyboardButton(text="⭐ Telegram Stars", callback_data="pay_stars")
    )
    builder.row(
        InlineKeyboardButton(text="❓ Помощь", callback_data="payment_help"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="back_to_main")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data == "payment_help")
async def payment_help(callback: CallbackQuery):
    """Помощь по оплате"""
    text = (
        "❓ *Помощь по оплате*\n\n"
        "💳 *Оплата картой РФ:*\n"
        "• Переходите по ссылке на сайт ЮKassa\n"
        "• Вводите данные карты\n"
        "• После оплаты нажимаете '✅ Я ОПЛАТИЛ'\n\n"
        "⭐ *Оплата Telegram Stars:*\n"
        "• Stars — внутренняя валюта Telegram\n"
        "• Купить Stars можно в настройках Telegram\n"
        "• Оплата происходит мгновенно\n\n"
        "❓ *Проблемы с оплатой?*\n"
        "Напишите администратору: @hop31esss"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="payment")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ОПЛАТА ЧЕРЕЗ ЮKASSA ================

@router.callback_query(F.data == "pay_yookassa")
async def pay_yookassa(callback: CallbackQuery):
    """Оплата через ЮKassa"""
    user_id = callback.from_user.id
    
    await callback.message.edit_text("⏳ *Создаю платеж...*")
    
    # Создаем счет через ЮKassa
    payment_data = await YooKassaService.create_payment(
        amount=PREMIUM_PRICE,
        description="Премиум подписка FitnessBot на 1 месяц",
        user_id=user_id,
        return_url="https://t.me/StrengthAIBot"
    )
    
    if payment_data and payment_data.get('confirmation_url'):
        # Сохраняем ID платежа в БД (можно добавить отдельную таблицу)
        # Отправляем пользователю ссылку на оплату
        text = (
            f"💳 *Оплата через ЮKassa*\n\n"
            f"💰 Сумма: {PREMIUM_PRICE} ₽\n"
            f"📝 Назначение: Премиум подписка на 1 месяц\n\n"
            f"1️⃣ Нажмите кнопку *'ОПЛАТИТЬ'*\n"
            f"2️⃣ Введите данные карты\n"
            f"3️⃣ После оплаты нажмите *'✅ Я ОПЛАТИЛ'*\n\n"
            f"Платёж обрабатывается до 5 минут."
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="💳 ОПЛАТИТЬ", url=payment_data['confirmation_url'])
        )
        builder.row(
            InlineKeyboardButton(text="✅ Я ОПЛАТИЛ", callback_data=f"check_payment:{payment_data['id']}"),
            InlineKeyboardButton(text="❌ ОТМЕНА", callback_data="payment")
        )
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
    else:
        await callback.message.edit_text(
            "❌ *Ошибка создания платежа*\n\n"
            "Попробуйте позже или выберите другой способ оплаты.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="↩️ НАЗАД", callback_data="payment")
            ).as_markup()
        )
    
    await callback.answer()

@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment(callback: CallbackQuery):
    """Проверка статуса платежа ЮKassa"""
    payment_id = callback.data.split(":")[1]
    user_id = callback.from_user.id
    
    await callback.message.edit_text("⏳ *Проверяю статус платежа...*")
    
    status = await YooKassaService.get_payment_status(payment_id)
    
    if status == "succeeded":
        # Платеж успешен - активируем подписку
        await activate_premium(user_id, callback.bot)
        
        text = (
            "✅ *Оплата прошла успешно!*\n\n"
            "🎉 Премиум-подписка активирована!\n\n"
            "✨ *Теперь вам доступно:*\n"
            "• 🏋️ Калькулятор 1ПМ\n"
            "• 🔥 Полный трекер калорий\n"
            "• 👥 Друзья и челленджи\n"
            "• 🤖 AI-советы\n"
            "• 📊 Расширенная статистика\n\n"
            "Спасибо за поддержку! 💪"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🏋️ К ТРЕНИРОВКАМ", callback_data="training_journal"),
            InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
        )
        
        await callback.message.edit_text(text, reply_markup=builder.as_markup())
        
    elif status == "pending":
        await callback.message.edit_text(
            "⏳ *Платёж ещё обрабатывается...*\n\n"
            "Обычно это занимает до 5 минут.\n"
            "Нажмите кнопку ниже, чтобы проверить снова.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🔄 ПРОВЕРИТЬ СНОВА", callback_data=f"check_payment:{payment_id}"),
                InlineKeyboardButton(text="↩️ В МЕНЮ", callback_data="payment")
            ).as_markup()
        )
    else:
        await callback.message.edit_text(
            "❌ *Платёж не найден или отклонён*\n\n"
            "Возможные причины:\n"
            "• Недостаточно средств\n"
            "• Отмена платежа\n"
            "• Техническая ошибка\n\n"
            "Попробуйте ещё раз или выберите другой способ оплаты.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="💳 ОПЛАТИТЬ СНОВА", callback_data="pay_yookassa"),
                InlineKeyboardButton(text="↩️ В МЕНЮ", callback_data="payment")
            ).as_markup()
        )
    
    await callback.answer()

# ================ ОПЛАТА ЧЕРЕЗ TELEGRAM STARS ================

@router.callback_query(F.data == "pay_stars")
async def pay_stars(callback: CallbackQuery):
    """Покупка через Telegram Stars"""
    user_id = callback.from_user.id
    
    # Создаем счет в Stars (1 Star = 1 цент, поэтому 25 Stars = 25 рублей)
    prices = [LabeledPrice(label="Премиум подписка (1 месяц)", amount=PREMIUM_STARS_PRICE)]
    
    payload = f"premium_{user_id}_{uuid.uuid4()}"
    
    try:
        await callback.bot.send_invoice(
            chat_id=user_id,
            title="Премиум подписка FitnessBot",
            description="Доступ ко всем премиум-функциям на 1 месяц",
            payload=payload,
            provider_token="",  # Для Stars оставляем пустым
            currency="XTR",  # XTR = Telegram Stars
            prices=prices,
            start_parameter="premium-subscription"
        )
        logger.info(f"✅ Инвойс отправлен пользователю {user_id}")
    except Exception as e:
        logger.error(f"❌ Ошибка отправки инвойса: {e}")
        await callback.message.answer(
            "❌ *Ошибка создания платежа*\n\n"
            "Попробуйте позже.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="↩️ НАЗАД", callback_data="payment")
            ).as_markup()
        )
    
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_handler(pre_checkout_query: PreCheckoutQuery):
    """Проверка перед оплатой Stars"""
    await pre_checkout_query.bot.answer_pre_checkout_query(
        pre_checkout_query.id,
        ok=True
    )
    logger.info(f"✅ Pre-checkout ok for user {pre_checkout_query.from_user.id}")

@router.message(F.successful_payment)
async def successful_payment_handler(message: Message):
    """Обработка успешной оплаты Stars"""
    user_id = message.from_user.id
    payment = message.successful_payment
    
    logger.info(f"💰 Успешная оплата Stars от пользователя {user_id}: {payment.total_amount} Stars")
    
    # Активируем подписку
    await activate_premium(user_id, message.bot)
    
    text = (
        "✅ *Оплата прошла успешно!*\n\n"
        "🎉 Премиум-подписка активирована через Telegram Stars!\n\n"
        "✨ *Теперь вам доступно:*\n"
        "• 🏋️ Калькулятор 1ПМ\n"
        "• 🔥 Полный трекер калорий\n"
        "• 👥 Друзья и челленджи\n"
        "• 🤖 AI-советы\n"
        "• 📊 Расширенная статистика\n\n"
        "Спасибо за поддержку! 💪"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🏋️ К ТРЕНИРОВКАМ", callback_data="training_journal"),
        InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

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
        text = (
            "❌ *У вас нет активной подписки*\n\n"
            f"💰 Премиум: {PREMIUM_PRICE} ₽/месяц или {PREMIUM_STARS_PRICE} ⭐/месяц\n\n"
            "Нажмите кнопку ниже для покупки:"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="💳 КУПИТЬ ПРЕМИУМ", callback_data="payment")
        )
        
        await message.answer(text, reply_markup=builder.as_markup())
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
            
            text = (
                "❌ *Срок подписки истек*\n\n"
                f"📅 Действовала до: {until.strftime('%d.%m.%Y')}\n\n"
                "Продлите подписку, чтобы продолжить пользоваться премиум-функциями!"
            )
            
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="💳 ПРОДЛИТЬ", callback_data="payment")
            )
        else:
            days_left = (until - now).days
            text = (
                f"✅ *Подписка активна*\n\n"
                f"📅 Действует до: {until.strftime('%d.%m.%Y')}\n"
                f"⏳ Осталось дней: {days_left}\n\n"
                f"✨ Спасибо за поддержку! 💪"
            )
            
            builder = InlineKeyboardBuilder()
            builder.row(
                InlineKeyboardButton(text="🏋️ ПРЕМИУМ ФУНКЦИИ", callback_data="premium_features"),
                InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
            )
        
        await message.answer(text, reply_markup=builder.as_markup())
        
    except Exception as e:
        logger.error(f"Ошибка проверки статуса: {e}")
        await message.answer("❌ Ошибка при проверке статуса")