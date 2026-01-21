"""
Schemas Module - DTOs für API Requests und Responses.
"""
from backend.schemas.dtos import (
    # Auth
    LoginRequest,
    RegisterRequest,
    AuthResponse,
    # User
    UserResponse,
    UserProfileResponse,
    UpdateUserRequest,
    # Challenge
    CreateChallengeRequest,
    ChallengeResponse,
    ChallengeDetailResponse,
    ChallengeMemberResponse,
    ChallengeStatsResponse,
    ConfirmChallengeRequest,
    ConfirmationResponse,
    ChallengeInviteRequest,
    # Chat
    ChatMessageRequest,
    ChatMessageResponse,
    # Friends
    FriendRequestRequest,
    FriendshipResponse,
    # Notifications
    NotificationResponse,
    # Reports
    CreateReportRequest,
    ReportResponse,
    # Common
    SuccessResponse,
    ErrorResponse,
    PaginationParams,
    PaginatedResponse,
)

__all__ = [
    # Auth
    "LoginRequest",
    "RegisterRequest",
    "AuthResponse",
    # User
    "UserResponse",
    "UserProfileResponse",
    "UpdateUserRequest",
    # Challenge
    "CreateChallengeRequest",
    "ChallengeResponse",
    "ChallengeDetailResponse",
    "ChallengeMemberResponse",
    "ChallengeStatsResponse",
    "ConfirmChallengeRequest",
    "ConfirmationResponse",
    "ChallengeInviteRequest",
    # Chat
    "ChatMessageRequest",
    "ChatMessageResponse",
    # Friends
    "FriendRequestRequest",
    "FriendshipResponse",
    # Notifications
    "NotificationResponse",
    # Reports
    "CreateReportRequest",
    "ReportResponse",
    # Common
    "SuccessResponse",
    "ErrorResponse",
    "PaginationParams",
    "PaginatedResponse",
]
