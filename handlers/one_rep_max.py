from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.premium_access import has_premium_access
from services.progress_analytics import estimated_1rm, format_kg

router = Router()

class OneRepMaxStates(StatesGroup):
    waiting_weight = State()
    waiting_reps = State()

def get_navigation_keyboard(premium: bool = True):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Новый расчет", callback_data="one_rep_max"),
        InlineKeyboardButton(text="👋 В меню", callback_data="menu_profile"),
    )
    if not premium:
        builder.row(InlineKeyboardButton(text="👑 Получить Premium", callback_data="payment"))
    return builder.as_markup()

def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="one_rep_max_cancel")
    )
    return builder.as_markup()

@router.callback_query(F.data == "one_rep_max")
async def one_rep_max_menu(callback: CallbackQuery, state: FSMContext):
    """Калькулятор доступен всем; история и сравнение — в Premium."""
    await callback.message.edit_text(
        "🏋️ *Калькулятор 1ПМ*\n\n"
        "Введите вес (кг):\n\n"
        "для отмены нажмите кнопку ниже",
        reply_markup=get_cancel_keyboard(),
    )
    await state.set_state(OneRepMaxStates.waiting_weight)
    await callback.answer()

@router.callback_query(F.data == "one_rep_max_cancel")
async def one_rep_max_cancel(callback: CallbackQuery, state: FSMContext):
    """Отмена расчета"""
    await state.clear()
    await callback.message.edit_text(
        "❌ *Расчет отменен*\n\n"
        "Возвращайтесь, когда захотите рассчитать 1ПовторныйМаксимум! 💪",
        reply_markup=InlineKeyboardBuilder().row(
        InlineKeyboardButton(text="👋 В меню", callback_data="menu_profile")
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
        
        one_rep_max = estimated_1rm(weight, reps)
        
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
        
        percent_table = ""
        for percent, value in percentages.items():
            percent_table += f"• {percent}: {format_kg(value, 1)} кг\n"
        
        premium = await has_premium_access(message.from_user.id)
        text = (
            f"✅ *Результат расчета 1ПМ*\n\n"
            f"💪 Расчётный 1ПМ ≈ *{format_kg(one_rep_max, 1)} кг*\n\n"
            f"📊 *Исходные данные:*\n"
            f"• Вес: {format_kg(weight, 1)} кг\n"
            f"• Повторения: {reps}\n\n"
            f"📈 *Проценты от максимума:*\n"
            f"{percent_table}"
        )
        if not premium:
            text += (
                "\n────────────────\n\n"
                "💎 *В Premium ты также сможешь:*\n"
                "• хранить историю 1ПМ\n"
                "• отслеживать изменение силы\n"
                "• видеть личные рекорды\n"
                "• сравнивать результаты по периодам\n"
            )
        await message.answer(text, reply_markup=get_navigation_keyboard(premium))
        await state.clear()
        
    except ValueError:
        await message.answer(
            "❌ Введите корректное число повторений (от 1 до 100):\n\n"
            "(Для отмены нажмите кнопку ниже)",
            reply_markup=get_cancel_keyboard()
        )