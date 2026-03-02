import re
from typing import Optional

def validate_exercise_name(name: str) -> bool:
    """Валидация названия упражнения"""
    if not name or len(name.strip()) < 2:
        return False
    if len(name) > 50:
        return False
    return True

def validate_sets_reps(value: str) -> Optional[int]:
    """Валидация подходов и повторений"""
    try:
        num = int(value)
        if 1 <= num <= 1000:
            return num
        return None
    except ValueError:
        return None

def validate_weight(weight: str) -> Optional[float]:
    """Валидация веса"""
    if weight.strip() in ['-', '0', '']:
        return None
    
    try:
        num = float(weight)
        if 0 <= num <= 1000:
            return num
        return None
    except ValueError:
        return None

def validate_duration(duration: str) -> Optional[int]:
    """Валидация длительности"""
    try:
        num = int(duration)
        if 1 <= num <= 1440:  # от 1 минуты до 24 часов
            return num
        return None
    except ValueError:
        return None

def sanitize_input(text: str) -> str:
    """Очистка пользовательского ввода"""
    # Удаляем потенциально опасные символы
    sanitized = re.sub(r'[;\"\']', '', text)
    return sanitized.strip()