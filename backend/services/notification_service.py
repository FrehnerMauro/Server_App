"""
Notification Service - Business Logic für Benachrichtigungen.
"""
from datetime import datetime
from typing import Optional

from backend.core.exceptions import ResourceNotFoundError
from backend.core.logging import get_logger
from backend.domain.models import NotificationType
from backend.repositories import NotificationRepository
from backend.schemas import NotificationResponse

logger = get_logger(__name__)


class NotificationService:
    """Service für Benachrichtigungen."""
    
    def __init__(self, notification_repo: Optional[NotificationRepository] = None):
        self.notification_repo = notification_repo or NotificationRepository()
    
    def create_notification(
        self,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        data: Optional[dict] = None
    ) -> NotificationResponse:
        """
        Erstellt eine Benachrichtigung.
        
        Args:
            user_id: Empfänger User-ID
            notification_type: Art der Benachrichtigung
            title: Titel
            message: Nachricht
            data: Zusätzliche Daten (JSON)
        
        Returns:
            Notification Response
        """
        import json
        
        now = int(datetime.utcnow().timestamp() * 1000)
        
        notification = self.notification_repo.create({
            "user_id": user_id,
            "notification_type": notification_type.value,
            "title": title,
            "message": message,
            "data": json.dumps(data or {}),
            "is_read": False,
            "created_at": now
        })
        
        logger.info(
            f"Notification created for user {user_id}: "
            f"type={notification_type.value}, title={title}"
        )
        
        return NotificationResponse.model_validate(notification)
    
    def get_user_notifications(
        self,
        user_id: int,
        unread_only: bool = False,
        limit: int = 50
    ) -> list[NotificationResponse]:
        """
        Gibt Benachrichtigungen eines Users zurück.
        
        Args:
            user_id: User-ID
            unread_only: Nur ungelesene Benachrichtigungen
            limit: Max. Anzahl
        
        Returns:
            Liste von Notifications
        """
        notifications = self.notification_repo.find_by_user(
            user_id,
            unread_only=unread_only,
            limit=limit
        )
        
        return [NotificationResponse.model_validate(n) for n in notifications]
    
    def get_unread_count(self, user_id: int) -> int:
        """
        Gibt Anzahl ungelesener Benachrichtigungen zurück.
        
        Args:
            user_id: User-ID
        
        Returns:
            Anzahl ungelesener Benachrichtigungen
        """
        return self.notification_repo.count_unread(user_id)
    
    def mark_as_read(self, notification_id: int, user_id: int) -> NotificationResponse:
        """
        Markiert Benachrichtigung als gelesen.
        
        Args:
            notification_id: Notification-ID
            user_id: User-ID (für Permission-Check)
        
        Returns:
            Aktualisierte Notification
        
        Raises:
            ResourceNotFoundError: Notification nicht gefunden
        """
        notification = self.notification_repo.find_by_id(notification_id)
        
        if not notification:
            raise ResourceNotFoundError("Notification", notification_id)
        
        # Prüfe Berechtigung
        if notification.user_id != user_id:
            raise ResourceNotFoundError("Notification", notification_id)
        
        # Markiere als gelesen
        success = self.notification_repo.mark_as_read(notification_id)
        
        if not success:
            raise ResourceNotFoundError("Notification", notification_id)
        
        # Lade aktualisierte Notification
        updated = self.notification_repo.find_by_id(notification_id)
        
        return NotificationResponse.model_validate(updated)
    
    def mark_all_as_read(self, user_id: int) -> int:
        """
        Markiert alle Benachrichtigungen eines Users als gelesen.
        
        Args:
            user_id: User-ID
        
        Returns:
            Anzahl markierter Benachrichtigungen
        """
        count = self.notification_repo.mark_all_as_read(user_id)
        
        logger.info(f"Marked {count} notifications as read for user {user_id}")
        
        return count
    
    def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """
        Löscht eine Benachrichtigung.
        
        Args:
            notification_id: Notification-ID
            user_id: User-ID (für Permission-Check)
        
        Returns:
            True wenn erfolgreich
        
        Raises:
            ResourceNotFoundError: Notification nicht gefunden
        """
        notification = self.notification_repo.find_by_id(notification_id)
        
        if not notification:
            raise ResourceNotFoundError("Notification", notification_id)
        
        # Prüfe Berechtigung
        if notification.user_id != user_id:
            raise ResourceNotFoundError("Notification", notification_id)
        
        deleted = self.notification_repo.delete(notification_id)
        
        logger.info(f"Notification {notification_id} deleted by user {user_id}")
        
        return deleted
    
    # Helper methods für spezifische Notification-Types
    
    def notify_friend_request(
        self,
        from_user_id: int,
        to_user_id: int,
        from_user_name: str
    ) -> NotificationResponse:
        """Erstellt Benachrichtigung für Freundschaftsanfrage."""
        return self.create_notification(
            user_id=to_user_id,
            notification_type=NotificationType.FRIEND_REQUEST,
            title="Neue Freundschaftsanfrage",
            message=f"{from_user_name} möchte dein Freund sein",
            data={"from_user_id": from_user_id}
        )
    
    def notify_friend_accepted(
        self,
        from_user_id: int,
        to_user_id: int,
        acceptor_name: str
    ) -> NotificationResponse:
        """Erstellt Benachrichtigung für akzeptierte Freundschaftsanfrage."""
        return self.create_notification(
            user_id=to_user_id,
            notification_type=NotificationType.FRIEND_ACCEPTED,
            title="Freundschaftsanfrage akzeptiert",
            message=f"{acceptor_name} hat deine Freundschaftsanfrage akzeptiert",
            data={"friend_id": from_user_id}
        )
    
    def notify_challenge_invite(
        self,
        challenge_id: int,
        from_user_id: int,
        to_user_id: int,
        challenge_title: str,
        from_user_name: str
    ) -> NotificationResponse:
        """Erstellt Benachrichtigung für Challenge-Einladung."""
        return self.create_notification(
            user_id=to_user_id,
            notification_type=NotificationType.CHALLENGE_INVITE,
            title="Challenge-Einladung",
            message=f"{from_user_name} hat dich zu '{challenge_title}' eingeladen",
            data={"challenge_id": challenge_id, "from_user_id": from_user_id}
        )
