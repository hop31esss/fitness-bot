import calendar
from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.progress_analytics import (
    fetch_day_exercises,
    fetch_range_totals,
    fetch_volume_by_date,
    format_kg,
)

router = Router()


def _month_bounds(year: int, month: int) -> tuple[str, str]:
    start = datetime(year, month, 1)
    if month == 12:
        end = datetime(year, 12, 31)
    else:
        end = datetime(year, month + 1, 1) - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _next_month(year: int, month: int) -> tuple[int, int]:
    if month == 12:
        return year + 1, 1
    return year, month + 1


async def _render_calendar(callback: CallbackQuery, year: int, month: int) -> None:
    user_id = callback.from_user.id
    start, end = _month_bounds(year, month)
    prev_year, prev_month = _previous_month(year, month)
    prev_start, prev_end = _month_bounds(prev_year, prev_month)

    workouts = await fetch_volume_by_date(user_id, start, end)
    previous = await fetch_range_totals(user_id, prev_start, prev_end)
    workout_dict = {
        str(row["workout_date"])[:10]: {
            "count": row["workout_count"],
            "volume": row["total_volume"],
        }
        for row in workouts
    }

    month_name = calendar.month_name[month]
    text = f"📅 *Календарь тренировок — {month_name} {year}*\n\n"
    if previous["count"]:
        text += (
            f"📊 *{calendar.month_name[prev_month]}:* {previous['count']} тренировок, "
            f"{format_kg(previous['volume'])} кг\n\n"
        )
    text += "*Нажми на день, чтобы посмотреть детали:*\n"

    builder = InlineKeyboardBuilder()
    for day in ("Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"):
        builder.button(text=day, callback_data="ignore")
    builder.adjust(7)

    for week in calendar.monthcalendar(year, month):
        for day in week:
            if day == 0:
                builder.button(text=" ", callback_data="ignore")
                continue
            current_date = f"{year}-{month:02d}-{day:02d}"
            if current_date in workout_dict:
                count = workout_dict[current_date]["count"]
                emoji = "🔥" if count >= 3 else "💪" if count == 2 else "✅"
                builder.button(text=f"{emoji}{day}", callback_data=f"day_detail:{current_date}")
            else:
                builder.button(text=f" {day} ", callback_data=f"day_empty:{current_date}")
    builder.adjust(7)

    total_workouts = sum(row["workout_count"] for row in workouts)
    total_volume = sum(float(row["total_volume"] or 0) for row in workouts)
    text += f"\n📊 *{month_name}:*\n"
    text += f"• Дней с тренировками: {len(workouts)}\n"
    text += f"• Всего тренировок: {total_workouts}\n"
    text += f"• Общий объем: {format_kg(total_volume)} кг\n"
    if workouts:
        text += f"• Средний объем за день: {format_kg(total_volume / len(workouts))} кг\n"

    next_year, next_month = _next_month(year, month)
    builder.row(
        InlineKeyboardButton(text="◀️ Предыдущий", callback_data=f"month_nav:{prev_year}:{prev_month}"),
        InlineKeyboardButton(text="▶️ Следующий", callback_data=f"month_nav:{next_year}:{next_month}"),
    )
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="progress_stats"),
        InlineKeyboardButton(text="↩️ В прогресс", callback_data="menu_progress"),
    )
    await callback.message.edit_text(text, reply_markup=builder.as_markup())


@router.callback_query(F.data == "calendar")
async def show_calendar(callback: CallbackQuery):
    now = datetime.now()
    await _render_calendar(callback, now.year, now.month)
    await callback.answer()


@router.callback_query(F.data.startswith("month_nav:"))
async def navigate_month(callback: CallbackQuery):
    try:
        _, year_str, month_str = callback.data.split(":")
        await _render_calendar(callback, int(year_str), int(month_str))
        await callback.answer()
    except Exception as exc:
        await callback.answer(f"Ошибка: {exc}")


@router.callback_query(F.data.startswith("day_detail:"))
async def show_day_detail(callback: CallbackQuery):
    date_str = callback.data.split(":")[1]
    workouts = await fetch_day_exercises(callback.from_user.id, date_str)
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
    text = (
        f"📅 *Детали дня: {day_name}, {date_obj.day} "
        f"{calendar.month_name[date_obj.month]} {date_obj.year}*\n\n"
    )
    if workouts:
        total_volume = sum(item["volume"] for item in workouts)
        total_sets = sum(item["sets"] for item in workouts)
        session_count = len({item["session_id"] for item in workouts})
        text += f"🏋️ *Тренировок: {session_count}*\n"
        text += f"⚖️ *Общий объем: {format_kg(total_volume)} кг*\n"
        text += f"📊 *Подходы: {total_sets}*\n\n*Упражнения:*\n"
        for index, workout in enumerate(workouts, 1):
            weight_text = f"{workout['weight']:g} кг" if workout["weight"] else "без веса"
            extra = f" | {workout['time']}" if workout.get("time") else ""
            text += (
                f"{index}. *{workout['exercise_name']}*\n"
                f"   {workout['sets']}×{int(workout['reps'])} | {weight_text}"
                f"{extra} | {format_kg(workout['volume'])} кг\n"
            )
    else:
        text += "В этот день не было тренировок.\n"

    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📅 Вернуться в календарь", callback_data="calendar"),
        InlineKeyboardButton(text="➕ Добавить тренировку", callback_data="add_workout"),
    )
    builder.row(InlineKeyboardButton(text="↩️ В прогресс", callback_data="menu_progress"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("day_empty:"))
async def show_empty_day(callback: CallbackQuery):
    date_str = callback.data.split(":")[1]
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    day_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"][date_obj.weekday()]
    text = (
        f"📅 *{day_name}, {date_obj.day} {calendar.month_name[date_obj.month]} {date_obj.year}*\n\n"
        "В этот день не было тренировок.\n\n"
        "Хотите добавить тренировку?"
    )
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Добавить тренировку", callback_data=f"add_workout_to_day:{date_str}"),
        InlineKeyboardButton(text="📅 Календарь", callback_data="calendar"),
    )
    builder.row(InlineKeyboardButton(text="↩️ В прогресс", callback_data="menu_progress"))
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery):
    await callback.answer()
