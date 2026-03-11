from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, date, timedelta
import logging

from config import FATSECRET_CLIENT_ID, FATSECRET_CLIENT_SECRET, USE_FATSECRET
from services.fatsecret_service import FatSecretService
from database.base import db
from config import ADMIN_ID

router = Router()
logger = logging.getLogger(__name__)

# ================ СОСТОЯНИЯ ================

class CalorieStates(StatesGroup):
    waiting_gender = State()
    waiting_age = State()
    waiting_weight = State()
    waiting_height = State()
    waiting_activity = State()
    waiting_goal = State()
    waiting_food_name = State()
    waiting_food_calories = State()
    waiting_food_amount = State()
    waiting_food_protein = State()
    waiting_food_fat = State()
    waiting_food_carbs = State()

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

# ================ БАЗА ПРОДУКТОВ ================

FOOD_DATABASE = {
    # Завтрак
    "овсянка": {"calories": 350, "protein": 12, "fat": 6, "carbs": 60, "unit": "г"},
    "гречка": {"calories": 330, "protein": 13, "fat": 3, "carbs": 68, "unit": "г"},
    "рис": {"calories": 360, "protein": 7, "fat": 1, "carbs": 79, "unit": "г"},
    "яйца": {"calories": 155, "protein": 13, "fat": 11, "carbs": 1, "unit": "шт"},
    "творог": {"calories": 120, "protein": 18, "fat": 5, "carbs": 3, "unit": "г"},
    
    # Мясо
    "курица": {"calories": 165, "protein": 31, "fat": 3.6, "carbs": 0, "unit": "г"},
    "говядина": {"calories": 250, "protein": 26, "fat": 17, "carbs": 0, "unit": "г"},
    "индейка": {"calories": 135, "protein": 29, "fat": 1, "carbs": 0, "unit": "г"},
    "рыба": {"calories": 150, "protein": 22, "fat": 6, "carbs": 0, "unit": "г"},
    
    # Овощи
    "картофель": {"calories": 77, "protein": 2, "fat": 0.1, "carbs": 17, "unit": "г"},
    "брокколи": {"calories": 34, "protein": 2.8, "fat": 0.4, "carbs": 6.6, "unit": "г"},
    "помидоры": {"calories": 20, "protein": 1, "fat": 0.2, "carbs": 4, "unit": "г"},
    "огурцы": {"calories": 15, "protein": 0.7, "fat": 0.1, "carbs": 3, "unit": "г"},
    
    # Фрукты
    "банан": {"calories": 95, "protein": 1.3, "fat": 0.3, "carbs": 24, "unit": "шт"},
    "яблоко": {"calories": 52, "protein": 0.3, "fat": 0.2, "carbs": 14, "unit": "шт"},
    "апельсин": {"calories": 47, "protein": 0.9, "fat": 0.1, "carbs": 12, "unit": "шт"},
    
    # Напитки
    "кофе": {"calories": 2, "protein": 0.1, "fat": 0, "carbs": 0, "unit": "чашка"},
    "чай": {"calories": 1, "protein": 0, "fat": 0, "carbs": 0, "unit": "чашка"},
    "сок": {"calories": 45, "protein": 0.5, "fat": 0, "carbs": 11, "unit": "мл"},
}

# Коэффициенты активности
ACTIVITY_LEVELS = {
    "1.2": {"name": "🪑 Сидячий", "desc": "Офисная работа, нет спорта"},
    "1.375": {"name": "🚶 Легкий", "desc": "Тренировки 1-3 раза в неделю"},
    "1.55": {"name": "🏋️ Средний", "desc": "Тренировки 3-5 раз в неделю"},
    "1.725": {"name": "🔥 Высокий", "desc": "Тренировки 6-7 раз в неделю"},
    "1.9": {"name": "⚡ Экстра", "desc": "Физическая работа + спорт"}
}

# Цели
GOALS = {
    "lose": {"name": "⬇️ Похудение", "adjustment": -0.15},
    "maintain": {"name": "➡️ Поддержание", "adjustment": 0},
    "gain": {"name": "⬆️ Набор массы", "adjustment": 0.15}
}

# ================ ГЛАВНОЕ МЕНЮ ================

@router.callback_query(F.data == "calorie_tracker")
async def calorie_tracker_menu(callback: CallbackQuery):
    """Главное меню трекера калорий"""
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
            "Трекер калорий доступен только с премиум-подпиской!\n\n"
            "💰 150₽/месяц",
            reply_markup=builder.as_markup()
        )
        return
    
    # Получаем данные за сегодня
    today_date = date.today().isoformat()
    
    # Получаем норму пользователя
    norm = await db.fetch_one(
        "SELECT calories, protein, fat, carbs FROM calorie_norms WHERE user_id = ?",
        (user_id,)
    )
    
    # Получаем сегодняшние записи
    today_entries = await db.fetch_all(
        """SELECT food_name, amount, unit, calories, protein, fat, carbs 
           FROM food_entries 
           WHERE user_id = ? AND date = ? 
           ORDER BY created_at""",
        (user_id, today_date)
    )
    
    # Считаем итоги
    total_calories = sum(e['calories'] for e in today_entries) if today_entries else 0
    total_protein = sum(e['protein'] or 0 for e in today_entries) if today_entries else 0
    total_fat = sum(e['fat'] or 0 for e in today_entries) if today_entries else 0
    total_carbs = sum(e['carbs'] or 0 for e in today_entries) if today_entries else 0
    
    # Формируем текст
    if norm:
        remaining = norm['calories'] - total_calories
        remaining_color = "✅" if remaining >= 0 else "⚠️"
        
        text = (
            f"🔥 *Трекер калорий*\n\n"
            f"📅 *Сегодня:* {today_date}\n"
            f"⚡ *Потреблено:* {total_calories} ккал\n"
            f"🎯 *Норма:* {norm['calories']} ккал\n"
            f"{remaining_color} *Осталось:* {remaining} ккал\n\n"
            f"🍗 *Белки:* {total_protein:.0f}/{norm['protein']} г\n"
            f"🥑 *Жиры:* {total_fat:.0f}/{norm['fat']} г\n"
            f"🍚 *Углеводы:* {total_carbs:.0f}/{norm['carbs']} г\n"
        )
    else:
        text = (
            f"🔥 *Трекер калорий*\n\n"
            f"📅 *Сегодня:* {today_date}\n"
            f"⚡ *Потреблено:* {total_calories} ккал\n\n"
            f"📝 У вас еще не рассчитана норма калорий.\n"
            f"Нажмите '📊 Моя норма' для расчета!"
        )
    
    if today_entries:
        text += "\n📋 *Сегодня съедено:*\n"
        for e in today_entries:
            text += f"• {e['food_name']}: {e['amount']}{e['unit']} ({e['calories']} ккал)\n"
    
    # Клавиатура
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ ЕДУ", callback_data="add_food_menu"),
        InlineKeyboardButton(text="📊 МОЯ НОРМА", callback_data="calculate_norm")
    )
    builder.row(
        InlineKeyboardButton(text="📖 БАЗА ПРОДУКТОВ", callback_data="food_database"),
        InlineKeyboardButton(text="📊 ИСТОРИЯ", callback_data="calorie_history")
    )
    #builder.row(
    #    InlineKeyboardButton(text="🔍 ПОИСК ПРОДУКТОВ", callback_data="search_food")
    #)
    builder.row(
        InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ РАСЧЕТ НОРМЫ ================

@router.callback_query(F.data == "calculate_norm")
async def calculate_norm_start(callback: CallbackQuery, state: FSMContext):
    """Начало расчета нормы калорий"""
    await callback.message.edit_text(
        "👤 *Расчет нормы калорий*\n\n"
        "Шаг 1/5: Выберите ваш пол:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👨 Мужской", callback_data="gender:male"),
        InlineKeyboardButton(text="👩 Женский", callback_data="gender:female")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ ОТМЕНА", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_reply_markup(reply_markup=builder.as_markup())
    await state.set_state(CalorieStates.waiting_gender)
    await callback.answer()

@router.callback_query(CalorieStates.waiting_gender, F.data.startswith("gender:"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    """Обработка пола"""
    gender = callback.data.split(":")[1]
    await state.update_data(gender=gender)
    
    await callback.message.edit_text(
        "📅 *Расчет нормы калорий*\n\n"
        "Шаг 2/5: Введите ваш возраст (лет):"
    )
    await state.set_state(CalorieStates.waiting_age)
    await callback.answer()

@router.message(CalorieStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    """Обработка возраста"""
    try:
        age = int(message.text)
        if age < 10 or age > 120:
            raise ValueError
        await state.update_data(age=age)
        
        await message.answer(
            "⚖️ *Расчет нормы калорий*\n\n"
            "Шаг 3/5: Введите ваш вес (кг):"
        )
        await state.set_state(CalorieStates.waiting_weight)
    except ValueError:
        await message.answer("❌ Введите корректный возраст (10-120 лет)")

@router.message(CalorieStates.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса"""
    try:
        weight = float(message.text.replace(',', '.'))
        if weight < 20 or weight > 300:
            raise ValueError
        await state.update_data(weight=weight)
        
        await message.answer(
            "📏 *Расчет нормы калорий*\n\n"
            "Шаг 4/5: Введите ваш рост (см):"
        )
        await state.set_state(CalorieStates.waiting_height)
    except ValueError:
        await message.answer("❌ Введите корректный вес (20-300 кг)")

@router.message(CalorieStates.waiting_height)
async def process_height(message: Message, state: FSMContext):
    """Обработка роста"""
    try:
        height = float(message.text.replace(',', '.'))
        if height < 100 or height > 250:
            raise ValueError
        await state.update_data(height=height)
        
        text = "🏃 *Расчет нормы калорий*\n\n"
        text += "Шаг 5/5: Выберите уровень активности:\n\n"
        
        builder = InlineKeyboardBuilder()
        for coef, data in ACTIVITY_LEVELS.items():
            builder.row(
                InlineKeyboardButton(
                    text=f"{data['name']} - {data['desc']}",
                    callback_data=f"activity:{coef}"
                )
            )
        builder.row(
            InlineKeyboardButton(text="↩️ ОТМЕНА", callback_data="calorie_tracker")
        )
        
        await message.answer(text, reply_markup=builder.as_markup())
        await state.set_state(CalorieStates.waiting_activity)
    except ValueError:
        await message.answer("❌ Введите корректный рост (100-250 см)")

@router.callback_query(CalorieStates.waiting_activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext):
    """Обработка активности"""
    activity = float(callback.data.split(":")[1])
    await state.update_data(activity=activity)
    
    text = "🎯 *Расчет нормы калорий*\n\n"
    text += "Выберите вашу цель:\n\n"
    
    builder = InlineKeyboardBuilder()
    for goal_id, goal_data in GOALS.items():
        builder.row(
            InlineKeyboardButton(
                text=goal_data['name'],
                callback_data=f"goal:{goal_id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="↩️ ОТМЕНА", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(CalorieStates.waiting_goal)
    await callback.answer()

@router.callback_query(CalorieStates.waiting_goal, F.data.startswith("goal:"))
async def process_goal(callback: CallbackQuery, state: FSMContext):
    """Расчет и сохранение нормы"""
    goal = callback.data.split(":")[1]
    
    data = await state.get_data()
    
    # Расчет BMR по формуле Миффлина-Сан Жеора
    if data['gender'] == 'male':
        bmr = (10 * data['weight']) + (6.25 * data['height']) - (5 * data['age']) + 5
    else:
        bmr = (10 * data['weight']) + (6.25 * data['height']) - (5 * data['age']) - 161
    
    # Учет активности
    tdee = bmr * data['activity']
    
    # Учет цели
    goal_adjustment = GOALS[goal]['adjustment']
    final_calories = int(tdee * (1 + goal_adjustment))
    
    # Расчет БЖУ
    protein = int(data['weight'] * 2.0)  # 2г на кг веса
    fat = int(data['weight'] * 1.0)      # 1г на кг веса
    carbs = int((final_calories - (protein * 4 + fat * 9)) / 4)
    
    # Сохраняем норму
    user_id = callback.from_user.id
    
    await db.execute("""
        INSERT OR REPLACE INTO calorie_norms 
        (user_id, calories, protein, fat, carbs, bmr, tdee, goal) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, final_calories, protein, fat, carbs, int(bmr), int(tdee), goal))
    
    text = (
        f"✅ *Ваша норма рассчитана!*\n\n"
        f"🎯 *Дневная норма:* {final_calories} ккал\n\n"
        f"🍗 *Белки:* {protein} г ({protein*4} ккал)\n"
        f"🥑 *Жиры:* {fat} г ({fat*9} ккал)\n"
        f"🍚 *Углеводы:* {carbs} г ({carbs*4} ккал)\n\n"
        f"📊 *Детали:*\n"
        f"• BMR: {int(bmr)} ккал (базальный метаболизм)\n"
        f"• TDEE: {int(tdee)} ккал (с учетом активности)\n"
        f"• Цель: {GOALS[goal]['name']}\n\n"
        f"Теперь добавляйте еду в трекер!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ ДОБАВИТЬ ЕДУ", callback_data="add_food_menu"),
        InlineKeyboardButton(text="📊 К ТРЕКЕРУ", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.clear()
    await callback.answer()
    
# ================ ДОБАВЛЕНИЕ ЕДЫ ================

@router.callback_query(F.data == "add_food_menu")
async def add_food_menu(callback: CallbackQuery, state: FSMContext):
    """Меню добавления еды"""
    text = (
        "🍎 *Добавление еды*\n\n"
        "Выберите способ добавления:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📖 ИЗ БАЗЫ", callback_data="add_from_db"),
        InlineKeyboardButton(text="✏️ ВРУЧНУЮ", callback_data="add_manual")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "add_from_db")
async def add_from_db(callback: CallbackQuery):
    """Добавление из базы продуктов"""
    text = "📖 *База продуктов*\n\nВыберите категорию:"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🥣 ЗАВТРАК", callback_data="food_cat:breakfast"),
        InlineKeyboardButton(text="🥩 МЯСО", callback_data="food_cat:meat")
    )
    builder.row(
        InlineKeyboardButton(text="🥬 ОВОЩИ", callback_data="food_cat:veg"),
        InlineKeyboardButton(text="🍎 ФРУКТЫ", callback_data="food_cat:fruit")
    )
    builder.row(
        InlineKeyboardButton(text="☕ НАПИТКИ", callback_data="food_cat:drinks"),
        InlineKeyboardButton(text="🍚 КРУПЫ", callback_data="food_cat:grains")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="add_food_menu")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("food_cat:"))
async def show_category(callback: CallbackQuery):
    """Показать продукты в категории"""
    category = callback.data.split(":")[1]
    
    # Категории продуктов
    categories = {
        "breakfast": ["овсянка", "гречка", "яйца", "творог"],
        "meat": ["курица", "говядина", "индейка", "рыба"],
        "veg": ["картофель", "брокколи", "помидоры", "огурцы"],
        "fruit": ["банан", "яблоко", "апельсин"],
        "drinks": ["кофе", "чай", "сок"],
        "grains": ["рис", "гречка", "овсянка"]
    }
    
    category_names = {
        "breakfast": "🥣 Завтрак",
        "meat": "🥩 Мясо",
        "veg": "🥬 Овощи",
        "fruit": "🍎 Фрукты",
        "drinks": "☕ Напитки",
        "grains": "🍚 Крупы"
    }
    
    text = f"📖 *{category_names[category]}*\n\nВыберите продукт:"
    
    builder = InlineKeyboardBuilder()
    for food in categories[category]:
        if food in FOOD_DATABASE:
            data = FOOD_DATABASE[food]
            builder.row(
                InlineKeyboardButton(
                    text=f"{food.title()} ({data['calories']} ккал/100{data['unit']})",
                    callback_data=f"select_food:{food}"
                )
            )
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="add_from_db")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("select_food:"))
async def select_food(callback: CallbackQuery, state: FSMContext):
    """Выбор продукта из базы"""
    food = callback.data.split(":")[1]
    
    await state.update_data(selected_food=food)
    
    data = FOOD_DATABASE[food]
    
    text = (
        f"✅ Выбран: *{food.title()}*\n\n"
        f"📊 *На 100{data['unit']}:*\n"
        f"• Калории: {data['calories']} ккал\n"
        f"• Белки: {data['protein']} г\n"
        f"• Жиры: {data['fat']} г\n"
        f"• Углеводы: {data['carbs']} г\n\n"
        f"Введите количество (в {data['unit']}):"
    )
    
    await callback.message.edit_text(text)
    await state.set_state(CalorieStates.waiting_food_amount)
    await callback.answer()

@router.callback_query(F.data == "add_manual")
async def add_manual(callback: CallbackQuery, state: FSMContext):
    """Ручное добавление еды"""
    await callback.message.edit_text(
        "✏️ *Ручное добавление*\n\n"
        "Введите название продукта:"
    )
    await state.set_state(CalorieStates.waiting_food_name)
    await callback.answer()

@router.message(CalorieStates.waiting_food_name)
async def process_food_name(message: Message, state: FSMContext):
    """Обработка названия продукта"""
    food_name = message.text.strip()
    await state.update_data(food_name=food_name)
    
    await message.answer(
        "⚖️ Введите калорийность на 100г (ккал):"
    )
    await state.set_state(CalorieStates.waiting_food_calories)

@router.message(CalorieStates.waiting_food_calories)
async def process_food_calories(message: Message, state: FSMContext):
    """Обработка калорийности"""
    try:
        calories = int(message.text)
        if calories <= 0:
            raise ValueError
        await state.update_data(calories=calories)
        
        await message.answer(
            "🥩 Введите количество белков на 100г (г):"
        )
        await state.set_state(CalorieStates.waiting_food_protein)
    except ValueError:
        await message.answer("❌ Введите положительное число")

@router.message(CalorieStates.waiting_food_protein)
async def process_food_protein(message: Message, state: FSMContext):
    """Обработка белков"""
    try:
        protein = float(message.text.replace(',', '.'))
        if protein < 0:
            raise ValueError
        await state.update_data(protein=protein)
        
        await message.answer(
            "🥑 Введите количество жиров на 100г (г):"
        )
        await state.set_state(CalorieStates.waiting_food_fat)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(CalorieStates.waiting_food_fat)
async def process_food_fat(message: Message, state: FSMContext):
    """Обработка жиров"""
    try:
        fat = float(message.text.replace(',', '.'))
        if fat < 0:
            raise ValueError
        await state.update_data(fat=fat)
        
        await message.answer(
            "🍚 Введите количество углеводов на 100г (г):"
        )
        await state.set_state(CalorieStates.waiting_food_carbs)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(CalorieStates.waiting_food_carbs)
async def process_food_carbs(message: Message, state: FSMContext):
    """Обработка углеводов"""
    try:
        carbs = float(message.text.replace(',', '.'))
        if carbs < 0:
            raise ValueError
        await state.update_data(carbs=carbs)
        
        await message.answer(
            "⚖️ Введите количество съеденного (в граммах):"
        )
        await state.update_data(unit="г")
        await state.set_state(CalorieStates.waiting_food_amount)
    except ValueError:
        await message.answer("❌ Введите число")

@router.message(CalorieStates.waiting_food_amount)
async def process_food_amount(message: Message, state: FSMContext):
    """Обработка количества"""
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0:
            raise ValueError
        
        data = await state.get_data()
        user_id = message.from_user.id
        today = date.today().isoformat()
        
        if 'selected_food' in data:
            # Из базы
            food = data['selected_food']
            food_data = FOOD_DATABASE[food]
            multiplier = amount / 100
            
            calories = int(food_data['calories'] * multiplier)
            protein = round(food_data['protein'] * multiplier, 1)
            fat = round(food_data['fat'] * multiplier, 1)
            carbs = round(food_data['carbs'] * multiplier, 1)
            unit = food_data['unit']
            food_name = food
            
        else:
            # Ручной ввод
            multiplier = amount / 100
            calories = int(data['calories'] * multiplier)
            protein = round(data['protein'] * multiplier, 1)
            fat = round(data['fat'] * multiplier, 1)
            carbs = round(data['carbs'] * multiplier, 1)
            unit = data['unit']
            food_name = data['food_name']
        
        # Сохраняем запись
        await db.execute("""
            INSERT INTO food_entries 
            (user_id, date, food_name, amount, unit, calories, protein, fat, carbs) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, today, food_name, amount, unit, calories, protein, fat, carbs))
        
        text = (
            f"✅ *Еда добавлена!*\n\n"
            f"🍽️ *{food_name}*\n"
            f"⚡ Калории: {calories} ккал\n"
            f"🍗 Белки: {protein} г\n"
            f"🥑 Жиры: {fat} г\n"
            f"🍚 Углеводы: {carbs} г\n"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➕ ЕЩЁ", callback_data="add_food_menu"),
            InlineKeyboardButton(text="📊 К ТРЕКЕРУ", callback_data="calorie_tracker")
        )
        
        await message.answer(text, reply_markup=builder.as_markup())
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Введите корректное количество")

# ================ ИСТОРИЯ ================

@router.callback_query(F.data == "calorie_history")
async def calorie_history(callback: CallbackQuery):
    """История питания"""
    user_id = callback.from_user.id
    
    # Получаем последние 7 дней
    end_date = date.today()
    start_date = end_date - timedelta(days=7)
    
    history = await db.fetch_all("""
        SELECT date, SUM(calories) as total_calories, COUNT(*) as items
        FROM food_entries
        WHERE user_id = ? AND date BETWEEN ? AND ?
        GROUP BY date
        ORDER BY date DESC
    """, (user_id, start_date.isoformat(), end_date.isoformat()))
    
    if not history:
        text = "📊 *История питания*\n\nПока нет записей о еде."
    else:
        text = "📊 *История питания (7 дней)*\n\n"
        for day in history:
            text += f"📅 {day['date']}: {day['total_calories']} ккал ({day['items']} продуктов)\n"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()    

if USE_FATSECRET:
    from services.fatsecret_service import FatSecretService
    fatsecret = FatSecretService(
        client_id=FATSECRET_CLIENT_ID,
        client_secret=FATSECRET_CLIENT_SECRET
    )
else:
    # Заглушка
    fatsecret = None

# Временно отключаем FatSecret
USE_FATSECRET = False


@router.callback_query(F.data == "search_food")
async def search_food(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(
        "🔍 *Поиск продукта*\n\n"
        "Введите название продукта (например: 'банан', 'куриная грудка'):"
    )
    await state.set_state(CalorieStates.waiting_search_query)
    await callback.answer()

@router.message(CalorieStates.waiting_search_query)
async def process_food_search(message: Message, state: FSMContext):
    query = message.text.strip()
    
    if len(query) < 2:
        await message.answer("❌ Слишком короткий запрос. Введите минимум 2 символа.")
        return
    
    await message.answer("🔍 Ищу продукты...")
    
    # Поиск через FatSecret API
    foods = fatsecret.search_foods(query)
    
    if not foods:
        await message.answer(
            "❌ Продукты не найдены.\n\n"
            "Попробуйте другое название или добавьте продукт вручную.",
            reply_markup=InlineKeyboardBuilder().row(
                InlineKeyboardButton(text="✏️ ВРУЧНУЮ", callback_data="add_manual"),
                InlineKeyboardButton(text="↩️ НАЗАД", callback_data="calorie_tracker")
            ).as_markup()
        )
        return
    
    # Показываем результаты поиска
    text = f"🔍 *Результаты поиска:*\n\n"
    builder = InlineKeyboardBuilder()
    
    for i, food in enumerate(foods[:10], 1):
        name = food.get('food_name', 'Без названия')
        brand = food.get('brand_name', '')
        description = f"{brand} - {name}" if brand else name
        text += f"{i}. {description}\n"
        
        builder.row(
            InlineKeyboardButton(
                text=f"{i}. {name[:20]}",
                callback_data=f"select_food:{food.get('food_id')}"
            )
        )
    
    text += f"\nВыберите продукт из списка или введите запрос заново:"
    
    builder.row(
        InlineKeyboardButton(text="🔄 НОВЫЙ ПОИСК", callback_data="search_food"),
        InlineKeyboardButton(text="↩️ НАЗАД", callback_data="calorie_tracker")
    )
    
    await message.answer(text, reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("select_food:"))
async def select_food(callback: CallbackQuery, state: FSMContext):
    food_id = callback.data.split(":")[1]
    
    # Получаем детали продукта
    food_data = fatsecret.get_food_details(food_id)
    
    if not food_data:
        await callback.answer("❌ Ошибка загрузки продукта", show_alert=True)
        return
    
    nutrition = fatsecret.get_nutrition_data(food_data)
    
    await state.update_data(
        selected_food=food_data.get('food_name'),
        calories_per_100=nutrition['calories'],
        protein_per_100=nutrition['protein'],
        fat_per_100=nutrition['fat'],
        carbs_per_100=nutrition['carbs']
    )
    
    text = (
        f"✅ *{food_data.get('food_name')}*\n\n"
        f"📊 *Пищевая ценность на 100г:*\n"
        f"⚡ Калории: {nutrition['calories']} ккал\n"
        f"🍗 Белки: {nutrition['protein']} г\n"
        f"🥑 Жиры: {nutrition['fat']} г\n"
        f"🍚 Углеводы: {nutrition['carbs']} г\n"
        f"🥬 Клетчатка: {nutrition['fiber']} г\n"
        f"🍬 Сахар: {nutrition['sugar']} г\n\n"
        f"Введите количество граммов:"
    )
    
    await callback.message.edit_text(text)
    await state.set_state(CalorieStates.waiting_food_amount)
    await callback.answer()