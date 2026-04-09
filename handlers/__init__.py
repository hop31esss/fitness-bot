from .start import router as start_router
from .training import router as training_router
from .profile import router as profile_router
from .leaderboard import router as leaderboard_router
from .achievements import router as achievements_router
from .timer import router as timer_router
from .stats import router as stats_router
from .calendar import router as calendar_router
from .exercises import router as exercises_router
from .settings import router as settings_router
from .recommendations import router as recommendations_router
from .challenges import router as challenges_router
from .features import router as features_router
from .feed import router as feed_router
from .daily_routine import router as daily_routine_router
from .music import router as music_router
from .friends import router as friends_router
from .one_rep_max import router as one_rep_max_router
from .calorie_tracker import router as calorie_tracker_router
from .premium import router as premium_router
from .admin_panel import router as admin_panel_router
from .common import router as common_router        # common должен быть ПОСЛЕДНИМ!

__all__ = [
    "start_router",
    "training_router",
    "profile_router",
    "leaderboard_router",
    "achievements_router",
    "timer_router", 
    "stats_router",
    "calendar_router",
    "exercises_router",
    "settings_router",
    "recommendations_router",
    "challenges_router",
    "features_router",
    "feed_router",
    "daily_routine_router",
    "music_router",
    "friends_router",
    "one_rep_max_router",
    "calorie_tracker_router",
    "premium_router",
    "admin_panel_router",
    "common_router",  # common должен быть последним!
]