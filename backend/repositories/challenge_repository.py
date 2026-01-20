"""
Challenge Repository - Datenbankzugriff für Challenge-Entitäten.
"""
from datetime import datetime
from typing import Optional

from psycopg2.extras import RealDictRow

from backend.core.database import get_db_cursor
from backend.core.exceptions import DatabaseError
from backend.domain.models import (
    Challenge,
    ChallengeStatus,
    ChallengeType,
    ChallengeMember,
    ChallengeStats,
    Confirmation,
    ConfirmationVisibility,
    ChallengeChat,
)
from backend.repositories.base import BaseRepository


class ChallengeRepository(BaseRepository[Challenge]):
    """Repository für Challenge-Operationen."""
    
    def __init__(self):
        super().__init__("challenges", Challenge)
    
    def _row_to_model(self, row: RealDictRow) -> Challenge:
        """Konvertiert DB-Row zu Challenge Domain Model."""
        # Parse weekdays
        weekdays_str = row.get("due_weekdays", "")
        weekdays = [int(d) for d in weekdays_str.split(",") if d.strip().isdigit()] if weekdays_str else []
        
        return Challenge(
            id=row["id"],
            creator_id=row["creator_id"],
            title=row["title"],
            description=row.get("description"),
            challenge_type=ChallengeType(row.get("challenge_type", "personal")),
            status=ChallengeStatus(row.get("status", "active")),
            start_at=self._timestamp_to_datetime(row["start_at"]),
            duration_days=row["duration_days"],
            allowed_fails=row.get("allowed_fails", 0),
            due_weekdays=weekdays,
            created_at=self._timestamp_to_datetime(row["created_at"]),
            updated_at=self._timestamp_to_datetime(row["updated_at"]) if row.get("updated_at") else None
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Timestamp zu datetime."""
        if timestamp > 10**12:
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def find_by_creator(self, creator_id: int) -> list[Challenge]:
        """Gibt alle Challenges eines Creators zurück."""
        return self.find_where(
            "creator_id = %s",
            (creator_id,),
            order_by="created_at DESC"
        )
    
    def find_active_challenges(self, user_id: Optional[int] = None) -> list[Challenge]:
        """Gibt aktive Challenges zurück."""
        now = int(datetime.utcnow().timestamp())
        
        if user_id:
            # Challenges bei denen User Mitglied ist
            sql = """
                SELECT c.* FROM challenges c
                JOIN challenge_members cm ON cm.challenge_id = c.id
                WHERE cm.user_id = %s
                AND c.status = 'active'
                AND c.start_at <= %s
                ORDER BY c.start_at DESC
            """
            params = (user_id, now * 1000)
        else:
            where = "status = 'active' AND start_at <= %s"
            params = (now * 1000,)
            return self.find_where(where, params, order_by="start_at DESC")
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Error finding active challenges: {str(e)}")


class ChallengeMemberRepository(BaseRepository[ChallengeMember]):
    """Repository für Challenge-Mitglieder."""
    
    def __init__(self):
        super().__init__("challenge_members", ChallengeMember)
    
    def _row_to_model(self, row: RealDictRow) -> ChallengeMember:
        """Konvertiert DB-Row zu ChallengeMember Domain Model."""
        return ChallengeMember(
            id=row["id"],
            challenge_id=row["challenge_id"],
            user_id=row["user_id"],
            role=row.get("role", "member"),
            joined_at=self._timestamp_to_datetime(row["joined_at"]),
            left_at=self._timestamp_to_datetime(row["left_at"]) if row.get("left_at") else None
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Timestamp zu datetime."""
        if timestamp > 10**12:
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def find_by_challenge(self, challenge_id: int, active_only: bool = True) -> list[ChallengeMember]:
        """Gibt alle Mitglieder einer Challenge zurück."""
        where = "challenge_id = %s"
        if active_only:
            where += " AND left_at IS NULL"
        
        return self.find_where(where, (challenge_id,), order_by="joined_at ASC")
    
    def find_by_user(self, user_id: int, active_only: bool = True) -> list[ChallengeMember]:
        """Gibt alle Challenge-Mitgliedschaften eines Users zurück."""
        where = "user_id = %s"
        if active_only:
            where += " AND left_at IS NULL"
        
        return self.find_where(where, (user_id,), order_by="joined_at DESC")
    
    def is_member(self, challenge_id: int, user_id: int) -> bool:
        """Prüft ob User Mitglied einer Challenge ist."""
        return self.count(
            "challenge_id = %s AND user_id = %s AND left_at IS NULL",
            (challenge_id, user_id)
        ) > 0
    
    def get_member(self, challenge_id: int, user_id: int) -> Optional[ChallengeMember]:
        """Gibt Mitgliedschaft zurück."""
        return self.find_one_where(
            "challenge_id = %s AND user_id = %s",
            (challenge_id, user_id)
        )


class ChallengeStatsRepository(BaseRepository[ChallengeStats]):
    """Repository für Challenge-Statistiken."""
    
    def __init__(self):
        super().__init__("challenge_stats", ChallengeStats)
    
    def _row_to_model(self, row: RealDictRow) -> ChallengeStats:
        """Konvertiert DB-Row zu ChallengeStats Domain Model."""
        return ChallengeStats(
            id=row["id"],
            challenge_id=row["challenge_id"],
            user_id=row["user_id"],
            conf_count=row.get("conf_count", 0),
            fail_count=row.get("fail_count", 0),
            streak=row.get("streak", 0),
            neg_streak=row.get("neg_streak", 0),
            best_streak=row.get("best_streak", 0),
            blocked=bool(row.get("blocked", False)),
            today_done=bool(row.get("today_done", False)),
            today_pending=bool(row.get("today_pending", True)),
            last_computed=self._timestamp_to_datetime(row["last_computed"]) if row.get("last_computed") else None,
            created_at=self._timestamp_to_datetime(row["created_at"]),
            updated_at=self._timestamp_to_datetime(row["updated_at"])
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Timestamp zu datetime."""
        if timestamp > 10**12:
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def get_stats(self, challenge_id: int, user_id: int) -> Optional[ChallengeStats]:
        """Gibt Statistiken für User in Challenge zurück."""
        return self.find_one_where(
            "challenge_id = %s AND user_id = %s",
            (challenge_id, user_id)
        )
    
    def find_by_challenge(self, challenge_id: int) -> list[ChallengeStats]:
        """Gibt alle Statistiken einer Challenge zurück."""
        return self.find_where(
            "challenge_id = %s",
            (challenge_id,),
            order_by="conf_count DESC"
        )


class ConfirmationRepository(BaseRepository[Confirmation]):
    """Repository für Challenge-Bestätigungen."""
    
    def __init__(self):
        super().__init__("challenge_confirmations", Confirmation)
    
    def _row_to_model(self, row: RealDictRow) -> Confirmation:
        """Konvertiert DB-Row zu Confirmation Domain Model."""
        return Confirmation(
            id=row["id"],
            challenge_id=row["challenge_id"],
            user_id=row["user_id"],
            image_url=row["image_url"],
            caption=row.get("caption"),
            visibility=ConfirmationVisibility(row.get("visibility", "freunde")),
            reactions_count=row.get("reactions_count", 0),
            comments_count=row.get("comments_count", 0),
            created_at=self._timestamp_to_datetime(row["created_at"])
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Timestamp zu datetime."""
        if timestamp > 10**12:
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def find_by_challenge(
        self,
        challenge_id: int,
        limit: Optional[int] = None
    ) -> list[Confirmation]:
        """Gibt Bestätigungen einer Challenge zurück."""
        return self.find_where(
            "challenge_id = %s",
            (challenge_id,),
            limit=limit,
            order_by="created_at DESC"
        )
    
    def find_by_user(
        self,
        user_id: int,
        limit: Optional[int] = None
    ) -> list[Confirmation]:
        """Gibt Bestätigungen eines Users zurück."""
        return self.find_where(
            "user_id = %s",
            (user_id,),
            limit=limit,
            order_by="created_at DESC"
        )


class ChallengeChatRepository(BaseRepository[ChallengeChat]):
    """Repository für Challenge-Chat."""
    
    def __init__(self):
        super().__init__("challenge_chat", ChallengeChat)
    
    def _row_to_model(self, row: RealDictRow) -> ChallengeChat:
        """Konvertiert DB-Row zu ChallengeChat Domain Model."""
        return ChallengeChat(
            id=row["id"],
            challenge_id=row["challenge_id"],
            user_id=row["user_id"],
            message=row["message"],
            image_url=row.get("image_url"),
            created_at=self._timestamp_to_datetime(row["created_at"])
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Timestamp zu datetime."""
        if timestamp > 10**12:
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def find_by_challenge(
        self,
        challenge_id: int,
        limit: Optional[int] = None
    ) -> list[ChallengeChat]:
        """Gibt Chat-Nachrichten einer Challenge zurück."""
        return self.find_where(
            "challenge_id = %s",
            (challenge_id,),
            limit=limit,
            order_by="created_at DESC"
        )
