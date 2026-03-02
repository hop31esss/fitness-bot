from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from keyboards.main import get_main_keyboard

router = Router()

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    """Возврат в главное меню"""
    text = "👋 Выбирай, что сделать:"
    keyboard = get_main_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.message()
async def unknown_message(message: Message):
    """Обработка неизвестных сообщений"""
    text = "👋 Привет! Используй меню ниже или команду /start"
    keyboard = get_main_keyboard()
    await message.answer(text, reply_markup=keyboard)

@router.callback_query()
async def handle_all_callbacks(callback: CallbackQuery):
    """Обработчик всех callback-ов которые не нашли другие обработчики"""
    unknown_callbacks = {
        "suggest_idea": "💡 Предложить идею",
        "suggest_feature": "💡 Предложить функцию",
        "other_projects": "🚀 Другие проекты",
        "settings_profile": "👤 Профиль",
        "settings_theme": "📱 Оформление",
        "settings_language": "🌍 Язык",
        "edit_profile_name": "✏️ Изменить имя",
        "edit_profile_contacts": "📧 Изменить контакты",
        "set_language_ru": "🇷🇺 Русский",
        "set_language_en": "🇬🇧 English",
        "set_units_kg": "📏 Килограммы",
        "set_units_lbs": "⚖️ Фунты",
        "edit_aliases": "🔤 Редактировать алиасы"
    }
    
  # Только для действительно нереализованных функций
@router.callback_query(F.data.in_([
    "exercise_aliases",  # если эти функции еще не готовы
]))
async def under_development(callback: CallbackQuery):
    await callback.answer("Функция в разработке 🚀")# Только для действительно нереализованных функций
@router.callback_query(F.data.in_([
    "exercise_aliases",  # если эти функции еще не готовы
]))
async def under_development(callback: CallbackQuery):
    await callback.answer("Функция в разработке 🚀")