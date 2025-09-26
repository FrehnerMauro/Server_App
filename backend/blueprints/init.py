# blueprints/__init__.py
"""Flask Blueprints: auth, users, friends, challenges, feed, notifications, admin."""
from .auth_routes import bp as auth_routes
from .users import bp as users
from .friends import bp as friends
from .challenges import bp as challenges
from .feed import bp as feed
from .notifications import bp as notifications
from .admin import bp as admin

__all__ = ["auth_routes", "users", "friends", "challenges", "feed", "notifications", "admin"]