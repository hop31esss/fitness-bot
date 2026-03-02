# handlers/features.py
from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

router = Router()

@router.callback_query(F.data == "bot_features")
async def show_features(callback: CallbackQuery):
    """Что умеет бот"""
    text = (
        "🤖 *Что умеет FitnessBot:*\n\n"
        
        "📒 **Журнал тренировок**\n"
        "• Запись упражнений с подходами, весом, повторениями\n"
        "• История всех тренировок\n"
        "• Добавление своих упражнений\n\n"
        
        "📊 **Аналитика и статистика**\n"
        "• Отслеживание прогресса\n"
        "• Графики роста\n"
        "• Календарь тренировок\n"
        "• Статистика по мышечным группам\n\n"
        
        "🏆 **Мотивация**\n"
        "• Таблицы лидеров\n"
        "• Ачивки и достижения\n"
        "• Серии тренировок\n"
        "• Челленджи\n\n"
        
        "🛠 **Инструменты**\n"
        "• Таймер для тренировок\n"
        "• Экспорт данных\n"
        "• Рекомендации\n"
        "• Настройки\n\n"
        
        "⚡ **Быстрый и удобный**\n"
        "• Простой интерфейс\n"
        "• Быстрый ввод данных\n"
        "• Мгновенная статистика\n\n"
        
        "*Разработчик:* @hop31esss\n"
        "*Поддержка:* @hop31esss\n\n"
        
        "Спасибо за использование! 💪"
    )
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📒 Начать тренироваться", callback_data="add_workout"),
        InlineKeyboardButton(text="📊 Посмотреть статистику", callback_data="stats")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main")
    )
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()