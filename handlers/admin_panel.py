from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta
from config import ADMIN_ID
from handlers.admin_panel import router as admin_panel_router
import logging
logger = logging.getLogger(__name__)

import asyncio

from database.base import db

router = Router()

# ВАШ РЕАЛЬНЫЙ ID (ТОЛЬКО ОН ИМЕЕТ ДОСТУП)
ADMIN_USER_ID = 385450652

# Состояния для FSM
class BroadcastStates(StatesGroup):
    waiting_message = State()
    waiting_confirm = State()

class PremiumGrantStates(StatesGroup):
    waiting_user_id = State()
    waiting_days = State()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Вход в админ-панель"""
    user_id = message.from_user.id
    logger.info(f"🔍 admin_panel вызвана пользователем {user_id}")
    
    if user_id != ADMIN_ID:
        logger.warning(f"❌ Доступ запрещён для {user_id}")
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    logger.info(f"✅ Доступ разрешён для {user_id}")
    # ... остальной код ...

# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================

def get_broadcast_confirmation_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ ОТПРАВИТЬ", callback_data="confirm_send"),
        InlineKeyboardButton(text="❌ ОТМЕНИТЬ", callback_data="cancel_send")
    )
    return builder.as_markup()

def get_admin_back_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ В админ-панель", callback_data="admin_panel")
    )
    return builder.as_markup()

# ================ ГЛАВНОЕ МЕНЮ АДМИНА ================

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Вход в админ-панель"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        await message.answer("❌ У вас нет доступа к админ-панели.")
        return
    
    text = (
        "⚙️ *АДМИН-ПАНЕЛЬ*\n\n"
        "👑 Добро пожаловать, администратор!\n\n"
        "*Доступные действия:*\n"
        "📊 • Статистика бота\n"
        "👥 • Список пользователей\n"
        "👑 • Управление премиум-доступом\n"
        "📢 • Рассылка сообщений"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="👥 Пользователи", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="👑 Премиум", callback_data="admin_premium_menu"),
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast_menu")
    )
    builder.row(
        InlineKeyboardButton(text="👋 Выход", callback_data="back_to_main")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

# ================ СТАТИСТИКА ================

@router.callback_query(F.data == "admin_stats")
async def admin_stats_handler(callback: CallbackQuery):
    """Статистика бота"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    users_count = await db.fetch_one("SELECT COUNT(*) as count FROM users")
    workouts_count = await db.fetch_one("SELECT COUNT(*) as count FROM workouts")
    premium_count = await db.fetch_one("SELECT COUNT(*) as count FROM users WHERE is_subscribed = TRUE")
    
    today = datetime.now().date().isoformat()
    active_today = await db.fetch_one(
        "SELECT COUNT(DISTINCT user_id) as count FROM workouts WHERE date(created_at) = ?",
        (today,)
    )
    
    text = (
        f"📊 *Статистика бота*\n\n"
        f"👥 Всего пользователей: {users_count['count'] if users_count else 0}\n"
        f"👑 Премиум пользователей: {premium_count['count'] if premium_count else 0}\n"
        f"🏋️ Всего тренировок: {workouts_count['count'] if workouts_count else 0}\n"
        f"🔥 Активных сегодня: {active_today['count'] if active_today else 0}\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_stats"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="admin_panel")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ПОЛЬЗОВАТЕЛИ ================

@router.callback_query(F.data == "admin_users")
async def admin_users_handler(callback: CallbackQuery):
    """Список пользователей"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    users = await db.fetch_all("""
        SELECT user_id, username, first_name, created_at, is_subscribed,
               subscription_until,
               (SELECT COUNT(*) FROM workouts WHERE user_id = users.user_id) as workout_count
        FROM users
        ORDER BY created_at DESC
        LIMIT 10
    """)
    
    text = "👥 *Последние 10 пользователей*\n\n"
    
    for i, user in enumerate(users, 1):
        name = user['username'] or user['first_name'] or f"ID{user['user_id']}"
        date = user['created_at'][:10] if user['created_at'] else "?"
        
        if user['is_subscribed'] and user['subscription_until']:
            until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
            if datetime.now() <= until:
                premium_status = "✅ Премиум"
            else:
                premium_status = "❌ Истек"
        else:
            premium_status = "❌ Нет"
        
        text += f"{i}. {name}\n"
        text += f"   ID: `{user['user_id']}` | Тренировок: {user['workout_count']} | {premium_status}\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Обновить", callback_data="admin_users"),
        InlineKeyboardButton(text="👑 Управление премиум", callback_data="admin_premium_menu")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="admin_panel")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ УПРАВЛЕНИЕ ПРЕМИУМ ================

@router.callback_query(F.data == "admin_premium_menu")
async def admin_premium_menu(callback: CallbackQuery):
    """Меню управления премиум"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = (
        "👑 *Управление премиум-доступом*\n\n"
        "Выберите действие:\n\n"
        "1️⃣ Выдать премиум пользователю\n"
        "2️⃣ Продлить премиум\n"
        "3️⃣ Забрать премиум\n"
        "4️⃣ Список премиум-пользователей"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1️⃣ Выдать", callback_data="premium_grant"),
        InlineKeyboardButton(text="2️⃣ Продлить", callback_data="premium_extend"),
        InlineKeyboardButton(text="3️⃣ Забрать", callback_data="premium_revoke")
    )
    builder.row(
        InlineKeyboardButton(text="4️⃣ Список", callback_data="premium_list"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="admin_panel")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ СПИСОК ПРЕМИУМ-ПОЛЬЗОВАТЕЛЕЙ ================

@router.callback_query(F.data == "premium_list")
async def premium_list(callback: CallbackQuery):
    """Список премиум-пользователей"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    premium_users = await db.fetch_all("""
        SELECT user_id, username, first_name, subscription_until
        FROM users
        WHERE is_subscribed = TRUE
        ORDER BY subscription_until DESC
    """)
    
    if not premium_users:
        text = "👑 *Премиум-пользователи*\n\n❌ Нет пользователей с премиум-доступом."
    else:
        text = f"👑 *Премиум-пользователи* ({len(premium_users)})\n\n"
        
        for i, user in enumerate(premium_users, 1):
            name = user['username'] or user['first_name'] or f"ID{user['user_id']}"
            until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
            days_left = (until - datetime.now()).days
            
            text += f"{i}. {name}\n"
            text += f"   ID: `{user['user_id']}` | До: {until.strftime('%d.%m.%Y')} (осталось {days_left} дн.)\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="admin_premium_menu")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ВЫДАТЬ ПРЕМИУМ ================

@router.callback_query(F.data == "premium_grant")
async def premium_grant_start(callback: CallbackQuery, state: FSMContext):
    """Начало выдачи премиум"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👑 *Выдача премиум-доступа*\n\n"
        "Введите Telegram ID пользователя, которому хотите выдать премиум:\n\n"
        "Или отправьте /cancel для отмены."
    )
    
    await state.set_state(PremiumGrantStates.waiting_user_id)
    await callback.answer()

@router.message(PremiumGrantStates.waiting_user_id)
async def process_premium_user_id(message: Message, state: FSMContext):
    """Обработка ID пользователя"""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("❌ Нет доступа")
        await state.clear()
        return
    
    if message.text == "/cancel":
        await message.answer("❌ Операция отменена.")
        await state.clear()
        return
    
    try:
        target_user_id = int(message.text.strip())
        await state.update_data(target_user_id=target_user_id)
        
        # Проверяем, существует ли пользователь
        user = await db.fetch_one(
            "SELECT user_id, username, first_name FROM users WHERE user_id = ?",
            (target_user_id,)
        )
        
        if user:
            name = user['username'] or user['first_name'] or f"ID{target_user_id}"
            await message.answer(
                f"✅ Пользователь найден: {name}\n\n"
                f"Введите количество дней (от 1 до 365):"
            )
        else:
            await message.answer(
                f"⚠️ Пользователь с ID {target_user_id} не найден в базе.\n"
                f"Всё равно выдать премиум? (он сможет активировать после запуска бота)\n\n"
                f"Введите количество дней (от 1 до 365):"
            )
        
        await state.set_state(PremiumGrantStates.waiting_days)
        
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число:")

@router.message(PremiumGrantStates.waiting_days)
async def process_premium_days(message: Message, state: FSMContext):
    """Обработка количества дней"""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("❌ Нет доступа")
        await state.clear()
        return
    
    try:
        days = int(message.text.strip())
        if days < 1 or days > 365:
            raise ValueError
        
        data = await state.get_data()
        target_user_id = data['target_user_id']
        
        # Рассчитываем дату окончания
        until = datetime.now() + timedelta(days=days)
        
        # Сохраняем в базу
        await db.execute(
            """INSERT INTO users (user_id, is_subscribed, subscription_until) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
            is_subscribed = TRUE, subscription_until = ?""",
            (target_user_id, True, until.isoformat(), until.isoformat())
        )
        
        # Отправляем уведомление пользователю
        try:
            await message.bot.send_message(
                target_user_id,
                f"🎁 *Вам выдан премиум-доступ!*\n\n"
                f"Администратор выдал вам премиум на {days} дней.\n"
                f"✅ Действует до: {until.strftime('%d.%m.%Y')}\n\n"
                f"Теперь вам доступны все премиум-функции бота! 💪"
            )
            notify_status = "✅ Уведомление отправлено"
        except:
            notify_status = "⚠️ Не удалось отправить уведомление (пользователь не запускал бота)"
        
        await message.answer(
            f"✅ *Премиум выдан!*\n\n"
            f"Пользователь: `{target_user_id}`\n"
            f"Срок: {days} дней\n"
            f"Действует до: {until.strftime('%d.%m.%Y')}\n"
            f"{notify_status}",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="👑 Управление премиум", callback_data="admin_premium_menu")
            ).as_markup()
        )
        
    except ValueError:
        await message.answer("❌ Введите корректное число дней (от 1 до 365):")
        return
    
    await state.clear()

# ================ ЗАБРАТЬ ПРЕМИУМ ================

@router.callback_query(F.data == "premium_revoke")
async def premium_revoke_start(callback: CallbackQuery, state: FSMContext):
    """Начало отзыва премиум"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👑 *Отзыв премиум-доступа*\n\n"
        "Введите Telegram ID пользователя, у которого хотите забрать премиум:"
    )
    
    await state.set_state(PremiumGrantStates.waiting_user_id)
    await callback.answer()

# Используем тот же обработчик message, но с проверкой на отзыв
@router.message(PremiumGrantStates.waiting_user_id)
async def process_revoke_user_id(message: Message, state: FSMContext):
    """Обработка отзыва премиум"""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("❌ Нет доступа")
        await state.clear()
        return
    
    try:
        target_user_id = int(message.text.strip())
        
        # Забираем премиум
        await db.execute(
            "UPDATE users SET is_subscribed = FALSE, subscription_until = NULL WHERE user_id = ?",
            (target_user_id,)
        )
        
        # Отправляем уведомление
        try:
            await message.bot.send_message(
                target_user_id,
                f"⚠️ *Премиум-доступ отозван*\n\n"
                f"Администратор отозвал ваш премиум-доступ.\n"
                f"Спасибо за использование бота! 🙏"
            )
            notify_status = "✅ Уведомление отправлено"
        except:
            notify_status = "⚠️ Не удалось отправить уведомление"
        
        await message.answer(
            f"✅ *Премиум отозван!*\n\n"
            f"Пользователь: `{target_user_id}`\n"
            f"{notify_status}",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="👑 Управление премиум", callback_data="admin_premium_menu")
            ).as_markup()
        )
        
    except ValueError:
        await message.answer("❌ Неверный формат ID. Введите число:")
        return
    
    await state.clear()

# ================ ПРОДЛИТЬ ПРЕМИУМ ================

@router.callback_query(F.data == "premium_extend")
async def premium_extend_start(callback: CallbackQuery, state: FSMContext):
    """Начало продления премиум"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text(
        "👑 *Продление премиум-доступа*\n\n"
        "Введите Telegram ID пользователя, которому хотите продлить премиум:"
    )
    
    await state.set_state(PremiumGrantStates.waiting_user_id)
    await callback.answer()

# ================ МЕНЮ РАССЫЛКИ ================

@router.callback_query(F.data == "admin_broadcast_menu")
async def admin_broadcast_menu(callback: CallbackQuery):
    """Меню рассылки"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    text = (
        "📢 *Рассылка сообщений*\n\n"
        "Выберите тип рассылки:\n\n"
        "1️⃣ Всем пользователям\n"
        "2️⃣ Только премиум-пользователям\n"
        "3️⃣ Тестовая (только себе)"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1️⃣ Всем", callback_data="broadcast_all"),
        InlineKeyboardButton(text="2️⃣ Премиум", callback_data="broadcast_premium"),
        InlineKeyboardButton(text="3️⃣ Тест", callback_data="broadcast_test")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="admin_panel")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.in_(["broadcast_all", "broadcast_premium", "broadcast_test"]))
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начало создания рассылки"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    # Определяем тип рассылки
    if callback.data == "broadcast_all":
        broadcast_type = "all"
        type_text = "Всем пользователям"
    elif callback.data == "broadcast_premium":
        broadcast_type = "premium"
        type_text = "Только премиум"
    else:
        broadcast_type = "test"
        type_text = "Тестовая (только себе)"
    
    await state.update_data(broadcast_type=broadcast_type)
    
    await callback.message.edit_text(
        f"📢 *Создание рассылки*\n\n"
        f"Тип рассылки: {type_text}\n\n"
        f"Введите текст сообщения для отправки:\n\n"
        f"Поддерживается Markdown:\n"
        f"• *жирный*\n"
        f"• _курсив_\n"
        f"• `код`\n"
        f"• [ссылка](https://example.com)\n\n"
        f"Или отправьте /cancel для отмены."
    )
    
    await state.set_state(BroadcastStates.waiting_message)
    await callback.answer()

@router.message(BroadcastStates.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    if message.from_user.id != ADMIN_USER_ID:
        await message.answer("❌ Нет доступа")
        await state.clear()
        return
    
    if message.text == "/cancel":
        await message.answer("❌ Рассылка отменена.")
        await state.clear()
        return
    
    broadcast_text = message.text
    data = await state.get_data()
    broadcast_type = data.get('broadcast_type')
    
    await state.update_data(broadcast_text=broadcast_text)
    
    # Определяем получателей для предпросмотра
    if broadcast_type == "test":
        recipients_text = "👤 Только вы"
        recipients_count = 1
    elif broadcast_type == "premium":
        users = await db.fetch_all("SELECT COUNT(*) as count FROM users WHERE is_subscribed = TRUE")
        recipients_count = users[0]['count'] if users else 0
        recipients_text = f"👥 {recipients_count} премиум-пользователей"
    else:
        users = await db.fetch_all("SELECT COUNT(*) as count FROM users")
        recipients_count = users[0]['count'] if users else 0
        recipients_text = f"👥 {recipients_count} пользователей"
    
    preview_text = (
        f"📋 *ПРЕДПРОСМОТР РАССЫЛКИ*\n\n"
        f"{broadcast_text}\n\n"
        f"*Детали:*\n"
        f"• Тип: {broadcast_type}\n"
        f"• Получатели: {recipients_text}\n"
        f"• Длина: {len(broadcast_text)} символов\n\n"
        f"❗️ *ВНИМАНИЕ:* Это сообщение будет отправлено {recipients_count} пользователям!\n\n"
        f"Отправить?"
    )
    
    confirm_builder = InlineKeyboardBuilder()
    confirm_builder.row(
        InlineKeyboardButton(text="✅ ДА, ОТПРАВИТЬ", callback_data="confirm_send"),
        InlineKeyboardButton(text="❌ НЕТ, ОТМЕНИТЬ", callback_data="cancel_send")
    )
    
    await message.answer(preview_text, reply_markup=confirm_builder.as_markup())
    await state.set_state(BroadcastStates.waiting_confirm)

@router.callback_query(F.data == "confirm_send")
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и отправка рассылки"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    data = await state.get_data()
    broadcast_text = data.get('broadcast_text')
    broadcast_type = data.get('broadcast_type')
    
    if not broadcast_text:
        await callback.message.edit_text("❌ Ошибка: текст сообщения не найден.")
        await state.clear()
        return
    
    # Получаем список получателей
    if broadcast_type == "test":
        user_ids = [callback.from_user.id]
        type_name = "тестовая рассылка"
    elif broadcast_type == "premium":
        users = await db.fetch_all("SELECT user_id FROM users WHERE is_subscribed = TRUE")
        user_ids = [user['user_id'] for user in users]
        type_name = "рассылка для премиум"
    else:
        users = await db.fetch_all("SELECT user_id FROM users")
        user_ids = [user['user_id'] for user in users]
        type_name = "массовая рассылка"
    
    total = len(user_ids)
    
    if total == 0:
        await callback.message.edit_text("❌ Нет получателей для рассылки.")
        await state.clear()
        return
    
    await callback.message.edit_text(f"📤 *Начинаю {type_name}...*\n\nВсего получателей: {total}")
    
    success = 0
    failed = 0
    
    for target_id in user_ids:
        try:
            await callback.bot.send_message(target_id, broadcast_text)
            success += 1
            await asyncio.sleep(0.03)
        except:
            failed += 1
    
    result_text = (
        f"✅ *Рассылка завершена!*\n\n"
        f"📊 *Статистика:*\n"
        f"• Всего: {total}\n"
        f"• Успешно: {success}\n"
        f"• Ошибок: {failed}\n\n"
        f"📝 *Текст:*\n{broadcast_text}"
    )
    
    await callback.message.answer(result_text, reply_markup=get_admin_back_keyboard())
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "cancel_send")
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await callback.message.edit_text("❌ Рассылка отменена.")
    await state.clear()
    await callback.answer()

# ================ ВОЗВРАТ В АДМИН-ПАНЕЛЬ ================

@router.callback_query(F.data == "admin_panel")
async def back_to_admin(callback: CallbackQuery):
    """Возврат в админ-панель"""
    if callback.from_user.id != ADMIN_USER_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    await admin_panel(callback.message)
    await callback.answer()