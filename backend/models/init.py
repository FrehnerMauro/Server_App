# models/__init__.py
"""Pydantic Schemas fuer Requests/Responses."""
from .schemas import (
    RegisterBody,
    LoginBody,
    CreateChallengeBody,
    ChatBody,
    ConfirmBody,
    ChallengeInviteBody,
    FriendReqBody,
)

__all__ = [
    "RegisterBody",
    "LoginBody",
    "CreateChallengeBody",
    "ChatBody",
    "ConfirmBody",
    "ChallengeInviteBody",
    "FriendReqBody",
]