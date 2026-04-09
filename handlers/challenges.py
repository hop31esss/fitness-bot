from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, timedelta

from database.base import db
from config import ADMIN_ID

router = Router()

class ChallengeStates(StatesGroup):
    choosing_friend = State()
    entering_name = State()
    choosing_type = State()
    entering_exercise = State()
    entering_goal = State()
    entering_days = State()


@router.callback_query(F.data.startswith("challenge_friend:"))
async def challenge_friend_chosen(callback: CallbackQuery, state: FSMContext):
    """Выбор друга для челленджа"""
    friend_id = int(callback.data.split(":")[1])
    await state.update_data(friend_id=friend_id)
    
    await callback.message.edit_text(
        "📝 *Название челленджа*\n\n"
        "Придумайте название для вашего челленджа:\n"
        "Например: 'Кто больше подтянется'"
    )
    await state.set_state(ChallengeStates.entering_name)
    await callback.answer()

@router.message(ChallengeStates.entering_name)
async def challenge_enter_name(message: Message, state: FSMContext):
    """Ввод названия челленджа"""
    name = message.text.strip()
    await state.update_data(name=name)
    
    text = (
        "🎯 *Тип челленджа*\n\n"
        "Выберите, по чему будем соревноваться:\n\n"
        "1️⃣ Количество тренировок\n"
        "2️⃣ Общий объем (кг)\n"
        "3️⃣ Количество подходов\n"
        "4️⃣ Конкретное упражнение"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="1️⃣ Тренировки", callback_data="challenge_type:workouts"),
        InlineKeyboardButton(text="2️⃣ Объем", callback_data="challenge_type:volume")
    )
    builder.row(
        InlineKeyboardButton(text="3️⃣ Подходы", callback_data="challenge_type:sets"),
        InlineKeyboardButton(text="4️⃣ Упражнение", callback_data="challenge_type:exercise")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())
    await state.set_state(ChallengeStates.choosing_type)

@router.callback_query(F.data.startswith("challenge_type:"))
async def challenge_choose_type(callback: CallbackQuery, state: FSMContext):
    """Выбор типа челленджа"""
    challenge_type = callback.data.split(":")[1]
    await state.update_data(challenge_type=challenge_type)
    
    if challenge_type == "exercise":
        await callback.message.edit_text(
            "💪 *Введите упражнение*\n\n"
            "Например: 'Подтягивания', 'Жим лежа', 'Приседания'"
        )
        await state.set_state(ChallengeStates.entering_exercise)
    else:
        # Для остальных типов - сразу запрашиваем цель
        units = {
            "workouts": "тренировок",
            "volume": "кг",
            "sets": "подходов"
        }
        unit = units.get(challenge_type, "")
        await state.update_data(unit=unit)
        
        await callback.message.edit_text(
            f"🎯 *Цель челленджа*\n\n"
            f"Введите цель (в {unit}):\n"
            f"Например: 10, 20, 30"
        )
        await state.set_state(ChallengeStates.entering_goal)
    
    await callback.answer()

@router.message(ChallengeStates.entering_exercise)
async def challenge_enter_exercise(message: Message, state: FSMContext):
    """Ввод упражнения для челленджа"""
    exercise = message.text.strip()
    await state.update_data(exercise=exercise, unit="раз")
    
    await message.answer(
        f"🎯 *Цель челленджа*\n\n"
        f"Сколько {exercise} нужно сделать?\n"
        f"Например: 50, 100, 200"
    )
    await state.set_state(ChallengeStates.entering_goal)

@router.message(ChallengeStates.entering_goal)
async def challenge_enter_goal(message: Message, state: FSMContext):
    """Ввод цели челленджа"""
    try:
        goal = int(message.text)
        if goal <= 0:
            raise ValueError
        await state.update_data(goal=goal)
        
        await message.answer(
            "⏳ *Длительность челленджа*\n\n"
            "На сколько дней?\n"
            "Например: 7, 14, 30"
        )
        await state.set_state(ChallengeStates.entering_days)
    except ValueError:
        await message.answer("❌ Введите положительное число")

@router.message(ChallengeStates.entering_days)
async def challenge_enter_days(message: Message, state: FSMContext):
    """Ввод длительности челленджа"""
    try:
        days = int(message.text)
        if days <= 0:
            raise ValueError
        
        data = await state.get_data()
        user_id = message.from_user.id
        friend_id = data['friend_id']
        
        # Создаем челлендж в базе
        await db.execute("""
            INSERT INTO challenges (
                user1_id, user2_id, name, type, exercise, goal, unit, status, created_at, end_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?)
        """, (
            user_id, friend_id,
            data['name'],
            data['challenge_type'],
            data.get('exercise'),
            data['goal'],
            data.get('unit', 'раз'),
            datetime.now().isoformat(),
            (datetime.now() + timedelta(days=days)).isoformat()
        ))
        
        # Отправляем уведомление другу
        try:
            await message.bot.send_message(
                friend_id,
                f"⚔️ *Новый челлендж!*\n\n"
                f"@{message.from_user.username} бросил вам вызов!\n\n"
                f"🏆 {data['name']}\n"
                f"🎯 Цель: {data['goal']} {data.get('unit', 'раз')}\n"
                f"⏳ {days} дней\n\n"
                f"Примите вызов в разделе 'Челленджи'!"
            )
        except Exception:
            pass
        
        await message.answer(
            "✅ *Челлендж создан!*\n\n"
            "Удачи в соревновании! 💪",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="🏆 К ЧЕЛЛЕНДЖАМ", callback_data="challenges_menu")
            ).as_markup()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите положительное число")

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