"""
API Routes Module - HTTP Endpoints.
"""
from backend.api.routes import (
    auth_routes,
    user_routes,
    challenge_routes,
    friend_routes,
    notification_routes,
)

__all__ = [
    "auth_routes",
    "user_routes",
    "challenge_routes",
    "friend_routes",
    "notification_routes",
]
