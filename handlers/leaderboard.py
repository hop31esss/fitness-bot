from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from database.base import db

router = Router()

@router.callback_query(F.data == "leaderboard")
async def leaderboard_menu(callback: CallbackQuery):
    """Меню таблиц лидеров"""
    text = "🏆 *Таблицы лидеров*\n\nВыберите тип:"
    keyboard = get_leaderboard_keyboard()
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

@router.callback_query(F.data == "global_leaderboard")
async def global_leaderboard(callback: CallbackQuery):
    """Глобальная таблица лидеров"""
    user_id = callback.from_user.id
    
    # Получаем топ-20 пользователей по количеству тренировок (из workout_sessions)
    query = """
        SELECT 
            u.user_id,
            u.first_name,
            COUNT(DISTINCT ws.id) as total_workouts
        FROM users u
        LEFT JOIN workout_sessions ws ON u.user_id = ws.user_id
        GROUP BY u.user_id
        ORDER BY total_workouts DESC
        LIMIT 20
    """
    leaders = await db.fetch_all(query)
    
    # Получаем место текущего пользователя
    user_rank = 0
    all_users = await db.fetch_all("""
        SELECT 
            u.user_id,
            COUNT(DISTINCT ws.id) as total_workouts
        FROM users u
        LEFT JOIN workout_sessions ws ON u.user_id = ws.user_id
        GROUP BY u.user_id
        ORDER BY total_workouts DESC
    """)
    
    for i, user in enumerate(all_users, 1):
        if user['user_id'] == user_id:
            user_rank = i
            break
    
    if leaders:
        text = "🏆 *Глобальный рейтинг*\n\n"
        
        for i, user in enumerate(leaders, 1):
            # Определяем эмодзи для первых трех мест
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."
            
            # Имя пользователя
            name = user['first_name'] or f"Пользователь {user['user_id']}"
            
            # Если это текущий пользователь
            if user['user_id'] == user_id:
                name = f"⭐ {name} (Это вы!)"
            
            text += f"{emoji} *{name}* — {user['total_workouts']} тренировок\n"
        
        if user_rank > 20:
            text += f"\n...\n{user_rank}. *Вы* — {all_users[user_rank-1]['total_workouts']} тренировок"
    else:
        text = "🏆 *Глобальный рейтинг*\n\nПока нет данных для таблицы лидеров"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_leaderboard_keyboard())
    await callback.answer()

@router.callback_query(F.data == "friends_leaderboard")
async def friends_leaderboard(callback: CallbackQuery):
    """Таблица лидеров среди друзей"""
    user_id = callback.from_user.id
    
    # Получаем друзей пользователя
    friends = await db.fetch_all("""
        SELECT 
            CASE 
                WHEN f.user_id = ? THEN f.friend_id
                ELSE f.user_id
            END as friend_id
        FROM friends f
        WHERE (f.user_id = ? OR f.friend_id = ?) AND f.status = 'accepted'
    """, (user_id, user_id, user_id))
    
    friend_ids = [user_id]  # включаем самого пользователя
    friend_ids.extend([f['friend_id'] for f in friends])
    
    if not friend_ids:
        text = "👥 *Рейтинг друзей*\n\nУ вас пока нет друзей.\n\n➕ Добавьте друзей, чтобы соревноваться!"
    else:
        # Формируем плейсхолдеры для SQL запроса
        placeholders = ','.join(['?'] * len(friend_ids))
        
        query = f"""
            SELECT 
                u.user_id,
                u.first_name,
                COUNT(DISTINCT ws.id) as total_workouts
            FROM users u
            LEFT JOIN workout_sessions ws ON u.user_id = ws.user_id
            WHERE u.user_id IN ({placeholders})
            GROUP BY u.user_id
            ORDER BY total_workouts DESC
        """
        
        leaders = await db.fetch_all(query, friend_ids)
        
        text = "👥 *Рейтинг друзей*\n\n"
        
        for i, user in enumerate(leaders, 1):
            # Определяем эмодзи для первых трех мест
            if i == 1:
                emoji = "🥇"
            elif i == 2:
                emoji = "🥈"
            elif i == 3:
                emoji = "🥉"
            else:
                emoji = f"{i}."
            
            # Имя пользователя
            name = user['first_name'] or f"Пользователь {user['user_id']}"
            
            # Если это текущий пользователь
            if user['user_id'] == user_id:
                name = f"⭐ {name} (Это вы!)"
            
            text += f"{emoji} *{name}* — {user['total_workouts']} тренировок\n"
    
    await callback.message.edit_text(text, reply_markup=get_back_to_leaderboard_keyboard())
    await callback.answer()

def get_leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура лидербордов"""
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text="🌍 Глобальный", callback_data="global_leaderboard"),
        InlineKeyboardButton(text="👥 Среди друзей", callback_data="friends_leaderboard")
    )
    builder.row(
        InlineKeyboardButton(text="↩️ Назад", callback_data="back_to_main")
    )
    
    return builder.as_markup()

def get_back_to_leaderboard_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура возврата к лидербордам"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="↩️ К ЛИДЕРБОРДАМ", callback_data="leaderboard"),
        InlineKeyboardButton(text="🏠 ГЛАВНОЕ МЕНЮ", callback_data="back_to_main")
    )
    return builder.as_markup()