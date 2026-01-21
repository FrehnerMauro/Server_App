"""
Notification API Routes - Notification Management Endpoints.
"""
from flask import Blueprint, request, jsonify, g

from backend.api.decorators import auth_required
from backend.core.container import get_container
from backend.core.logging import get_logger

logger = get_logger(__name__)

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@bp.get("")
@auth_required
def list_notifications():
    """
    Listet Benachrichtigungen des eingeloggten Users auf.
    
    Requires: Authentication
    
    Query Params:
        - unread_only: bool (optional, default: false)
        - limit: int (optional, default: 50)
    
    Returns:
        200: [NotificationResponse]
    """
    user_id = g.user_id
    unread_only = request.args.get("unread_only", "false").lower() == "true"
    limit = min(int(request.args.get("limit", 50)), 200)
    
    container = get_container()
    notification_service = container.notification_service
    
    notifications = notification_service.get_user_notifications(
        user_id,
        unread_only=unread_only,
        limit=limit
    )
    
    return jsonify([n.model_dump() for n in notifications]), 200


@bp.get("/unread-count")
@auth_required
def get_unread_count():
    """
    Gibt Anzahl ungelesener Benachrichtigungen zurück.
    
    Requires: Authentication
    
    Returns:
        200: {count: int}
    """
    user_id = g.user_id
    
    container = get_container()
    notification_service = container.notification_service
    
    count = notification_service.get_unread_count(user_id)
    
    return jsonify({"count": count}), 200


@bp.post("/<int:notification_id>/read")
@auth_required
def mark_as_read(notification_id: int):
    """
    Markiert Benachrichtigung als gelesen.
    
    Requires: Authentication
    
    Args:
        notification_id: Notification-ID
    
    Returns:
        200: NotificationResponse
        404: Notification nicht gefunden
    """
    user_id = g.user_id
    
    container = get_container()
    notification_service = container.notification_service
    
    notification = notification_service.mark_as_read(notification_id, user_id)
    
    return jsonify(notification.model_dump()), 200


@bp.post("/mark-all-read")
@auth_required
def mark_all_as_read():
    """
    Markiert alle Benachrichtigungen als gelesen.
    
    Requires: Authentication
    
    Returns:
        200: {count: int, success: true}
    """
    user_id = g.user_id
    
    container = get_container()
    notification_service = container.notification_service
    
    count = notification_service.mark_all_as_read(user_id)
    
    return jsonify({
        "success": True,
        "count": count,
        "message": f"{count} Benachrichtigungen als gelesen markiert"
    }), 200


@bp.delete("/<int:notification_id>")
@auth_required
def delete_notification(notification_id: int):
    """
    Löscht eine Benachrichtigung.
    
    Requires: Authentication
    
    Args:
        notification_id: Notification-ID
    
    Returns:
        200: {success: true}
        404: Notification nicht gefunden
    """
    user_id = g.user_id
    
    container = get_container()
    notification_service = container.notification_service
    
    notification_service.delete_notification(notification_id, user_id)
    
    return jsonify({"success": True, "message": "Benachrichtigung gelöscht"}), 200
