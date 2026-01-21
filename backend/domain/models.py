"""
Domain Models - Core Business Entities.
Diese Klassen repräsentieren die Business-Domain, unabhängig von der Datenbank.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


# Enums
class UserRole(str, Enum):
    """Benutzer-Rollen."""
    USER = "user"
    ADMIN = "admin"


class FriendshipStatus(str, Enum):
    """Status einer Freundschaftsanfrage."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    DECLINED = "declined"
    BLOCKED = "blocked"


class ChallengeStatus(str, Enum):
    """Status einer Challenge."""
    DRAFT = "draft"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ChallengeType(str, Enum):
    """Art der Challenge."""
    PERSONAL = "personal"
    GROUP = "group"


class ConfirmationVisibility(str, Enum):
    """Sichtbarkeit einer Bestätigung."""
    PRIVATE = "privat"
    FRIENDS = "freunde"
    PUBLIC = "oeffentlich"


class NotificationType(str, Enum):
    """Art der Benachrichtigung."""
    FRIEND_REQUEST = "friend_request"
    FRIEND_ACCEPTED = "friend_accepted"
    CHALLENGE_INVITE = "challenge_invite"
    CHALLENGE_CHAT = "challenge_chat"
    CHALLENGE_COMPLETION = "challenge_completion"
    SYSTEM = "system"


# Domain Models
@dataclass
class User:
    """Benutzer Domain Model."""
    id: int
    username: str
    email: str
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def is_admin(self) -> bool:
        """Prüft ob Benutzer Admin ist."""
        return self.role == UserRole.ADMIN


@dataclass
class AuthToken:
    """Authentication Token."""
    id: int
    user_id: int
    token: str
    device: Optional[str] = None
    expires_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Friendship:
    """Freundschaft zwischen zwei Benutzern."""
    id: int
    user_id: int
    friend_id: int
    status: FriendshipStatus
    message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Challenge:
    """Challenge Domain Model."""
    id: int
    creator_id: int
    title: str
    description: Optional[str] = None
    challenge_type: ChallengeType = ChallengeType.PERSONAL
    status: ChallengeStatus = ChallengeStatus.DRAFT
    start_at: datetime = field(default_factory=datetime.utcnow)
    duration_days: int = 30
    allowed_fails: int = 0
    due_weekdays: list[int] = field(default_factory=list)  # 0=Mo, 6=So
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    
    @property
    def end_at(self) -> datetime:
        """Berechnet Enddatum der Challenge."""
        from datetime import timedelta
        return self.start_at + timedelta(days=self.duration_days)
    
    @property
    def is_active(self) -> bool:
        """Prüft ob Challenge aktiv ist."""
        now = datetime.utcnow()
        return (
            self.status == ChallengeStatus.ACTIVE
            and self.start_at <= now <= self.end_at
        )


@dataclass
class ChallengeMember:
    """Mitglied einer Challenge."""
    id: int
    challenge_id: int
    user_id: int
    role: str = "member"  # creator, member
    joined_at: datetime = field(default_factory=datetime.utcnow)
    left_at: Optional[datetime] = None
    
    @property
    def is_active(self) -> bool:
        """Prüft ob Mitglied noch aktiv ist."""
        return self.left_at is None


@dataclass
class ChallengeStats:
    """Statistiken eines Challenge-Mitglieds."""
    id: int
    challenge_id: int
    user_id: int
    conf_count: int = 0  # Bestätigungen
    fail_count: int = 0  # Fehlschläge
    streak: int = 0  # Aktuelle Streak
    neg_streak: int = 0  # Negative Streak
    best_streak: int = 0  # Beste Streak
    blocked: bool = False  # Challenge blockiert?
    today_done: bool = False  # Heute erledigt?
    today_pending: bool = True  # Heute noch offen?
    last_computed: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Confirmation:
    """Bestätigung einer Challenge-Aktivität."""
    id: int
    challenge_id: int
    user_id: int
    image_url: str
    caption: Optional[str] = None
    visibility: ConfirmationVisibility = ConfirmationVisibility.FRIENDS
    reactions_count: int = 0
    comments_count: int = 0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChallengeChat:
    """Chat-Nachricht in einer Challenge."""
    id: int
    challenge_id: int
    user_id: int
    message: str
    image_url: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Notification:
    """Benachrichtigung für einen Benutzer."""
    id: int
    user_id: int
    notification_type: NotificationType
    title: str
    message: str
    data: dict = field(default_factory=dict)
    is_read: bool = False
    read_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class UserDevice:
    """Gerät eines Benutzers für Push-Notifications."""
    id: int
    user_id: int
    device_token: str
    device_type: str = "ios"  # ios, android
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class Report:
    """Meldung über unangemessenen Inhalt."""
    id: int
    reporter_id: int
    reported_user_id: Optional[int] = None
    reported_content_id: Optional[int] = None
    content_type: Optional[str] = None  # confirmation, chat, profile
    reason: str = ""
    description: Optional[str] = None
    status: str = "pending"  # pending, reviewed, resolved
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None
