from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import asyncio
from datetime import datetime

router = Router()

# Словарь для хранения активных таймеров
active_timers = {}

@router.callback_query(F.data == "timer")
async def timer_menu(callback: CallbackQuery):
    """Меню таймера"""
    def get_timer_keyboard():
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="⏱️ 30 сек", callback_data="timer_start:30"),
            InlineKeyboardButton(text="⏱️ 1 мин", callback_data="timer_start:60")
        )
        builder.row(
            InlineKeyboardButton(text="⏱️ 2 мин", callback_data="timer_start:120"),
            InlineKeyboardButton(text="⏱️ 5 мин", callback_data="timer_start:300")
        )
        builder.row(
            InlineKeyboardButton(text="⏱️ 10 мин", callback_data="timer_start:600"),
            InlineKeyboardButton(text="⏱️ 15 мин", callback_data="timer_start:900")
        )
        builder.row(
            InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
        )
        return builder.as_markup()
    
    text = (
        "⏱️ *Таймер тренировки*\n\n"
        "Выберите время для таймера. После запуска бот уведомит вас "
        "когда время истечет.\n\n"
        "Используйте для отдыха между подходами!"
    )
    await callback.message.edit_text(text, reply_markup=get_timer_keyboard())
    await callback.answer()

@router.callback_query(F.data.startswith("timer_start:"))
async def start_timer(callback: CallbackQuery):
    """Запуск таймера"""
    try:
        seconds = int(callback.data.split(":")[1])
        user_id = callback.from_user.id
        chat_id = callback.message.chat.id
        message_id = callback.message.message_id
        
        # Останавливаем предыдущий таймер, если есть
        if user_id in active_timers:
            active_timers[user_id].cancel()
        
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        time_text = f"{minutes}:{remaining_seconds:02d}" if minutes > 0 else f"{seconds} сек"
        
        # Обновляем сообщение с таймером
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="🛑 Остановить", callback_data="timer_stop"),
            InlineKeyboardButton(text="➕ Еще время", callback_data="timer")
        )
        
        await callback.message.edit_text(
            f"⏱️ *Таймер запущен на {time_text}*\n\n"
            f"Осталось: {time_text}\n"
            f"Статус: ⏳ Идет отсчет\n\n"
            f"Бот пришлет уведомление когда время выйдет.",
            reply_markup=builder.as_markup()
        )
        
        await callback.answer(f"Таймер на {time_text} запущен!")
        
        # Запускаем таймер в фоне
        timer_task = asyncio.create_task(
            run_timer(user_id, chat_id, message_id, seconds, time_text, callback.bot)
        )
        active_timers[user_id] = timer_task
        
    except Exception as e:
        await callback.answer(f"Ошибка: {str(e)}")

async def run_timer(user_id: int, chat_id: int, message_id: int, seconds: int, time_text: str, bot):
    """Фоновый таймер"""
    try:
        # Ждем указанное время
        await asyncio.sleep(seconds)
        
        # Отправляем уведомление
        try:
            await bot.send_message(
                chat_id=chat_id,
                text=f"🔔 *Таймер завершен!*\n\nВремя {time_text} вышло! Продолжайте тренировку! 💪",
                reply_markup=get_completed_timer_keyboard()
            )
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
        
        # Обновляем исходное сообщение
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=f"⏱️ *Таймер {time_text} завершен!*\n\n"
                     f"Время вышло! ✅\n\n"
                     f"Что дальше?",
                reply_markup=get_completed_timer_keyboard()
            )
        except:
            pass
        
        # Удаляем таймер из активных
        if user_id in active_timers:
            del active_timers[user_id]
            
    except asyncio.CancelledError:
        # Таймер был остановлен
        if user_id in active_timers:
            del active_timers[user_id]
    except Exception as e:
        print(f"Ошибка таймера: {e}")

@router.callback_query(F.data == "timer_stop")
async def stop_timer(callback: CallbackQuery):
    """Остановка таймера"""
    user_id = callback.from_user.id
    
    # Останавливаем таймер
    if user_id in active_timers:
        active_timers[user_id].cancel()
        del active_timers[user_id]
    
    await callback.message.edit_text(
        "⏹️ *Таймер остановлен*\n\n"
        "Вы можете запустить новый таймер или вернуться в меню.",
        reply_markup=get_completed_timer_keyboard()
    )
    await callback.answer("Таймер остановлен")

@router.callback_query(F.data == "timer_restart")
async def restart_timer(callback: CallbackQuery):
    """Перезапуск таймера"""
    # Просто возвращаемся в меню таймера
    await timer_menu(callback)

def get_completed_timer_keyboard():
    """Клавиатура после завершения таймера"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔄 Новый таймер", callback_data="timer"),
        InlineKeyboardButton(text="👋 В меню", callback_data="back_to_main")
    )
    return builder.as_markup()