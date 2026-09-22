"""Premium info, paywalls, and CTA into the existing payment flow."""

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.premium_access import has_premium_access

router = Router()

PREMIUM_FEATURES = (
    "Динамика силы и расчётный 1ПМ",
    "Распределение нагрузки по мышцам",
    "Личные рекорды и сравнение периодов",
    "Подробная статистика за 7/30/90 дней",
    "AI-разбор прогресса",
    "Трекер калорий и экспорт данных",
)


def premium_cta_markup(back_callback: str = "menu_profile") -> object:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👑 Оформить Premium", callback_data="payment"))
    builder.row(InlineKeyboardButton(text="↩️ Назад", callback_data=back_callback))
    return builder.as_markup()


def build_teaser_paywall(title: str, visible_lines: list[str], extra: list[str] | None = None) -> str:
    blocks = [title, "", *visible_lines, "", "────────────────", "", "💎 *В PREMIUM:*"]
    for item in extra or PREMIUM_FEATURES:
        blocks.append(f"• {item}")
    return "\n".join(blocks)


async def build_premium_screen(user_id: int) -> tuple[str, object]:
    if await has_premium_access(user_id):
        text = (
            "👑 *Premium активен*\n\n"
            "Доступны углублённые разделы внутри Прогресса и AI-советов:\n"
            "• сила, объём, мышцы, регулярность, рекорды\n"
            "• AI-анализ на основе ваших цифр\n"
            "• калькулятор 1ПМ, калории, друзья и экспорт\n\n"
            "Новых кнопок в главном меню нет — Premium открывает глубину."
        )
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(text="📊 Прогресс", callback_data="progress_stats"),
            InlineKeyboardButton(text="🤖 AI-советы", callback_data="ai_advice"),
        )
        builder.row(
            InlineKeyboardButton(text="🏋️ 1ПМ", callback_data="one_rep_max"),
            InlineKeyboardButton(text="🔥 Калории", callback_data="calorie_tracker"),
        )
        builder.row(
            InlineKeyboardButton(text="⭐ Функции", callback_data="premium_features"),
            InlineKeyboardButton(text="↩️ В профиль", callback_data="menu_profile"),
        )
        return text, builder.as_markup()

    text = (
        "👑 *Premium*\n\n"
        "Базовый прогресс уже доступен. Premium делает разбор глубже:\n\n"
        + "\n".join(f"• {item}" for item in PREMIUM_FEATURES)
        + "\n\nОплата картой РФ или Telegram Stars — без переписки с администратором."
    )
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👑 Оформить Premium", callback_data="payment"))
    builder.row(
        InlineKeyboardButton(text="⭐ Что входит", callback_data="premium_features"),
        InlineKeyboardButton(text="↩️ В профиль", callback_data="menu_profile"),
    )
    return text, builder.as_markup()


@router.callback_query(F.data == "show_premium_info")
async def show_premium_info(callback: CallbackQuery):
    text, markup = await build_premium_screen(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "premium_features")
async def premium_features_menu(callback: CallbackQuery):
    premium = await has_premium_access(callback.from_user.id)
    text = (
        "⭐ *Premium-функции*\n\n"
        "Они открываются внутри существующих разделов:\n\n"
        "▫️ *Прогресс* — 5 блоков аналитики и AI-разбор\n"
        "▫️ *1ПМ* — расчёт и отслеживание силы\n"
        "▫️ *Калории* — нормы и дневник еды\n"
        "▫️ *Друзья / челленджи*\n"
        "▫️ *Экспорт* данных\n"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="advanced_stats"),
        InlineKeyboardButton(text="🏋️ 1ПМ", callback_data="one_rep_max"),
    )
    builder.row(
        InlineKeyboardButton(text="🔥 Калории", callback_data="calorie_tracker"),
        InlineKeyboardButton(text="👥 Друзья", callback_data="friends_menu"),
    )
    builder.row(
        InlineKeyboardButton(text="🤖 AI-советы", callback_data="ai_advice"),
        InlineKeyboardButton(text="📤 Экспорт", callback_data="export_data"),
    )
    if not premium:
        builder.row(InlineKeyboardButton(text="👑 Оформить Premium", callback_data="payment"))
    builder.row(InlineKeyboardButton(text="↩️ В профиль", callback_data="menu_profile"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.message(Command("premium"))
async def cmd_premium(message: Message):
    text, markup = await build_premium_screen(message.from_user.id)
    await message.answer(text, reply_markup=markup)
