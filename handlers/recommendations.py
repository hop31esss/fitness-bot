# handlers/recommendations.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.callback_query(F.data == "recommendations")
async def show_recommendations(callback: CallbackQuery):
    """Рекомендации по тренировкам"""
    text = (
        "💡 *Рекомендации по тренировкам:*\n\n"
        
        "1. **Разминка 5-10 минут** перед каждой тренировкой\n"
        "2. **Техника важнее веса** - не гонитесь за рекордами\n"
        "3. **Восстановление** - спите 7-9 часов\n"
        "4. **Питание** - белок после тренировки\n"
        "5. **Вода** - 2-3 литра в день\n"
        "6. **Регулярность** - 3-4 тренировки в неделю\n"
        "7. **Прогрессия** - увеличивайте вес постепенно\n\n"
        
        "💪 *Совет от бота:*\n"
        "Записывайте каждую тренировку в журнал для отслеживания прогресса!\n\n"
        
        "*Разработано с ❤️ @hop31esss*"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить тренировку", callback_data="add_workout"),
        InlineKeyboardButton(text="📋 Мои упражнения", callback_data="my_exercises")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()