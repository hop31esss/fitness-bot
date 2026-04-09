from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

# ID администратора - ОН ИМЕЕТ ДОСТУП КО ВСЕМУ
ADMIN_ID = 385450652  # ВАШ ID

# Список ID, у которых есть премиум-доступ (друзья)
PREMIUM_USERS = [
    # Добавляйте сюда ID друзей
    # 123456789,  # Пример
]

# ================ ПРОВЕРКА ДОСТУПА ================

def has_premium_access(user_id: int) -> bool:
    """Проверка доступа к премиум-функциям"""
    # Админ имеет доступ всегда
    if user_id == ADMIN_ID:
        return True
    
    # Друзья из списка имеют доступ
    if user_id in PREMIUM_USERS:
        return True
    
    # Остальные не имеют доступа
    return False

# ================ МЕНЮ ПРЕМИУМ ================

@router.callback_query(F.data == "show_premium_info")
async def show_premium_info(callback: CallbackQuery):
    """Показать информацию о премиум-подписке"""
    user_id = callback.from_user.id
    
    if has_premium_access(user_id):
        # Для админа и друзей
        text = (
            "👑 *Премиум доступ*\n\n"
            "✅ У вас есть доступ ко всем премиум-функциям!\n\n"
            "*Доступные функции:*\n"
            "• 🏋️ Калькулятор 1ПМ\n"
            "• 🔥 Трекер калорий\n"
            "• 👥 Друзья и челленджи\n"
            "• 📊 Расширенная статистика\n"
            "• 📤 Экспорт данных\n\n"
            "Наслаждайтесь! 💪"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🏋️ 1ПМ", callback_data="one_rep_max"),
            InlineKeyboardButton(text="🔥 Калории", callback_data="calorie_tracker")
        )
        builder.row(
            InlineKeyboardButton(text="👥 Друзья", callback_data="friends_menu"),
            InlineKeyboardButton(text="↩️ В меню", callback_data="back_to_main")
        )
        
    else:
        # Для обычных пользователей
        text = (
            "👑 *Премиум подписка*\n\n"
            "Получите доступ к расширенным функциям:\n\n"
            "✨ *Премиум-функции:*\n"
            "• 🏋️ **Калькулятор 1ПМ**\n"
            "• 🔥 **Трекер калорий**\n"
            "• 👥 **Друзья и челленджи**\n"
            "• 📊 **Расширенная статистика**\n"
            "• 📤 **Экспорт данных**\n\n"
            "💰 *Стоимость:* 150₽/месяц или 120 ⭐\n\n"
            "Для покупки напишите администратору: @hop31esss"
        )
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="✉️ Написать админу", url="https://t.me/hop31esss"),
            InlineKeyboardButton(text="↩️ В меню", callback_data="back_to_main")
        )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()

@router.callback_query(F.data == "premium_features")
async def premium_features_menu(callback: CallbackQuery):
    """Меню премиум-функций"""
    text = (
        "⭐ *ПРЕМИУМ ФУНКЦИИ*\n\n"
        "✨ *Что доступно:*\n\n"
        "▫️ 🏋️ *1ПМ Калькулятор* - максимумы с историей\n"
        "▫️ 🔥 *Трекер калорий* - база продуктов\n"
        "▫️ 👥 *Друзья* - соревнуйтесь и мотивируйте\n"
        "▫️ 🤖 *AI-советы* - персональные рекомендации\n"
        "▫️ 📊 *Расширенная статистика* - графики\n"
        "▫️ 📤 *Экспорт данных* - в Excel/CSV\n\n"
        "👇 *Выберите функцию:*"
    )
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🏋️ 1ПМ", callback_data="one_rep_max"),
        InlineKeyboardButton(text="🔥 КАЛОРИИ", callback_data="calorie_tracker")
    )
    
    builder.row(
        InlineKeyboardButton(text="👥 ДРУЗЬЯ", callback_data="friends_menu"),
        InlineKeyboardButton(text="🤖 AI-СОВЕТЫ", callback_data="ai_advice")
    )
    
    builder.row(
        InlineKeyboardButton(text="📊 РАСШ. СТАТИСТИКА", callback_data="advanced_stats"),
        InlineKeyboardButton(text="📤 ЭКСПОРТ", callback_data="export_data")
    )
    
    builder.row(
        InlineKeyboardButton(text="◀️ НАЗАД", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(
        caption=text,
        reply_markup=builder.as_markup()
    )
    await callback.answer()    

@router.message(Command("premium"))
async def cmd_premium(message: Message):
    """Команда для вызова премиум-меню"""
    # Создаем фиктивный callback
    class FakeCallback:
        def __init__(self, message):
            self.message = message
            self.from_user = message.from_user
            self.answer = lambda x: None
    
    fake_callback = FakeCallback(message)
    await show_premium_info(fake_callback)