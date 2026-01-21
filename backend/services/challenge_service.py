"""
Challenge Service - Business Logic für Challenge-Operationen.
"""
from datetime import datetime
from typing import Optional

from backend.core.exceptions import (
    ResourceNotFoundError,
    BusinessLogicError,
    InsufficientPermissionsError,
    ValidationError,
)
from backend.core.logging import get_logger
from backend.domain.models import Challenge, ChallengeStatus, ChallengeMember
from backend.repositories import (
    ChallengeRepository,
    ChallengeMemberRepository,
    ChallengeStatsRepository,
    ConfirmationRepository,
    ChallengeChatRepository,
    UserRepository,
)
from backend.schemas import (
    CreateChallengeRequest,
    ChallengeResponse,
    ChallengeDetailResponse,
    ChallengeMemberResponse,
    ChallengeStatsResponse,
    ConfirmChallengeRequest,
    ConfirmationResponse,
    ChatMessageRequest,
    ChatMessageResponse,
    UserResponse,
)

logger = get_logger(__name__)


class ChallengeService:
    """Service für Challenge-Operationen."""
    
    def __init__(
        self,
        challenge_repo: Optional[ChallengeRepository] = None,
        member_repo: Optional[ChallengeMemberRepository] = None,
        stats_repo: Optional[ChallengeStatsRepository] = None,
        confirmation_repo: Optional[ConfirmationRepository] = None,
        chat_repo: Optional[ChallengeChatRepository] = None,
        user_repo: Optional[UserRepository] = None,
    ):
        self.challenge_repo = challenge_repo or ChallengeRepository()
        self.member_repo = member_repo or ChallengeMemberRepository()
        self.stats_repo = stats_repo or ChallengeStatsRepository()
        self.confirmation_repo = confirmation_repo or ConfirmationRepository()
        self.chat_repo = chat_repo or ChallengeChatRepository()
        self.user_repo = user_repo or UserRepository()
    
    def create_challenge(self, user_id: int, request: CreateChallengeRequest) -> ChallengeDetailResponse:
        """
        Erstellt eine neue Challenge.
        
        Args:
            user_id: Creator User-ID
            request: Challenge-Daten
        
        Returns:
            Challenge Detail Response
        """
        logger.info(f"Creating challenge for user {user_id}: {request.name}")
        
        # Validiere Weekdays
        weekdays = self._normalize_weekdays(request.faelligeWochentage)
        
        # Erstelle Challenge
        now = int(datetime.utcnow().timestamp() * 1000)
        start_at = request.startAt or int(datetime.utcnow().timestamp())
        
        challenge = self.challenge_repo.create({
            "creator_id": user_id,
            "title": request.name,
            "description": request.beschreibung,
            "challenge_type": "group" if request.friendsToAdd else "personal",
            "status": ChallengeStatus.ACTIVE.value,
            "start_at": start_at * 1000 if start_at < 10**12 else start_at,
            "duration_days": request.dauerTage,
            "allowed_fails": request.erlaubteFailsTage,
            "due_weekdays": ",".join(map(str, weekdays)),
            "created_at": now,
            "updated_at": now
        })
        
        # Creator als Mitglied hinzufügen
        member = self.member_repo.create({
            "challenge_id": challenge.id,
            "user_id": user_id,
            "role": "creator",
            "joined_at": now
        })
        
        # Stats initialisieren
        self.stats_repo.create({
            "challenge_id": challenge.id,
            "user_id": user_id,
            "conf_count": 0,
            "fail_count": 0,
            "streak": 0,
            "neg_streak": 0,
            "best_streak": 0,
            "blocked": False,
            "today_done": False,
            "today_pending": True,
            "created_at": now,
            "updated_at": now
        })
        
        # Initial Chat-Message
        self.chat_repo.create({
            "challenge_id": challenge.id,
            "user_id": user_id,
            "message": "Challenge erstellt 🎯",
            "created_at": now
        })
        
        logger.info(f"Challenge created: id={challenge.id}")
        
        return self._build_challenge_detail_response(challenge, user_id)
    
    def get_challenge(self, challenge_id: int, user_id: Optional[int] = None) -> ChallengeDetailResponse:
        """
        Gibt Challenge-Details zurück.
        
        Args:
            challenge_id: Challenge-ID
            user_id: Optional User-ID für User-spezifische Daten
        
        Returns:
            Challenge Detail Response
        
        Raises:
            ResourceNotFoundError: Challenge nicht gefunden
        """
        challenge = self.challenge_repo.find_by_id(challenge_id)
        
        if not challenge:
            raise ResourceNotFoundError("Challenge", challenge_id)
        
        return self._build_challenge_detail_response(challenge, user_id)
    
    def list_user_challenges(self, user_id: int) -> list[ChallengeResponse]:
        """
        Listet alle Challenges eines Users auf.
        
        Args:
            user_id: User-ID
        
        Returns:
            Liste von Challenge Responses
        """
        challenges = self.challenge_repo.find_active_challenges(user_id)
        
        return [ChallengeResponse.model_validate(c) for c in challenges]
    
    def confirm_challenge(
        self,
        challenge_id: int,
        user_id: int,
        request: ConfirmChallengeRequest
    ) -> ConfirmationResponse:
        """
        Bestätigt Challenge-Aktivität für einen Tag.
        
        Args:
            challenge_id: Challenge-ID
            user_id: User-ID
            request: Confirmation-Daten
        
        Returns:
            Confirmation Response
        
        Raises:
            ResourceNotFoundError: Challenge nicht gefunden
            BusinessLogicError: User ist kein Mitglied
        """
        # Prüfe ob Challenge existiert
        challenge = self.challenge_repo.find_by_id(challenge_id)
        if not challenge:
            raise ResourceNotFoundError("Challenge", challenge_id)
        
        # Prüfe ob User Mitglied ist
        if not self.member_repo.is_member(challenge_id, user_id):
            raise BusinessLogicError("Du bist kein Mitglied dieser Challenge")
        
        # Erstelle Confirmation
        now = int(datetime.utcnow().timestamp() * 1000)
        
        confirmation = self.confirmation_repo.create({
            "challenge_id": challenge_id,
            "user_id": user_id,
            "image_url": request.imageUrl,
            "caption": request.caption,
            "visibility": request.visibility or "freunde",
            "reactions_count": 0,
            "comments_count": 0,
            "created_at": now
        })
        
        # Update Stats
        stats = self.stats_repo.get_stats(challenge_id, user_id)
        if stats:
            self.stats_repo.update(stats.id, {
                "conf_count": stats.conf_count + 1,
                "streak": stats.streak + 1,
                "best_streak": max(stats.best_streak, stats.streak + 1),
                "today_done": True,
                "today_pending": False,
                "updated_at": now
            })
        
        logger.info(f"Challenge {challenge_id} confirmed by user {user_id}")
        
        # Lade User
        user = self.user_repo.find_by_id(user_id)
        
        return ConfirmationResponse(
            **confirmation.__dict__,
            user=UserResponse.model_validate(user) if user else None
        )
    
    def get_challenge_chat(
        self,
        challenge_id: int,
        user_id: int,
        limit: int = 50
    ) -> list[ChatMessageResponse]:
        """
        Gibt Challenge-Chat zurück.
        
        Args:
            challenge_id: Challenge-ID
            user_id: User-ID (für Permission-Check)
            limit: Max. Anzahl Nachrichten
        
        Returns:
            Liste von Chat-Messages
        
        Raises:
            ResourceNotFoundError: Challenge nicht gefunden
            InsufficientPermissionsError: User ist kein Mitglied
        """
        # Prüfe Berechtigung
        if not self.member_repo.is_member(challenge_id, user_id):
            raise InsufficientPermissionsError("Du bist kein Mitglied dieser Challenge")
        
        messages = self.chat_repo.find_by_challenge(challenge_id, limit=limit)
        
        # Lade User-Daten
        user_ids = list(set(m.user_id for m in messages))
        users = {u.id: u for u in [self.user_repo.find_by_id(uid) for uid in user_ids] if u}
        
        return [
            ChatMessageResponse(
                **msg.__dict__,
                user=UserResponse.model_validate(users[msg.user_id]) if msg.user_id in users else None
            )
            for msg in messages
        ]
    
    def post_chat_message(
        self,
        challenge_id: int,
        user_id: int,
        request: ChatMessageRequest
    ) -> ChatMessageResponse:
        """
        Postet Chat-Nachricht in Challenge.
        
        Args:
            challenge_id: Challenge-ID
            user_id: User-ID
            request: Chat-Message-Daten
        
        Returns:
            Chat Message Response
        
        Raises:
            ResourceNotFoundError: Challenge nicht gefunden
            InsufficientPermissionsError: User ist kein Mitglied
        """
        # Prüfe Berechtigung
        if not self.member_repo.is_member(challenge_id, user_id):
            raise InsufficientPermissionsError("Du bist kein Mitglied dieser Challenge")
        
        # Erstelle Message
        now = int(datetime.utcnow().timestamp() * 1000)
        
        message = self.chat_repo.create({
            "challenge_id": challenge_id,
            "user_id": user_id,
            "message": request.text,
            "created_at": now
        })
        
        logger.info(f"Chat message posted in challenge {challenge_id} by user {user_id}")
        
        # Lade User
        user = self.user_repo.find_by_id(user_id)
        
        return ChatMessageResponse(
            **message.__dict__,
            user=UserResponse.model_validate(user) if user else None
        )
    
    def _build_challenge_detail_response(
        self,
        challenge: Challenge,
        user_id: Optional[int] = None
    ) -> ChallengeDetailResponse:
        """Erstellt Challenge Detail Response mit Mitgliedern und Stats."""
        # Lade Mitglieder
        members = self.member_repo.find_by_challenge(challenge.id, active_only=True)
        
        # Lade User-Daten für Mitglieder
        user_ids = [m.user_id for m in members]
        users = {u.id: u for u in [self.user_repo.find_by_id(uid) for uid in user_ids] if u}
        
        member_responses = [
            ChallengeMemberResponse(
                **m.__dict__,
                user=UserResponse.model_validate(users[m.user_id]) if m.user_id in users else None
            )
            for m in members
        ]
        
        # Lade Stats für aktuellen User (falls vorhanden)
        stats_response = None
        if user_id:
            stats = self.stats_repo.get_stats(challenge.id, user_id)
            if stats:
                stats_response = ChallengeStatsResponse.model_validate(stats)
        
        return ChallengeDetailResponse(
            **challenge.__dict__,
            members=member_responses,
            stats=stats_response
        )
    
    @staticmethod
    def _normalize_weekdays(raw_list: list[int]) -> list[int]:
        """Normalisiert Wochentage (0=Mo, 6=So)."""
        return sorted(set(d for d in raw_list if 0 <= d <= 6))
