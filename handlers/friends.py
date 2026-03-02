from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database.base import db
from config import ADMIN_ID

router = Router()

class FriendStates(StatesGroup):
    waiting_friend_username = State()

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

# ================ ГЛАВНОЕ МЕНЮ ДРУЗЕЙ ================

@router.callback_query(F.data == "friends_menu")
async def friends_menu(callback: CallbackQuery):
    """Меню друзей"""
    user_id = callback.from_user.id
    
    # Проверка премиум-доступа
    if not await check_premium_access(user_id):
        await callback.answer("❌ Премиум-функция!", show_alert=True)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="👑 Премиум", callback_data="show_premium_info")
        )
        
        await callback.message.answer(
            "👑 *Премиум-доступ*\n\n"
            "Друзья и челленджи доступны только с премиум-подпиской!\n\n"
            "💰 299₽/месяц\n\n"
            "Приобрести можно у администратора: @hop31esss",
            reply_markup=builder.as_markup()
        )
        return
    
    # Получаем статистику друзей
    friends_count = await db.fetch_one(
        "SELECT COUNT(*) as count FROM friends WHERE user_id = ? AND status = 'accepted'",
        (user_id,)
    )
    
    pending_requests = await db.fetch_one(
        "SELECT COUNT(*) as count FROM friends WHERE friend_id = ? AND status = 'pending'",
        (user_id,)
    )
    
    text = (
        "👥 *Друзья*\n\n"
        f"👤 Ваши друзья: {friends_count['count'] if friends_count else 0}\n"
        f"📨 Входящие заявки: {pending_requests['count'] if pending_requests else 0}\n\n"
        "Выберите действие:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👥 Мои друзья", callback_data="my_friends"),
        InlineKeyboardButton(text="➕ Добавить друга", callback_data="add_friend")
    )
    builder.row(
        InlineKeyboardButton(text="📨 Входящие заявки", callback_data="friend_requests"),
        InlineKeyboardButton(text="↩️ В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ МОИ ДРУЗЬЯ ================

@router.callback_query(F.data == "my_friends")
async def my_friends(callback: CallbackQuery):
    """Список друзей"""
    user_id = callback.from_user.id
    
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
        text = (
            "👥 *Мои друзья*\n\n"
            "У вас пока нет друзей в боте.\n\n"
            "➕ Добавьте друга, чтобы соревноваться!"
        )
    else:
        text = f"👥 *Мои друзья* ({len(friends)})\n\n"
        for i, friend in enumerate(friends, 1):
            name = friend['username'] or friend['first_name'] or f"ID{friend['user_id']}"
            text += f"{i}. @{name}\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить друга", callback_data="add_friend"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="friends_menu")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ДОБАВЛЕНИЕ ДРУГА ================

@router.callback_query(F.data == "add_friend")
async def add_friend_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления друга"""
    await callback.message.edit_text(
        "👤 *Добавление в друзья*\n\n"
        "Введите @username пользователя, которого хотите добавить:\n"
        "Например: @username\n\n"
        "Или отправьте /cancel для отмены."
    )
    await state.set_state(FriendStates.waiting_friend_username)
    await callback.answer()

@router.message(FriendStates.waiting_friend_username)
async def process_friend_username(message: Message, state: FSMContext):
    """Обработка username для добавления в друзья"""
    username = message.text.strip()
    
    if username == "/cancel":
        await message.answer("❌ Добавление отменено.")
        await state.clear()
        return
    
    # Убираем @ если есть
    clean_username = username.replace('@', '')
    
    # Проверяем существование пользователя
    friend = await db.fetch_one(
        "SELECT user_id, first_name FROM users WHERE username = ?",
        (clean_username,)
    )
    
    if not friend:
        await message.answer(
            f"❌ Пользователь @{clean_username} не найден.\n"
            f"Убедитесь, что пользователь уже запускал бота.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="👥 К друзьям", callback_data="friends_menu")
            ).as_markup()
        )
        await state.clear()
        return
    
    user_id = message.from_user.id
    friend_id = friend['user_id']
    
    # Проверяем, не друзья ли уже
    existing = await db.fetch_one(
        """SELECT status FROM friends 
        WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)""",
        (user_id, friend_id, friend_id, user_id)
    )
    
    if existing:
        if existing['status'] == 'accepted':
            await message.answer("✅ Вы уже друзья с этим пользователем!")
        elif existing['status'] == 'pending':
            if existing['user_id'] == user_id:
                await message.answer("⏳ Вы уже отправили заявку этому пользователю.")
            else:
                await message.answer(
                    "📨 Этот пользователь уже отправил вам заявку!\n"
                    "Перейдите в 'Входящие заявки' чтобы принять её."
                )
        await state.clear()
        return
    
    # Создаем заявку в друзья
    await db.execute(
        "INSERT INTO friends (user_id, friend_id, status) VALUES (?, ?, 'pending')",
        (user_id, friend_id)
    )
    
    # Отправляем уведомление другу
    try:
        # Получаем имя отправителя
        sender = await db.fetch_one(
            "SELECT username, first_name FROM users WHERE user_id = ?",
            (user_id,)
        )
        sender_name = sender['username'] or sender['first_name'] or f"ID{user_id}"
        
        # Создаем клавиатуру для принятия заявки
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="✅ Принять заявку", 
                callback_data=f"accept_friend_request:{user_id}"
            ),
            InlineKeyboardButton(
                text="❌ Отклонить", 
                callback_data=f"reject_friend_request:{user_id}"
            )
        )
        
        await message.bot.send_message(
            friend_id,
            f"👤 *Новая заявка в друзья!*\n\n"
            f"Пользователь @{sender_name} хочет добавить вас в друзья.\n\n"
            f"Хотите принять заявку?",
            reply_markup=builder.as_markup()
        )
        
        await message.answer(
            f"✅ Заявка в друзья отправлена пользователю @{clean_username}!\n\n"
            f"Как только он примет заявку, вы получите уведомление.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="👥 К друзьям", callback_data="friends_menu")
            ).as_markup()
        )
        
    except Exception as e:
        # Если не удалось отправить уведомление (пользователь не запускал бота)
        await message.answer(
            f"✅ Заявка в друзья отправлена, но пользователь @{clean_username} ещё не запускал бота.\n"
            f"Он получит уведомление, когда запустит бота впервые.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="👥 К друзьям", callback_data="friends_menu")
            ).as_markup()
        )
    
    await state.clear()

# ================ ВХОДЯЩИЕ ЗАЯВКИ ================

@router.callback_query(F.data == "friend_requests")
async def friend_requests(callback: CallbackQuery):
    """Просмотр входящих заявок"""
    user_id = callback.from_user.id
    
    requests = await db.fetch_all("""
        SELECT f.id, u.user_id, u.username, u.first_name, f.created_at
        FROM friends f
        JOIN users u ON f.user_id = u.user_id
        WHERE f.friend_id = ? AND f.status = 'pending'
        ORDER BY f.created_at DESC
    """, (user_id,))
    
    if not requests:
        text = "📨 *Входящие заявки*\n\nУ вас нет новых заявок в друзья."
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="↩️ Назад", callback_data="friends_menu")
        )
    else:
        text = f"📨 *Входящие заявки* ({len(requests)})\n\n"
        builder = InlineKeyboardBuilder()
        
        for req in requests:
            name = req['username'] or req['first_name'] or f"ID{req['user_id']}"
            date = req['created_at'][:10] if req['created_at'] else "?"
            text += f"👤 @{name}\n"
            text += f"📅 {date}\n\n"
            
            builder.row(
                InlineKeyboardButton(
                    text=f"✅ Принять @{name}",
                    callback_data=f"accept_friend:{req['id']}"
                ),
                InlineKeyboardButton(
                    text=f"❌ Отклонить",
                    callback_data=f"reject_friend:{req['id']}"
                )
            )
        builder.row(
            InlineKeyboardButton(text="↩️ Назад", callback_data="friends_menu")
        )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ ПРИНЯТЬ ЗАЯВКУ ================

@router.callback_query(F.data.startswith("accept_friend:"))
async def accept_friend(callback: CallbackQuery):
    """Принять заявку в друзья (из списка)"""
    request_id = int(callback.data.split(":")[1])
    
    # Получаем информацию о заявке
    request = await db.fetch_one(
        "SELECT user_id, friend_id FROM friends WHERE id = ?",
        (request_id,)
    )
    
    if request:
        # Обновляем статус
        await db.execute(
            "UPDATE friends SET status = 'accepted' WHERE id = ?",
            (request_id,)
        )
        
        # Отправляем уведомление отправителю
        try:
            await callback.bot.send_message(
                request['user_id'],
                f"✅ @{callback.from_user.username or callback.from_user.first_name} принял вашу заявку в друзья!\n\n"
                f"Теперь вы можете соревноваться и участвовать в челленджах! 🏆"
            )
        except:
            pass
        
        await callback.answer("✅ Заявка принята!")
    else:
        await callback.answer("❌ Заявка не найдена")
    
    await friend_requests(callback)

# ================ ПРИНЯТЬ ЗАЯВКУ (ПРЯМАЯ) ================

@router.callback_query(F.data.startswith("accept_friend_request:"))
async def accept_friend_request(callback: CallbackQuery):
    """Принять заявку в друзья (из уведомления)"""
    requester_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # Находим заявку
    request = await db.fetch_one(
        "SELECT id FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'pending'",
        (requester_id, user_id)
    )
    
    if request:
        await db.execute(
            "UPDATE friends SET status = 'accepted' WHERE id = ?",
            (request['id'],)
        )
        
        # Отправляем уведомление отправителю
        try:
            await callback.bot.send_message(
                requester_id,
                f"✅ @{callback.from_user.username or callback.from_user.first_name} принял вашу заявку в друзья!\n\n"
                f"Теперь вы можете соревноваться и участвовать в челленджах! 🏆"
            )
        except:
            pass
        
        await callback.message.edit_text(
            "✅ *Заявка принята!*\n\n"
            "Теперь вы друзья с этим пользователем."
        )
        await callback.answer("✅ Заявка принята!")
    else:
        await callback.answer("❌ Заявка не найдена")

# ================ ОТКЛОНИТЬ ЗАЯВКУ ================

@router.callback_query(F.data.startswith("reject_friend:"))
async def reject_friend(callback: CallbackQuery):
    """Отклонить заявку в друзья"""
    request_id = int(callback.data.split(":")[1])
    
    # Удаляем заявку
    await db.execute("DELETE FROM friends WHERE id = ?", (request_id,))
    
    await callback.answer("❌ Заявка отклонена")
    await friend_requests(callback)

@router.callback_query(F.data.startswith("reject_friend_request:"))
async def reject_friend_request(callback: CallbackQuery):
    """Отклонить заявку из уведомления"""
    requester_id = int(callback.data.split(":")[1])
    user_id = callback.from_user.id
    
    # Удаляем заявку
    await db.execute(
        "DELETE FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'pending'",
        (requester_id, user_id)
    )
    
    await callback.message.edit_text("❌ Заявка отклонена.")
    await callback.answer("❌ Заявка отклонена")