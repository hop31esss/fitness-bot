from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db
from services.notifications import send_broadcast_message
from keyboards.admin import get_admin_keyboard

router = Router()

class BroadcastStates(StatesGroup):
    waiting_message = State()
    waiting_confirmation = State()

@router.message(Command("admin"))
async def admin_panel(message: Message):
    """Админ-панель"""
    user_id = message.from_user.id
    
    # Проверяем, является ли пользователь админом
    user = await db.fetch_one(
        "SELECT is_admin FROM users WHERE user_id = ?", 
        (user_id,)
    )
    
    if not user or not user['is_admin']:
        await message.answer("У вас нет доступа к админ-панели")
        return
    
    text = (
        "⚙️ *Админ-панель*\n\n"
        "Доступные функции:\n"
        "• 📢 Отправка рассылок всем пользователям\n"
        "• 📊 Просмотр статистики бота\n"
        "• 👥 Управление пользователями\n"
        "• ⚙️ Настройки бота\n\n"
        "Выберите действие:"
    )
    
    keyboard = get_admin_keyboard()
    await message.answer(text, reply_markup=keyboard)

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки"""
    await callback.message.answer(
        "📢 *Создание рассылки*\n\n"
        "Введите сообщение для отправки всем пользователям:\n\n"
        "Можно использовать разметку:\n"
        "• *жирный*\n"
        "• _курсив_\n"
        "• `код`\n\n"
        "Или отправьте /cancel для отмены."
    )
    
    await state.set_state(BroadcastStates.waiting_message)
    await callback.answer()

@router.message(BroadcastStates.waiting_message)
async def process_broadcast_message(message: Message, state: FSMContext):
    """Обработка сообщения для рассылки"""
    if message.text and message.text.startswith('/cancel'):
        await message.answer("❌ Рассылка отменена.")
        await state.clear()
        return
    
    broadcast_text = message.text
    
    if not broadcast_text or len(broadcast_text.strip()) < 5:
        await message.answer("Сообщение слишком короткое. Введите сообщение длиннее 5 символов:")
        return
    
    # Сохраняем сообщение
    await state.update_data(broadcast_text=broadcast_text)
    
    # Показываем предпросмотр
    await message.answer(
        f"📋 *Предпросмотр рассылки:*\n\n{broadcast_text}\n\n"
        f"Отправить это сообщение всем пользователям?",
        reply_markup=get_broadcast_confirmation_keyboard()
    )
    
    await state.set_state(BroadcastStates.waiting_confirmation)

@router.callback_query(F.data == "broadcast_confirm", BroadcastStates.waiting_confirmation)
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Подтверждение и отправка рассылки"""
    data = await state.get_data()
    broadcast_text = data['broadcast_text']
    
    # Показываем что началась рассылка
    await callback.message.edit_text("📤 Начинаю рассылку... Это может занять некоторое время.")
    
    # Отправляем рассылку
    success_count = await send_broadcast_message(callback.bot, broadcast_text)
    
    # Обновляем сообщение
    await callback.message.edit_text(
        f"✅ *Рассылка завершена!*\n\n"
        f"Сообщение отправлено {success_count} пользователям.\n\n"
        f"📝 Текст сообщения:\n{broadcast_text}",
        reply_markup=get_admin_back_keyboard()
    )
    
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "broadcast_cancel", BroadcastStates.waiting_confirmation)
async def cancel_broadcast(callback: CallbackQuery, state: FSMContext):
    """Отмена рассылки"""
    await callback.message.edit_text("❌ Рассылка отменена.")
    await state.clear()
    await callback.answer()

@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    """Статистика бота для админа"""
    # Получаем общую статистику
    total_users = await db.fetch_one("SELECT COUNT(*) as count FROM users")
    total_workouts = await db.fetch_one("SELECT COUNT(*) as count FROM workouts")
    active_today = await db.fetch_one(
        "SELECT COUNT(DISTINCT user_id) as count FROM workouts WHERE date(created_at) = date('now')"
    )
    active_week = await db.fetch_one(
        "SELECT COUNT(DISTINCT user_id) as count FROM workouts WHERE created_at > datetime('now', '-7 days')"
    )
    
    # Топ пользователей
    top_users = await db.fetch_all("""
        SELECT u.user_id, u.username, u.first_name, us.total_workouts 
        FROM user_stats us
        JOIN users u ON us.user_id = u.user_id
        ORDER BY us.total_workouts DESC
        LIMIT 5
    """)
    
    text = (
        "📊 *Статистика бота:*\n\n"
        f"👥 Всего пользователей: {total_users['count']}\n"
        f"🏋️ Всего тренировок: {total_workouts['count']}\n"
        f"🔥 Активных сегодня: {active_today['count']}\n"
        f"📈 Активных за неделю: {active_week['count']}\n\n"
    )
    
    if top_users:
        text += "🏆 *Топ-5 пользователей:*\n"
        for i, user in enumerate(top_users, 1):
            name = user['username'] or user['first_name']
            text += f"{i}. {name} - {user['total_workouts']} тренировок\n"
    
    await callback.message.edit_text(text, reply_markup=get_admin_back_keyboard())
    await callback.answer()

def get_broadcast_confirmation_keyboard():
    """Клавиатура подтверждения рассылки"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ Отправить", callback_data="broadcast_confirm"),
        InlineKeyboardButton(text="❌ Отменить", callback_data="broadcast_cancel")
    )
    return builder.as_markup()

def get_admin_back_keyboard():
    """Клавиатура возврата в админ-панель"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="admin_panel")
    )
    return builder.as_markup()