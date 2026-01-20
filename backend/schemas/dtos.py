"""
DTOs (Data Transfer Objects) für API Requests und Responses.
Verwendet Pydantic V2 für Validierung.
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict, computed_field


# ============================================================
# Authentication DTOs
# ============================================================

class LoginRequest(BaseModel):
    """Login Request DTO."""
    email: EmailStr
    password: str = Field(..., min_length=6)
    device_token: Optional[str] = None
    
    model_config = ConfigDict(str_strip_whitespace=True)


class RegisterRequest(BaseModel):
    """Registrierung Request DTO."""
    vorname: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    avatar: Optional[str] = None
    nb_state: Optional[str] = None
    
    model_config = ConfigDict(str_strip_whitespace=True)


class AuthResponse(BaseModel):
    """Authentication Response DTO."""
    token: str
    user: "UserResponse"


# ============================================================
# User DTOs
# ============================================================

class UserResponse(BaseModel):
    """User Response DTO (ohne sensible Daten)."""
    id: int
    username: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_admin: bool = False
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(UserResponse):
    """Erweitertes User-Profil mit Statistiken."""
    friends_count: int = 0
    challenges_count: int = 0
    confirmations_count: int = 0


class UpdateUserRequest(BaseModel):
    """User Update Request DTO."""
    display_name: Optional[str] = Field(None, max_length=100)
    avatar_url: Optional[str] = None
    email: Optional[EmailStr] = None


# ============================================================
# Challenge DTOs
# ============================================================

class CreateChallengeRequest(BaseModel):
    """Challenge erstellen Request DTO."""
    name: str = Field(..., min_length=1, max_length=100)
    beschreibung: Optional[str] = Field(None, max_length=500)
    art: Optional[str] = None
    startAt: Optional[int] = None
    faelligeWochentage: list[int] = Field(default_factory=list)
    friendsToAdd: Optional[list[int]] = None
    days: Optional[int] = None
    dauerTage: int = Field(default=30, ge=1, le=365)
    erlaubteFailsTage: int = Field(default=0, ge=0)
    
    model_config = ConfigDict(str_strip_whitespace=True)


class ChallengeResponse(BaseModel):
    """Challenge Response DTO."""
    id: int
    creator_id: int
    title: str
    description: Optional[str] = None
    challenge_type: str
    status: str
    start_at: datetime
    duration_days: int
    allowed_fails: int
    due_weekdays: list[int]
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ChallengeDetailResponse(ChallengeResponse):
    """Detaillierte Challenge-Ansicht mit Mitgliedern."""
    members: list["ChallengeMemberResponse"] = []
    stats: Optional["ChallengeStatsResponse"] = None


class ChallengeMemberResponse(BaseModel):
    """Challenge-Mitglied Response DTO."""
    id: int
    user_id: int
    user: Optional[UserResponse] = None
    role: str
    joined_at: datetime
    
    @computed_field
    @property
    def avatar_url(self) -> Optional[str]:
        """Extrahiert avatar_url aus dem nested user Objekt."""
        return self.user.avatar_url if self.user else None
    
    @computed_field
    @property
    def display_name(self) -> Optional[str]:
        """Extrahiert display_name aus dem nested user Objekt."""
        return self.user.display_name if self.user else None
    
    @computed_field
    @property
    def avatar(self) -> Optional[str]:
        """Alias für avatar_url (Frontend Compatibility)."""
        return self.user.avatar_url if self.user else None
    
    model_config = ConfigDict(from_attributes=True)


class ChallengeStatsResponse(BaseModel):
    """Challenge-Statistiken Response DTO."""
    conf_count: int
    fail_count: int
    streak: int
    neg_streak: int
    best_streak: int = 0
    blocked: bool
    today_done: bool
    today_pending: bool
    
    model_config = ConfigDict(from_attributes=True)


class ConfirmChallengeRequest(BaseModel):
    """Challenge bestätigen Request DTO."""
    imageUrl: str = Field(..., min_length=1)
    caption: Optional[str] = Field(None, max_length=500)
    visibility: Optional[str] = Field(default="freunde")
    user_id: Optional[int] = None
    challenge_id: Optional[int] = None
    timestamp: Optional[int] = None


class ConfirmationResponse(BaseModel):
    """Confirmation Response DTO."""
    id: int
    challenge_id: int
    user_id: int
    user: Optional[UserResponse] = None
    image_url: str
    caption: Optional[str] = None
    visibility: str
    reactions_count: int = 0
    comments_count: int = 0
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class ChallengeInviteRequest(BaseModel):
    """Challenge-Einladung Request DTO."""
    toUserId: int = Field(..., gt=0)
    message: Optional[str] = Field(None, max_length=200)


# ============================================================
# Chat DTOs
# ============================================================

class ChatMessageRequest(BaseModel):
    """Chat-Nachricht Request DTO."""
    text: str = Field(..., min_length=1, max_length=1000)
    
    model_config = ConfigDict(str_strip_whitespace=True)


class ChatMessageResponse(BaseModel):
    """Chat-Nachricht Response DTO."""
    id: int
    challenge_id: int
    user_id: int
    user: Optional[UserResponse] = None
    message: str
    image_url: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Friends DTOs
# ============================================================

class FriendRequestRequest(BaseModel):
    """Freundschaftsanfrage Request DTO."""
    toUserId: int = Field(..., gt=0)
    message: Optional[str] = Field(None, max_length=200)


class FriendshipResponse(BaseModel):
    """Friendship Response DTO."""
    id: int
    user_id: int
    friend_id: int
    friend: Optional[UserResponse] = None
    status: str
    message: Optional[str] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Notification DTOs
# ============================================================

class NotificationResponse(BaseModel):
    """Notification Response DTO."""
    id: int
    user_id: int
    notification_type: str
    title: str
    message: str
    data: dict = {}
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Report DTOs
# ============================================================

class CreateReportRequest(BaseModel):
    """Report erstellen Request DTO."""
    reported_user_id: Optional[int] = None
    reported_content_id: Optional[int] = None
    content_type: Optional[str] = None
    reason: str = Field(..., min_length=1)
    description: Optional[str] = Field(None, max_length=1000)


class ReportResponse(BaseModel):
    """Report Response DTO."""
    id: int
    reporter_id: int
    reported_user_id: Optional[int] = None
    reported_content_id: Optional[int] = None
    content_type: Optional[str] = None
    reason: str
    description: Optional[str] = None
    status: str
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


# ============================================================
# Common DTOs
# ============================================================

class SuccessResponse(BaseModel):
    """Generische Success Response."""
    success: bool = True
    message: Optional[str] = None
    data: Optional[dict] = None


class ErrorResponse(BaseModel):
    """Generische Error Response."""
    error: str
    message: str
    details: Optional[dict] = None


class PaginationParams(BaseModel):
    """Pagination Parameter."""
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    
    @property
    def offset(self) -> int:
        """Berechnet Offset für SQL."""
        return (self.page - 1) * self.page_size
    
    @property
    def limit(self) -> int:
        """Gibt Limit zurück."""
        return self.page_size


class PaginatedResponse(BaseModel):
    """Paginierte Response."""
    items: list
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(cls, items: list, total: int, pagination: PaginationParams):
        """Factory-Methode für paginierte Response."""
        import math
        return cls(
            items=items,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size,
            total_pages=math.ceil(total / pagination.page_size) if total > 0 else 0
        )
