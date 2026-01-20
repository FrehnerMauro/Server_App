"""
Friend Service - Business Logic für Freundschaften.
"""
from datetime import datetime
from typing import Optional

from backend.core.exceptions import (
    ResourceNotFoundError,
    ResourceConflictError,
    BusinessLogicError,
)
from backend.core.logging import get_logger
from backend.domain.models import FriendshipStatus
from backend.repositories import FriendshipRepository, UserRepository
from backend.schemas import (
    FriendRequestRequest,
    FriendshipResponse,
    UserResponse,
)

logger = get_logger(__name__)


class FriendService:
    """Service für Freundschafts-Operationen."""
    
    def __init__(
        self,
        friendship_repo: Optional[FriendshipRepository] = None,
        user_repo: Optional[UserRepository] = None,
    ):
        self.friendship_repo = friendship_repo or FriendshipRepository()
        self.user_repo = user_repo or UserRepository()
    
    def send_friend_request(
        self,
        from_user_id: int,
        request: FriendRequestRequest
    ) -> FriendshipResponse:
        """
        Sendet Freundschaftsanfrage.
        
        Args:
            from_user_id: Sender User-ID
            request: Friend Request Daten
        
        Returns:
            Friendship Response
        
        Raises:
            ResourceNotFoundError: User nicht gefunden
            BusinessLogicError: Kann sich nicht selbst anfragen
            ResourceConflictError: Freundschaft existiert bereits
        """
        to_user_id = request.toUserId
        
        # Prüfe ob User existiert
        if not self.user_repo.exists(to_user_id):
            raise ResourceNotFoundError("User", to_user_id)
        
        # Prüfe ob nicht sich selbst
        if from_user_id == to_user_id:
            raise BusinessLogicError("Du kannst dich nicht selbst als Freund hinzufügen")
        
        # Prüfe ob Freundschaft bereits existiert
        if self.friendship_repo.friendship_exists(from_user_id, to_user_id):
            raise ResourceConflictError("Freundschaftsanfrage existiert bereits")
        
        # Erstelle Friendship
        now = int(datetime.utcnow().timestamp() * 1000)
        
        friendship = self.friendship_repo.create({
            "user_id": from_user_id,
            "friend_id": to_user_id,
            "status": FriendshipStatus.PENDING.value,
            "message": request.message,
            "created_at": now,
            "updated_at": now
        })
        
        logger.info(f"Friend request sent from {from_user_id} to {to_user_id}")
        
        # Lade Friend-User
        friend = self.user_repo.find_by_id(to_user_id)
        
        return FriendshipResponse(
            **friendship.__dict__,
            friend=UserResponse.model_validate(friend) if friend else None
        )
    
    def accept_friend_request(self, user_id: int, friendship_id: int) -> FriendshipResponse:
        """
        Akzeptiert Freundschaftsanfrage.
        
        Args:
            user_id: User-ID der akzeptiert
            friendship_id: Friendship-ID
        
        Returns:
            Aktualisierte Friendship
        
        Raises:
            ResourceNotFoundError: Friendship nicht gefunden
            BusinessLogicError: Keine Berechtigung
        """
        friendship = self.friendship_repo.find_by_id(friendship_id)
        
        if not friendship:
            raise ResourceNotFoundError("Friendship", friendship_id)
        
        # Prüfe Berechtigung (muss Empfänger sein)
        if friendship.friend_id != user_id:
            raise BusinessLogicError("Du kannst diese Anfrage nicht akzeptieren")
        
        # Update Status
        now = int(datetime.utcnow().timestamp() * 1000)
        
        updated_friendship = self.friendship_repo.update(friendship_id, {
            "status": FriendshipStatus.ACCEPTED.value,
            "updated_at": now
        })
        
        if not updated_friendship:
            raise ResourceNotFoundError("Friendship", friendship_id)
        
        logger.info(f"Friend request {friendship_id} accepted by user {user_id}")
        
        # Lade Friend-User
        friend = self.user_repo.find_by_id(friendship.user_id)
        
        return FriendshipResponse(
            **updated_friendship.__dict__,
            friend=UserResponse.model_validate(friend) if friend else None
        )
    
    def decline_friend_request(self, user_id: int, friendship_id: int) -> bool:
        """
        Lehnt Freundschaftsanfrage ab.
        
        Args:
            user_id: User-ID der ablehnt
            friendship_id: Friendship-ID
        
        Returns:
            True wenn erfolgreich
        
        Raises:
            ResourceNotFoundError: Friendship nicht gefunden
            BusinessLogicError: Keine Berechtigung
        """
        friendship = self.friendship_repo.find_by_id(friendship_id)
        
        if not friendship:
            raise ResourceNotFoundError("Friendship", friendship_id)
        
        # Prüfe Berechtigung
        if friendship.friend_id != user_id:
            raise BusinessLogicError("Du kannst diese Anfrage nicht ablehnen")
        
        # Lösche Friendship
        deleted = self.friendship_repo.delete(friendship_id)
        
        logger.info(f"Friend request {friendship_id} declined by user {user_id}")
        
        return deleted
    
    def remove_friend(self, user_id: int, friend_id: int) -> bool:
        """
        Entfernt Freund.
        
        Args:
            user_id: User-ID
            friend_id: Friend-ID
        
        Returns:
            True wenn erfolgreich
        
        Raises:
            ResourceNotFoundError: Friendship nicht gefunden
        """
        friendship = self.friendship_repo.get_friendship(user_id, friend_id)
        
        if not friendship:
            raise ResourceNotFoundError("Friendship", f"{user_id}-{friend_id}")
        
        deleted = self.friendship_repo.delete(friendship.id)
        
        logger.info(f"Friendship removed: {user_id} <-> {friend_id}")
        
        return deleted
    
    def get_friends(self, user_id: int) -> list[FriendshipResponse]:
        """
        Gibt alle Freunde eines Users zurück.
        
        Args:
            user_id: User-ID
        
        Returns:
            Liste von Friendships
        """
        friendships = self.friendship_repo.find_friends(
            user_id,
            status=FriendshipStatus.ACCEPTED
        )
        
        # Lade User-Daten
        friend_ids = []
        for f in friendships:
            friend_id = f.friend_id if f.user_id == user_id else f.user_id
            friend_ids.append(friend_id)
        
        users = {u.id: u for u in [self.user_repo.find_by_id(fid) for fid in friend_ids] if u}
        
        return [
            FriendshipResponse(
                **f.__dict__,
                friend=UserResponse.model_validate(
                    users[f.friend_id if f.user_id == user_id else f.user_id]
                ) if (f.friend_id if f.user_id == user_id else f.user_id) in users else None
            )
            for f in friendships
        ]
    
    def get_pending_requests(self, user_id: int, incoming: bool = True) -> list[FriendshipResponse]:
        """
        Gibt ausstehende Freundschaftsanfragen zurück.
        
        Args:
            user_id: User-ID
            incoming: True für eingehende, False für ausgehende
        
        Returns:
            Liste von Friendships
        """
        friendships = self.friendship_repo.find_pending_requests(user_id, incoming)
        
        # Lade User-Daten
        if incoming:
            user_ids = [f.user_id for f in friendships]
        else:
            user_ids = [f.friend_id for f in friendships]
        
        users = {u.id: u for u in [self.user_repo.find_by_id(uid) for uid in user_ids] if u}
        
        return [
            FriendshipResponse(
                **f.__dict__,
                friend=UserResponse.model_validate(
                    users[f.user_id if incoming else f.friend_id]
                ) if (f.user_id if incoming else f.friend_id) in users else None
            )
            for f in friendships
        ]
