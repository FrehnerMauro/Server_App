"""
Repositories Module - Data Access Layer.
"""
from backend.repositories.base import BaseRepository
from backend.repositories.user_repository import UserRepository, AuthTokenRepository
from backend.repositories.challenge_repository import (
    ChallengeRepository,
    ChallengeMemberRepository,
    ChallengeStatsRepository,
    ConfirmationRepository,
    ChallengeChatRepository,
)
from backend.repositories.friend_repository import FriendshipRepository
from backend.repositories.notification_repository import (
    NotificationRepository,
    ReportRepository,
)

__all__ = [
    "BaseRepository",
    "UserRepository",
    "AuthTokenRepository",
    "ChallengeRepository",
    "ChallengeMemberRepository",
    "ChallengeStatsRepository",
    "ConfirmationRepository",
    "ChallengeChatRepository",
    "FriendshipRepository",
    "NotificationRepository",
    "ReportRepository",
]
