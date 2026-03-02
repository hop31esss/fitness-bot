from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime, date, timedelta

from database.base import db
from config import ADMIN_ID

router = Router()

@router.callback_query(F.data == "calorie_tracker")
async def calorie_tracker_menu(callback: CallbackQuery):
    """Главное меню трекера калорий"""
    user_id = callback.from_user.id
    
    print(f"DEBUG: calorie_tracker_menu called by user {user_id}")  # Отладка
    
    # ПРОВЕРКА: если это админ - даем доступ
    if user_id == ADMIN_ID:
        print(f"DEBUG: Admin access granted")  # Отладка
        await show_calorie_menu(callback)
        return
    
    # Для всех остальных - проверяем премиум
    user = await db.fetch_one(
        "SELECT is_subscribed, subscription_until FROM users WHERE user_id = ?",
        (user_id,)
    )
    
    is_premium = False
    if user and user['is_subscribed'] and user['subscription_until']:
        until = datetime.fromisoformat(user['subscription_until'].replace('Z', '+00:00'))
        if datetime.now() <= until:
            is_premium = True
    
    if is_premium:
        print(f"DEBUG: Premium access granted")  # Отладка
        await show_calorie_menu(callback)
    else:
        print(f"DEBUG: No access for user {user_id}")  # Отладка
        await callback.answer("❌ Премиум-функция!", show_alert=True)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="👑 Премиум", callback_data="show_premium_info")
        )
        
        await callback.message.answer(
            "👑 *Премиум-доступ*\n\n"
            "Трекер калорий доступен только с премиум-подпиской!\n\n"
            "💰 299₽/месяц\n\n"
            "Приобрести можно у администратора: @hop31esss",
            reply_markup=builder.as_markup()
        )

async def show_calorie_menu(callback: CallbackQuery):
    """Показать меню трекера"""
    text = "🔥 *Трекер калорий*\n\nВыберите действие:"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить еду", callback_data="add_food"),
        InlineKeyboardButton(text="📊 Моя норма", callback_data="calculate_norm")
    )
    builder.row(
        InlineKeyboardButton(text="📖 База продуктов", callback_data="food_database"),
        InlineKeyboardButton(text="↩️ В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# Состояния для FSM
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

# База данных продуктов (упрощенная)
FOOD_DATABASE = {
    # Завтрак
    "овсянка": {"calories": 350, "unit": "г", "protein": 12, "fat": 6, "carbs": 60},
    "гречка": {"calories": 330, "unit": "г", "protein": 13, "fat": 3, "carbs": 68},
    "рис": {"calories": 360, "unit": "г", "protein": 7, "fat": 1, "carbs": 79},
    "яйца": {"calories": 155, "unit": "шт", "protein": 13, "fat": 11, "carbs": 1},
    "омлет": {"calories": 180, "unit": "порция", "protein": 12, "fat": 13, "carbs": 3},
    "творог": {"calories": 120, "unit": "г", "protein": 18, "fat": 5, "carbs": 3},
    "йогурт": {"calories": 80, "unit": "г", "protein": 5, "fat": 2, "carbs": 12},
    
    # Обед
    "курица": {"calories": 165, "unit": "г", "protein": 31, "fat": 3.6, "carbs": 0},
    "говядина": {"calories": 250, "unit": "г", "protein": 26, "fat": 17, "carbs": 0},
    "рыба": {"calories": 150, "unit": "г", "protein": 22, "fat": 6, "carbs": 0},
    "картошка": {"calories": 77, "unit": "г", "protein": 2, "fat": 0.1, "carbs": 17},
    "макароны": {"calories": 350, "unit": "г", "protein": 13, "fat": 1.5, "carbs": 75},
    "суп": {"calories": 60, "unit": "мл", "protein": 3, "fat": 2, "carbs": 8},
    
    # Ужин
    "индейка": {"calories": 135, "unit": "г", "protein": 29, "fat": 1, "carbs": 0},
    "креветки": {"calories": 85, "unit": "г", "protein": 18, "fat": 0.8, "carbs": 0},
    "салат": {"calories": 30, "unit": "г", "protein": 2, "fat": 0.2, "carbs": 5},
    "овощи": {"calories": 40, "unit": "г", "protein": 2, "fat": 0.2, "carbs": 8},
    
    # Перекусы
    "банан": {"calories": 95, "unit": "шт", "protein": 1.3, "fat": 0.3, "carbs": 24},
    "яблоко": {"calories": 52, "unit": "шт", "protein": 0.3, "fat": 0.2, "carbs": 14},
    "апельсин": {"calories": 47, "unit": "шт", "protein": 0.9, "fat": 0.1, "carbs": 12},
    "орехи": {"calories": 600, "unit": "г", "protein": 20, "fat": 50, "carbs": 15},
    "протеин": {"calories": 120, "unit": "порция", "protein": 25, "fat": 2, "carbs": 3},
    "батончик": {"calories": 200, "unit": "шт", "protein": 10, "fat": 8, "carbs": 25},
    
    # Напитки
    "кофе": {"calories": 2, "unit": "чашка", "protein": 0.1, "fat": 0, "carbs": 0},
    "чай": {"calories": 1, "unit": "чашка", "protein": 0, "fat": 0, "carbs": 0},
    "сок": {"calories": 45, "unit": "мл", "protein": 0.5, "fat": 0, "carbs": 11},
    "вода": {"calories": 0, "unit": "мл", "protein": 0, "fat": 0, "carbs": 0},
}

# Коэффициенты активности
ACTIVITY_LEVELS = {
    "1.2": {"name": "Минимальная", "desc": "Сидячая работа, нет тренировок"},
    "1.375": {"name": "Низкая", "desc": "Тренировки 1-3 раза в неделю"},
    "1.55": {"name": "Средняя", "desc": "Тренировки 3-5 раз в неделю"},
    "1.725": {"name": "Высокая", "desc": "Тренировки 6-7 раз в неделю"},
    "1.9": {"name": "Очень высокая", "desc": "Спортсмены, физический труд"}
}

# Цели
GOALS = {
    "lose": {"name": "Похудение", "adjustment": -0.15},
    "maintain": {"name": "Поддержание", "adjustment": 0},
    "gain": {"name": "Набор массы", "adjustment": 0.15}
}

# ================ ГЛАВНОЕ МЕНЮ ТРЕКЕРА ================

@router.callback_query(F.data == "calorie_tracker")
async def calorie_tracker_menu(callback: CallbackQuery):
    """Главное меню трекера калорий"""
    user_id = callback.from_user.id
    today = date.today().isoformat()
    
    # Получаем сегодняшние данные
    today_data = await get_today_calories(user_id, today)
    
    if today_data:
        text = (
            "🔥 *Трекер калорий*\n\n"
            f"📅 Сегодня: {today_data['date']}\n"
            f"⚡ Потреблено: {today_data['total']} ккал\n"
            f"🎯 Норма: {today_data['goal']} ккал\n"
            f"📊 Осталось: {today_data['remaining']} ккал\n\n"
            
            f"🍗 Белки: {today_data['protein']}г\n"
            f"🥑 Жиры: {today_data['fat']}г\n"
            f"🍚 Углеводы: {today_data['carbs']}г\n"
        )
    else:
        # Нет данных за сегодня
        text = (
            "🔥 *Трекер калорий*\n\n"
            "У вас пока нет записей за сегодня.\n\n"
            "Начните с расчета вашей нормы калорий!"
        )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить еду", callback_data="add_food"),
        InlineKeyboardButton(text="📊 Моя норма", callback_data="calculate_norm")
    )
    builder.row(
        InlineKeyboardButton(text="📋 История", callback_data="calorie_history"),
        InlineKeyboardButton(text="📖 База продуктов", callback_data="food_database")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 Сбросить день", callback_data="reset_day"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

# ================ РАСЧЕТ НОРМЫ КАЛОРИЙ ================

@router.callback_query(F.data == "calculate_norm")
async def calculate_norm_start(callback: CallbackQuery, state: FSMContext):
    """Начало расчета нормы калорий"""
    text = (
        "📊 *Расчет нормы калорий*\n\n"
        "Для расчета вашей суточной нормы калорий ответьте на несколько вопросов.\n\n"
        "Шаг 1/5: Выберите ваш пол:"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="👨 Мужской", callback_data="gender:male"),
        InlineKeyboardButton(text="👩 Женский", callback_data="gender:female")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Отмена", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(CalorieStates.waiting_gender)

@router.callback_query(CalorieStates.waiting_gender, F.data.startswith("gender:"))
async def process_gender(callback: CallbackQuery, state: FSMContext):
    """Обработка пола"""
    gender = callback.data.split(":")[1]
    await state.update_data(gender=gender)
    
    await callback.message.edit_text(
        "📊 *Расчет нормы калорий*\n\n"
        "Шаг 2/5: Введите ваш возраст (лет):"
    )
    await state.set_state(CalorieStates.waiting_age)
    await callback.answer()

@router.message(CalorieStates.waiting_age)
async def process_age(message: Message, state: FSMContext):
    """Обработка возраста"""
    try:
        age = int(message.text.strip())
        if age < 10 or age > 120:
            raise ValueError
        
        await state.update_data(age=age)
        
        await message.answer(
            "📊 *Расчет нормы калорий*\n\n"
            "Шаг 3/5: Введите ваш вес (кг):"
        )
        await state.set_state(CalorieStates.waiting_weight)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный возраст (от 10 до 120 лет):"
        )

@router.message(CalorieStates.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса"""
    try:
        weight = float(message.text.strip().replace(',', '.'))
        if weight < 20 or weight > 300:
            raise ValueError
        
        await state.update_data(weight=weight)
        
        await message.answer(
            "📊 *Расчет нормы калорий*\n\n"
            "Шаг 4/5: Введите ваш рост (см):"
        )
        await state.set_state(CalorieStates.waiting_height)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный вес (от 20 до 300 кг):"
        )

@router.message(CalorieStates.waiting_height)
async def process_height(message: Message, state: FSMContext):
    """Обработка роста"""
    try:
        height = float(message.text.strip().replace(',', '.'))
        if height < 100 or height > 250:
            raise ValueError
        
        await state.update_data(height=height)
        
        text = "📊 *Расчет нормы калорий*\n\n"
        text += "Шаг 5/5: Выберите уровень физической активности:\n\n"
        
        builder = InlineKeyboardBuilder()
        for coef, data in ACTIVITY_LEVELS.items():
            builder.row(
                InlineKeyboardButton(
                    text=f"{data['name']} - {data['desc']}",
                    callback_data=f"activity:{coef}"
                )
            )
        builder.row(
            InlineKeyboardButton(text="↩️ Отмена", callback_data="calorie_tracker")
        )
        
        await message.answer(text, reply_markup=builder.as_markup())
        await state.set_state(CalorieStates.waiting_activity)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректный рост (от 100 до 250 см):"
        )

@router.callback_query(CalorieStates.waiting_activity, F.data.startswith("activity:"))
async def process_activity(callback: CallbackQuery, state: FSMContext):
    """Обработка уровня активности"""
    activity = float(callback.data.split(":")[1])
    await state.update_data(activity=activity)
    
    text = "📊 *Расчет нормы калорий*\n\n"
    text += "Выберите вашу цель:\n\n"
    
    builder = InlineKeyboardBuilder()
    for goal_id, goal_data in GOALS.items():
        builder.row(
            InlineKeyboardButton(
                text=f"{goal_data['name']}",
                callback_data=f"goal:{goal_id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="↩️ Отмена", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.set_state(CalorieStates.waiting_goal)
    await callback.answer()

@router.callback_query(CalorieStates.waiting_goal, F.data.startswith("goal:"))
async def process_goal(callback: CallbackQuery, state: FSMContext):
    """Обработка цели и расчет итоговой нормы"""
    goal = callback.data.split(":")[1]
    
    data = await state.get_data()
    
    # Расчет BMR (базальный метаболизм) по формуле Миффлина-Сан Жеора
    if data['gender'] == 'male':
        bmr = (10 * data['weight']) + (6.25 * data['height']) - (5 * data['age']) + 5
    else:
        bmr = (10 * data['weight']) + (6.25 * data['height']) - (5 * data['age']) - 161
    
    # Учет активности
    tdee = bmr * data['activity']
    
    # Учет цели
    goal_adjustment = GOALS[goal]['adjustment']
    final_calories = tdee * (1 + goal_adjustment)
    
    # Расчет БЖУ
    protein = data['weight'] * 2.0  # 2г на кг веса
    fat = data['weight'] * 1.0       # 1г на кг веса
    carbs = (final_calories - (protein * 4 + fat * 9)) / 4
    
    # Сохраняем в БД
    user_id = callback.from_user.id
    await save_user_norm(user_id, {
        'calories': round(final_calories),
        'protein': round(protein),
        'fat': round(fat),
        'carbs': round(carbs),
        'bmr': round(bmr),
        'tdee': round(tdee),
        'goal': goal
    })
    
    # Формируем результат
    text = (
        "✅ *Ваша норма калорий рассчитана!*\n\n"
        f"🎯 Суточная норма: {round(final_calories)} ккал\n\n"
        
        f"🍗 Белки: {round(protein)}г ({round(protein * 4)} ккал)\n"
        f"🥑 Жиры: {round(fat)}г ({round(fat * 9)} ккал)\n"
        f"🍚 Углеводы: {round(carbs)}г ({round(carbs * 4)} ккал)\n\n"
        
        f"📊 Детали расчета:\n"
        f"• BMR: {round(bmr)} ккал (базальный метаболизм)\n"
        f"• TDEE: {round(tdee)} ккал (с учетом активности)\n"
        f"• Цель: {GOALS[goal]['name']}\n\n"
        
        f"💡 *Совет:* Теперь добавляйте еду в трекер и следите за калориями!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить еду", callback_data="add_food"),
        InlineKeyboardButton(text="📊 К трекеру", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await state.clear()
    await callback.answer()

# ================ ДОБАВЛЕНИЕ ЕДЫ ================

@router.callback_query(F.data == "add_food")
async def add_food_menu(callback: CallbackQuery, state: FSMContext):
    """Меню добавления еды"""
    text = (
        "➕ *Добавление еды*\n\n"
        "Выберите способ добавления:\n\n"
        "1️⃣ Из базы продуктов\n"
        "2️⃣ Ввести вручную"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📖 Из базы", callback_data="add_from_database"),
        InlineKeyboardButton(text="✏️ Вручную", callback_data="add_manual")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "add_from_database")
async def add_from_database(callback: CallbackQuery):
    """Добавление из базы продуктов"""
    # Группируем продукты по категориям
    categories = {
        "Завтрак": ["овсянка", "гречка", "рис", "яйца", "омлет", "творог", "йогурт"],
        "Обед": ["курица", "говядина", "рыба", "картошка", "макароны", "суп"],
        "Ужин": ["индейка", "креветки", "салат", "овощи"],
        "Перекусы": ["банан", "яблоко", "апельсин", "орехи", "протеин", "батончик"],
        "Напитки": ["кофе", "чай", "сок", "вода"]
    }
    
    text = "📖 *База продуктов*\n\nВыберите категорию:"
    
    builder = InlineKeyboardBuilder()
    for category in categories.keys():
        builder.row(
            InlineKeyboardButton(
                text=f"🍽️ {category}",
                callback_data=f"food_category:{category}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="add_food")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data.startswith("food_category:"))
async def show_food_category(callback: CallbackQuery):
    """Показать продукты в категории"""
    category = callback.data.split(":")[1]
    
    categories = {
        "Завтрак": ["овсянка", "гречка", "рис", "яйца", "омлет", "творог", "йогурт"],
        "Обед": ["курица", "говядина", "рыба", "картошка", "макароны", "суп"],
        "Ужин": ["индейка", "креветки", "салат", "овощи"],
        "Перекусы": ["банан", "яблоко", "апельсин", "орехи", "протеин", "батончик"],
        "Напитки": ["кофе", "чай", "сок", "вода"]
    }
    
    text = f"🍽️ *{category}*\n\nВыберите продукт:"
    
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
        InlineKeyboardButton(text="↩️ Назад", callback_data="add_from_database")
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
        f"✅ Выбран продукт: *{food.title()}*\n\n"
        f"📊 На 100{data['unit']}:\n"
        f"• Калории: {data['calories']} ккал\n"
        f"• Белки: {data['protein']}г\n"
        f"• Жиры: {data['fat']}г\n"
        f"• Углеводы: {data['carbs']}г\n\n"
        f"Введите количество (в {data['unit']}):"
    )
    
    await callback.message.edit_text(text)
    await state.set_state(CalorieStates.waiting_food_amount)
    await callback.answer()

@router.message(CalorieStates.waiting_food_amount)
async def process_food_amount(message: Message, state: FSMContext):
    """Обработка количества продукта"""
    try:
        amount = float(message.text.strip().replace(',', '.'))
        if amount <= 0:
            raise ValueError
        
        data = await state.get_data()
        food = data['selected_food']
        food_data = FOOD_DATABASE[food]
        
        # Расчет калорий и БЖУ
        multiplier = amount / 100
        calories = round(food_data['calories'] * multiplier)
        protein = round(food_data['protein'] * multiplier, 1)
        fat = round(food_data['fat'] * multiplier, 1)
        carbs = round(food_data['carbs'] * multiplier, 1)
        
        # Сохраняем запись о еде
        user_id = message.from_user.id
        today = date.today().isoformat()
        
        await save_food_entry(user_id, today, {
            'food': food,
            'amount': amount,
            'unit': food_data['unit'],
            'calories': calories,
            'protein': protein,
            'fat': fat,
            'carbs': carbs
        })
        
        # Подтверждение
        text = (
            f"✅ *Еда добавлена!*\n\n"
            f"🍽️ {food.title()}: {amount}{food_data['unit']}\n"
            f"⚡ Калории: {calories} ккал\n"
            f"🍗 Белки: {protein}г\n"
            f"🥑 Жиры: {fat}г\n"
            f"🍚 Углеводы: {carbs}г\n\n"
            f"Хотите добавить еще?"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="➕ Еще", callback_data="add_food"),
            InlineKeyboardButton(text="📊 К трекеру", callback_data="calorie_tracker")
        )
        
        await message.answer(text, reply_markup=builder.as_markup())
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректное количество:"
        )

# ================ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ================

async def get_today_calories(user_id: int, date_str: str):
    """Получить данные о калориях за сегодня"""
    # В реальном проекте здесь должен быть запрос к БД
    # Пока возвращаем заглушку
    return None

async def save_user_norm(user_id: int, norm_data: dict):
    """Сохранить норму калорий пользователя"""
    # Здесь будет сохранение в БД
    pass

async def save_food_entry(user_id: int, date_str: str, food_data: dict):
    """Сохранить запись о еде"""
    # Здесь будет сохранение в БД
    pass

# Заглушки для остальных функций
@router.callback_query(F.data == "calorie_history")
async def calorie_history(callback: CallbackQuery):
    """История калорий"""
    text = (
        "📋 *История калорий*\n\n"
        "Функция будет доступна в следующем обновлении!"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "food_database")
async def food_database(callback: CallbackQuery):
    """База продуктов"""
    text = (
        "📖 *База продуктов*\n\n"
        "В базе {len(FOOD_DATABASE)} продуктов.\n\n"
        "Используйте 'Добавить еду' → 'Из базы' для выбора."
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить еду", callback_data="add_food"),
        InlineKeyboardButton(text="↩️ Назад", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "reset_day")
async def reset_day(callback: CallbackQuery):
    """Сбросить данные за день"""
    text = (
        "🔄 *Сброс дня*\n\n"
        "Вы уверены? Все данные за сегодня будут удалены."
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Да, сбросить", callback_data="confirm_reset_day"),
        InlineKeyboardButton(text="❌ Нет", callback_data="calorie_tracker")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "confirm_reset_day")
async def confirm_reset_day(callback: CallbackQuery):
    """Подтверждение сброса дня"""
    await callback.message.edit_text(
        "✅ Данные за сегодня сброшены!",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="📊 К трекеру", callback_data="calorie_tracker")
        ).as_markup()
    )
    await callback.answer()