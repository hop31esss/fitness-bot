# handlers/challenges.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.callback_query(F.data == "challenges")
async def show_challenges(callback: CallbackQuery):
    """Челленджи"""
    text = (
        "🎯 *Текущие челленджи:*\n\n"
        
        "🏆 **30 дней подряд**\n"
        "Тренируйтесь каждый день 30 дней\n"
        "Награда: Ачивка 'Железная воля'\n"
        "Участников: 127\n\n"
        
        "💪 **+10% к весу**\n"
        "Увеличьте рабочий вес в любом упражнении на 10%\n"
        "Награда: Значок 'Прогресс'\n"
        "Участников: 89\n\n"
        
        "🔥 **5 тренировок в неделю**\n"
        "Завершите 5 тренировок за неделю\n"
        "Награда: Медаль 'Трудяга'\n"
        "Участников: 56\n\n"
        
        "🏃 **100 км кардио**\n"
        "Пробегите/пройдите 100 км за месяц\n"
        "Награда: Значок 'Марафонец'\n"
        "Участников: 42\n"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Принять челлендж", callback_data="join_challenge"),
        InlineKeyboardButton(text="📊 Мои челленджи", callback_data="my_challenges")
    )
    builder.row(
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()