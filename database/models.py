from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class User:
    user_id: int
    username: Optional[str]
    first_name: str
    last_name: Optional[str]
    created_at: datetime
    is_subscribed: bool = False
    is_admin: bool = False

@dataclass
class Workout:
    id: int
    user_id: int
    exercise_name: str
    sets: int
    reps: int
    weight: Optional[float]
    duration: Optional[int]
    notes: Optional[str]
    created_at: datetime

@dataclass
class Exercise:
    id: int
    user_id: int
    name: str
    alias: Optional[str]

@dataclass
class Achievement:
    id: int
    user_id: int
    achievement_type: str
    achievement_name: str
    achieved_at: datetime

@dataclass
class UserStats:
    user_id: int
    total_workouts: int
    total_exercises: int
    current_streak: int
    longest_streak: int
    last_workout_date: Optional[datetime]