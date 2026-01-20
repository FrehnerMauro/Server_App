"""
Friend Repository - Datenbankzugriff für Freundschaften.
"""
from datetime import datetime
from typing import Optional

from psycopg2.extras import RealDictRow

from backend.core.database import get_db_cursor
from backend.core.exceptions import DatabaseError
from backend.domain.models import Friendship, FriendshipStatus
from backend.repositories.base import BaseRepository


class FriendshipRepository(BaseRepository[Friendship]):
    """Repository für Freundschaften."""
    
    def __init__(self):
        super().__init__("user_friends", Friendship)
    
    def _row_to_model(self, row: RealDictRow) -> Friendship:
        """Konvertiert DB-Row zu Friendship Domain Model."""
        return Friendship(
            id=row["id"],
            user_id=row["user_id"],
            friend_id=row["friend_id"],
            status=FriendshipStatus(row.get("status", "pending")),
            message=row.get("message"),
            created_at=self._timestamp_to_datetime(row["created_at"]),
            updated_at=self._timestamp_to_datetime(row["updated_at"])
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Timestamp zu datetime."""
        if timestamp > 10**12:
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def find_friends(self, user_id: int, status: Optional[FriendshipStatus] = None) -> list[Friendship]:
        """
        Gibt Freunde eines Users zurück.
        
        Args:
            user_id: User-ID
            status: Optional Filter nach Status
        
        Returns:
            Liste von Friendships
        """
        if status:
            where = "(user_id = %s OR friend_id = %s) AND status = %s"
            params = (user_id, user_id, status.value)
        else:
            where = "(user_id = %s OR friend_id = %s)"
            params = (user_id, user_id)
        
        return self.find_where(where, params, order_by="created_at DESC")
    
    def find_pending_requests(self, user_id: int, incoming: bool = True) -> list[Friendship]:
        """
        Gibt ausstehende Freundschaftsanfragen zurück.
        
        Args:
            user_id: User-ID
            incoming: True für eingehende, False für ausgehende Anfragen
        
        Returns:
            Liste von Friendships
        """
        if incoming:
            where = "friend_id = %s AND status = 'pending'"
        else:
            where = "user_id = %s AND status = 'pending'"
        
        return self.find_where(where, (user_id,), order_by="created_at DESC")
    
    def get_friendship(self, user_id: int, friend_id: int) -> Optional[Friendship]:
        """
        Gibt Freundschaft zwischen zwei Users zurück.
        
        Args:
            user_id: User-ID
            friend_id: Friend-ID
        
        Returns:
            Friendship oder None
        """
        where = "(user_id = %s AND friend_id = %s) OR (user_id = %s AND friend_id = %s)"
        params = (user_id, friend_id, friend_id, user_id)
        
        return self.find_one_where(where, params)
    
    def are_friends(self, user_id: int, friend_id: int) -> bool:
        """
        Prüft ob zwei Users befreundet sind.
        
        Args:
            user_id: User-ID
            friend_id: Friend-ID
        
        Returns:
            True wenn befreundet
        """
        friendship = self.get_friendship(user_id, friend_id)
        return friendship is not None and friendship.status == FriendshipStatus.ACCEPTED
    
    def friendship_exists(self, user_id: int, friend_id: int) -> bool:
        """
        Prüft ob Freundschaft (in irgendeinem Status) existiert.
        
        Args:
            user_id: User-ID
            friend_id: Friend-ID
        
        Returns:
            True wenn existiert
        """
        return self.get_friendship(user_id, friend_id) is not None
    
    def count_friends(self, user_id: int) -> int:
        """
        Zählt Freunde eines Users.
        
        Args:
            user_id: User-ID
        
        Returns:
            Anzahl Freunde
        """
        where = "(user_id = %s OR friend_id = %s) AND status = 'accepted'"
        return self.count(where, (user_id, user_id))
