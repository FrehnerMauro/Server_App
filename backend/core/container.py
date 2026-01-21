"""
Dependency Injection Container.
Zentrale Verwaltung von Service-Instanzen.
"""
from functools import lru_cache
from typing import Optional

from backend.repositories import (
    UserRepository,
    AuthTokenRepository,
    ChallengeRepository,
    ChallengeMemberRepository,
    ChallengeStatsRepository,
    ConfirmationRepository,
    ChallengeChatRepository,
    FriendshipRepository,
    NotificationRepository,
    ReportRepository,
)
from backend.services import (
    AuthService,
    UserService,
    ChallengeService,
    FriendService,
    NotificationService,
)


class Container:
    """
    Dependency Injection Container.
    Singleton Pattern für Service-Instanzen.
    """
    
    _instance: Optional["Container"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Repositories
        self._user_repo: Optional[UserRepository] = None
        self._auth_token_repo: Optional[AuthTokenRepository] = None
        self._challenge_repo: Optional[ChallengeRepository] = None
        self._member_repo: Optional[ChallengeMemberRepository] = None
        self._stats_repo: Optional[ChallengeStatsRepository] = None
        self._confirmation_repo: Optional[ConfirmationRepository] = None
        self._chat_repo: Optional[ChallengeChatRepository] = None
        self._friendship_repo: Optional[FriendshipRepository] = None
        self._notification_repo: Optional[NotificationRepository] = None
        self._report_repo: Optional[ReportRepository] = None
        
        # Services
        self._auth_service: Optional[AuthService] = None
        self._user_service: Optional[UserService] = None
        self._challenge_service: Optional[ChallengeService] = None
        self._friend_service: Optional[FriendService] = None
        self._notification_service: Optional[NotificationService] = None
        
        self._initialized = True
    
    # Repository Getters (Lazy Loading)
    
    @property
    def user_repo(self) -> UserRepository:
        if self._user_repo is None:
            self._user_repo = UserRepository()
        return self._user_repo
    
    @property
    def auth_token_repo(self) -> AuthTokenRepository:
        if self._auth_token_repo is None:
            self._auth_token_repo = AuthTokenRepository()
        return self._auth_token_repo
    
    @property
    def challenge_repo(self) -> ChallengeRepository:
        if self._challenge_repo is None:
            self._challenge_repo = ChallengeRepository()
        return self._challenge_repo
    
    @property
    def member_repo(self) -> ChallengeMemberRepository:
        if self._member_repo is None:
            self._member_repo = ChallengeMemberRepository()
        return self._member_repo
    
    @property
    def stats_repo(self) -> ChallengeStatsRepository:
        if self._stats_repo is None:
            self._stats_repo = ChallengeStatsRepository()
        return self._stats_repo
    
    @property
    def confirmation_repo(self) -> ConfirmationRepository:
        if self._confirmation_repo is None:
            self._confirmation_repo = ConfirmationRepository()
        return self._confirmation_repo
    
    @property
    def chat_repo(self) -> ChallengeChatRepository:
        if self._chat_repo is None:
            self._chat_repo = ChallengeChatRepository()
        return self._chat_repo
    
    @property
    def friendship_repo(self) -> FriendshipRepository:
        if self._friendship_repo is None:
            self._friendship_repo = FriendshipRepository()
        return self._friendship_repo
    
    @property
    def notification_repo(self) -> NotificationRepository:
        if self._notification_repo is None:
            self._notification_repo = NotificationRepository()
        return self._notification_repo
    
    @property
    def report_repo(self) -> ReportRepository:
        if self._report_repo is None:
            self._report_repo = ReportRepository()
        return self._report_repo
    
    # Service Getters (Lazy Loading mit Dependency Injection)
    
    @property
    def auth_service(self) -> AuthService:
        if self._auth_service is None:
            self._auth_service = AuthService(
                user_repo=self.user_repo,
                token_repo=self.auth_token_repo
            )
        return self._auth_service
    
    @property
    def user_service(self) -> UserService:
        if self._user_service is None:
            self._user_service = UserService(user_repo=self.user_repo)
        return self._user_service
    
    @property
    def challenge_service(self) -> ChallengeService:
        if self._challenge_service is None:
            self._challenge_service = ChallengeService(
                challenge_repo=self.challenge_repo,
                member_repo=self.member_repo,
                stats_repo=self.stats_repo,
                confirmation_repo=self.confirmation_repo,
                chat_repo=self.chat_repo,
                user_repo=self.user_repo
            )
        return self._challenge_service
    
    @property
    def friend_service(self) -> FriendService:
        if self._friend_service is None:
            self._friend_service = FriendService(
                friendship_repo=self.friendship_repo,
                user_repo=self.user_repo
            )
        return self._friend_service
    
    @property
    def notification_service(self) -> NotificationService:
        if self._notification_service is None:
            self._notification_service = NotificationService(
                notification_repo=self.notification_repo
            )
        return self._notification_service
    
    def reset(self):
        """Reset all services and repositories (hauptsächlich für Tests)."""
        self._user_repo = None
        self._auth_token_repo = None
        self._challenge_repo = None
        self._member_repo = None
        self._stats_repo = None
        self._confirmation_repo = None
        self._chat_repo = None
        self._friendship_repo = None
        self._notification_repo = None
        self._report_repo = None
        
        self._auth_service = None
        self._user_service = None
        self._challenge_service = None
        self._friend_service = None
        self._notification_service = None


@lru_cache
def get_container() -> Container:
    """
    Gibt globale Container-Instanz zurück (Singleton).
    
    Returns:
        Container-Instanz
    """
    return Container()
