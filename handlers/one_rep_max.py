from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from datetime import datetime

from database.base import db
from config import ADMIN_ID

router = Router()

class OneRepMaxStates(StatesGroup):
    waiting_weight = State()
    waiting_reps = State()

# Функция для создания клавиатуры с кнопками навигации
def get_navigation_keyboard():
    """Клавиатура с кнопками навигации"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Новый расчет", callback_data="one_rep_max"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_cancel_keyboard():
    """Клавиатура с кнопкой отмены"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="one_rep_max_cancel")
    )
    return builder.as_markup()

@router.callback_query(F.data == "one_rep_max")
async def one_rep_max_menu(callback: CallbackQuery, state: FSMContext):
    """Меню калькулятора 1ПМ"""
    user_id = callback.from_user.id
    
    # Проверка доступа
    if user_id == ADMIN_ID:
        await callback.message.edit_text(
            "🏋️ *Калькулятор 1ПМ*\n\n"
            "Введите вес (кг):\n\n"
            "для отмены нажмите кнопку ниже",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(OneRepMaxStates.waiting_weight)
        await callback.answer()
        return
    
    # Проверка премиум-доступа
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
        await callback.message.edit_text(
            "🏋️ *Калькулятор 1ПМ*\n\n"
            "Введите вес (кг):\n\n"
            "_(для отмены нажмите кнопку ниже)_",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(OneRepMaxStates.waiting_weight)
        await callback.answer()
    else:
        await callback.answer("❌ Премиум-функция!", show_alert=True)
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="👑 Премиум", callback_data="show_premium_info")
        )
        
        await callback.message.answer(
            "👑 *Премиум-доступ*\n\n"
            "Калькулятор 1ПМ доступен только с премиум-подпиской!\n\n"
            "💰 150₽/месяц\n\n"
            "Приобрести можно у администратора: @hop31esss",
            reply_markup=builder.as_markup()
        )

@router.callback_query(F.data == "one_rep_max_cancel")
async def one_rep_max_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена расчета"""
    await state.clear()
    await callback.message.edit_text(
        "❌ *Расчет отменен*\n\n"
        "Возвращайтесь, когда захотите рассчитать 1ПовторныйМаксимум! 💪",
        reply_markup=InlineKeyboardBuilder().row(
            InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
        ).as_markup()
    )
    await callback.answer()

@router.message(OneRepMaxStates.waiting_weight)
async def process_weight(message: Message, state: FSMContext):
    """Обработка веса"""
    try:
        weight = float(message.text.strip().replace(',', '.'))
        if weight <= 0 or weight > 500:
            raise ValueError
        
        await state.update_data(weight=weight)
        await message.answer(
            "Введите количество повторений (от 1 до 100):\n\n"
            "_(для отмены нажмите кнопку ниже)_",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(OneRepMaxStates.waiting_reps)
    except ValueError:
        await message.answer(
            "❌ Введите корректное число (например: 80 или 80.5):\n\n"
            "(Для отмены нажмите кнопку ниже)",
            reply_markup=get_cancel_keyboard()
        )

@router.message(OneRepMaxStates.waiting_reps)
async def process_reps(message: Message, state: FSMContext):
    """Обработка повторений и расчет"""
    try:
        reps = int(message.text.strip())
        if reps < 1 or reps > 100:
            raise ValueError
        
        data = await state.get_data()
        weight = data['weight']
        
        # Расчет по формуле Эпли
        one_rep_max = weight * (1 + reps / 30)
        
        # Расчет процентов
        percentages = {
            "100%": one_rep_max,
            "95%": one_rep_max * 0.95,
            "90%": one_rep_max * 0.90,
            "85%": one_rep_max * 0.85,
            "80%": one_rep_max * 0.80,
            "75%": one_rep_max * 0.75,
            "70%": one_rep_max * 0.70,
            "65%": one_rep_max * 0.65,
            "60%": one_rep_max * 0.60,
        }
        
        # Создаем таблицу процентов
        percent_table = ""
        for percent, value in percentages.items():
            percent_table += f"• {percent}: {value:.1f} кг\n"
        
        await message.answer(
            f"✅ *Результат расчета 1ПМ*\n\n"
            f"🏋️ *Ваш 1ПМ:* **{one_rep_max:.1f} кг**\n\n"
            f"📊 *Исходные данные:*\n"
            f"• Вес: {weight} кг\n"
            f"• Повторения: {reps}\n\n"
            f"📈 *Проценты от максимума:*\n"
            f"{percent_table}\n"
            f"💡 *Совет:* Для роста силы работайте в диапазоне 80-90% от 1ПМ",
            reply_markup=get_navigation_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Введите корректное число повторений (от 1 до 100):\n\n"
            "(Для отмены нажмите кнопку ниже)",
            reply_markup=get_cancel_keyboard()
        )