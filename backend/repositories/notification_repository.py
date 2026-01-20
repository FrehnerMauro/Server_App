"""
Notification & Report Repositories.
"""
from datetime import datetime
from typing import Optional

from psycopg2.extras import RealDictRow

from backend.domain.models import Notification, NotificationType, Report
from backend.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    """Repository für Benachrichtigungen."""
    
    def __init__(self):
        super().__init__("notifications", Notification)
    
    def _row_to_model(self, row: RealDictRow) -> Notification:
        """Konvertiert DB-Row zu Notification Domain Model."""
        import json
        
        return Notification(
            id=row["id"],
            user_id=row["user_id"],
            notification_type=NotificationType(row["notification_type"]),
            title=row["title"],
            message=row["message"],
            data=json.loads(row.get("data", "{}")) if isinstance(row.get("data"), str) else row.get("data", {}),
            is_read=bool(row.get("is_read", False)),
            read_at=self._timestamp_to_datetime(row["read_at"]) if row.get("read_at") else None,
            created_at=self._timestamp_to_datetime(row["created_at"])
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Timestamp zu datetime."""
        if timestamp > 10**12:
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def find_by_user(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: Optional[int] = None
    ) -> list[Notification]:
        """
        Gibt Benachrichtigungen eines Users zurück.
        
        Args:
            user_id: User-ID
            unread_only: Nur ungelesene Benachrichtigungen
            limit: Max. Anzahl
        
        Returns:
            Liste von Notifications
        """
        where = "user_id = %s"
        if unread_only:
            where += " AND is_read = FALSE"
        
        return self.find_where(
            where,
            (user_id,),
            limit=limit,
            order_by="created_at DESC"
        )
    
    def count_unread(self, user_id: int) -> int:
        """
        Zählt ungelesene Benachrichtigungen eines Users.
        
        Args:
            user_id: User-ID
        
        Returns:
            Anzahl ungelesener Benachrichtigungen
        """
        return self.count("user_id = %s AND is_read = FALSE", (user_id,))
    
    def mark_as_read(self, notification_id: int) -> bool:
        """
        Markiert Benachrichtigung als gelesen.
        
        Args:
            notification_id: Notification-ID
        
        Returns:
            True wenn erfolgreich
        """
        now = int(datetime.utcnow().timestamp() * 1000)
        updated = self.update(notification_id, {
            "is_read": True,
            "read_at": now
        })
        return updated is not None
    
    def mark_all_as_read(self, user_id: int) -> int:
        """
        Markiert alle Benachrichtigungen eines Users als gelesen.
        
        Args:
            user_id: User-ID
        
        Returns:
            Anzahl aktualisierter Benachrichtigungen
        """
        from backend.core.database import get_db_cursor
        
        now = int(datetime.utcnow().timestamp() * 1000)
        sql = """
            UPDATE notifications 
            SET is_read = TRUE, read_at = %s, updated_at = %s
            WHERE user_id = %s AND is_read = FALSE
        """
        
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(sql, (now, now, user_id))
                return cursor.rowcount
        except Exception as e:
            from backend.core.exceptions import DatabaseError
            raise DatabaseError(f"Error marking notifications as read: {str(e)}")
    
    def delete_old_notifications(self, days: int = 30) -> int:
        """
        Löscht alte Benachrichtigungen.
        
        Args:
            days: Anzahl Tage
        
        Returns:
            Anzahl gelöschter Benachrichtigungen
        """
        from backend.core.database import get_db_cursor
        
        cutoff = int((datetime.utcnow().timestamp() - (days * 86400)) * 1000)
        sql = f"DELETE FROM {self.table_name} WHERE created_at < %s"
        
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(sql, (cutoff,))
                return cursor.rowcount
        except Exception as e:
            from backend.core.exceptions import DatabaseError
            raise DatabaseError(f"Error deleting old notifications: {str(e)}")


class ReportRepository(BaseRepository[Report]):
    """Repository für Meldungen."""
    
    def __init__(self):
        super().__init__("reports", Report)
    
    def _row_to_model(self, row: RealDictRow) -> Report:
        """Konvertiert DB-Row zu Report Domain Model."""
        return Report(
            id=row["id"],
            reporter_id=row["reporter_id"],
            reported_user_id=row.get("reported_user_id"),
            reported_content_id=row.get("reported_content_id"),
            content_type=row.get("content_type"),
            reason=row["reason"],
            description=row.get("description"),
            status=row.get("status", "pending"),
            created_at=self._timestamp_to_datetime(row["created_at"]),
            resolved_at=self._timestamp_to_datetime(row["resolved_at"]) if row.get("resolved_at") else None
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Timestamp zu datetime."""
        if timestamp > 10**12:
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def find_pending_reports(self, limit: Optional[int] = None) -> list[Report]:
        """
        Gibt ausstehende Meldungen zurück.
        
        Args:
            limit: Max. Anzahl
        
        Returns:
            Liste von Reports
        """
        return self.find_where(
            "status = 'pending'",
            (),
            limit=limit,
            order_by="created_at DESC"
        )
    
    def find_by_reporter(self, reporter_id: int) -> list[Report]:
        """
        Gibt Meldungen eines Reporters zurück.
        
        Args:
            reporter_id: Reporter User-ID
        
        Returns:
            Liste von Reports
        """
        return self.find_where(
            "reporter_id = %s",
            (reporter_id,),
            order_by="created_at DESC"
        )
