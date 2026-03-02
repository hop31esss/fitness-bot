from typing import List, Dict

def format_stats(stats: Dict) -> str:
    """Форматирование статистики"""
    text = (
        "📊 *Ваша статистика:*\n\n"
        f"🏋️ Всего тренировок: {stats['total_workouts']}\n"
        f"💪 Уникальных упражнений: {stats['total_exercises']}\n"
        f"🔥 Текущая серия: {stats['current_streak']} дней\n"
        f"🏆 Самая длинная серия: {stats['longest_streak']} дней\n"
    )
    
    if stats['last_workout_date']:
        text += f"📅 Последняя тренировка: {stats['last_workout_date'][:10]}\n"
    
    return text

def format_leaderboard(leaders: List[Dict], title: str) -> str:
    """Форматирование таблицы лидеров"""
    text = f"🏆 *{title}*\n\n"
    
    for i, leader in enumerate(leaders, 1):
        username = leader['username'] or f"{leader['first_name']} {leader['last_name'] or ''}".strip()
        emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        
        text += f"{emoji} {username} - {leader['total_workouts']} тренировок\n"
    
    return text

def format_workout(workout: Dict) -> str:
    """Форматирование информации о тренировке"""
    weight_text = f"{workout['weight']} кг" if workout['weight'] else "без веса"
    
    text = (
        f"🏋️ *{workout['exercise_name']}*\n"
        f"📊 Подходы: {workout['sets']}\n"
        f"🔄 Повторения: {workout['reps']}\n"
        f"⚖️ Вес: {weight_text}\n"
        f"📅 Дата: {workout['created_at'][:16]}"
    )
    
    if workout.get('notes'):
        text += f"\n📝 Заметки: {workout['notes']}"
    
    return text