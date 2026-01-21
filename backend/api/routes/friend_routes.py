"""
Friend API Routes - Friendship Management Endpoints.
"""
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError as PydanticValidationError

from backend.api.decorators import auth_required
from backend.core.container import get_container
from backend.core.logging import get_logger
from backend.schemas import FriendRequestRequest

logger = get_logger(__name__)

bp = Blueprint("friends", __name__, url_prefix="/api/friends")


@bp.get("")
@auth_required
def list_friends():
    """
    Listet alle Freunde des eingeloggten Users auf.
    
    Requires: Authentication
    
    Returns:
        200: [FriendshipResponse]
    """
    user_id = g.user_id
    
    container = get_container()
    friend_service = container.friend_service
    
    friends = friend_service.get_friends(user_id)
    
    return jsonify([f.model_dump() for f in friends]), 200


@bp.post("/requests")
@auth_required
def send_friend_request():
    """
    Sendet eine Freundschaftsanfrage.
    
    Requires: Authentication
    
    Request Body:
        - toUserId: int
        - message: str (optional)
    
    Returns:
        201: FriendshipResponse
        400: Validation Error
        404: User nicht gefunden
        409: Freundschaft existiert bereits
    """
    try:
        data = request.get_json(force=True) or {}
        friend_request = FriendRequestRequest(**data)
    except PydanticValidationError as e:
        return jsonify({
            "error": "validation_error",
            "message": "Eingabedaten ungültig",
            "details": e.errors()
        }), 400
    
    user_id = g.user_id
    
    container = get_container()
    friend_service = container.friend_service
    
    friendship = friend_service.send_friend_request(user_id, friend_request)
    
    return jsonify(friendship.model_dump()), 201


@bp.get("/requests/incoming")
@auth_required
def list_incoming_requests():
    """
    Listet eingehende Freundschaftsanfragen auf.
    
    Requires: Authentication
    
    Returns:
        200: [FriendshipResponse]
    """
    user_id = g.user_id
    
    container = get_container()
    friend_service = container.friend_service
    
    requests = friend_service.get_pending_requests(user_id, incoming=True)
    
    return jsonify([r.model_dump() for r in requests]), 200


@bp.get("/requests/outgoing")
@auth_required
def list_outgoing_requests():
    """
    Listet ausgehende Freundschaftsanfragen auf.
    
    Requires: Authentication
    
    Returns:
        200: [FriendshipResponse]
    """
    user_id = g.user_id
    
    container = get_container()
    friend_service = container.friend_service
    
    requests = friend_service.get_pending_requests(user_id, incoming=False)
    
    return jsonify([r.model_dump() for r in requests]), 200


@bp.post("/requests/<int:friendship_id>/accept")
@auth_required
def accept_friend_request(friendship_id: int):
    """
    Akzeptiert eine Freundschaftsanfrage.
    
    Requires: Authentication
    
    Args:
        friendship_id: Friendship-ID
    
    Returns:
        200: FriendshipResponse
        403: Keine Berechtigung
        404: Friendship nicht gefunden
    """
    user_id = g.user_id
    
    container = get_container()
    friend_service = container.friend_service
    
    friendship = friend_service.accept_friend_request(user_id, friendship_id)
    
    return jsonify(friendship.model_dump()), 200


@bp.post("/requests/<int:friendship_id>/decline")
@auth_required
def decline_friend_request(friendship_id: int):
    """
    Lehnt eine Freundschaftsanfrage ab.
    
    Requires: Authentication
    
    Args:
        friendship_id: Friendship-ID
    
    Returns:
        200: {success: true}
        403: Keine Berechtigung
        404: Friendship nicht gefunden
    """
    user_id = g.user_id
    
    container = get_container()
    friend_service = container.friend_service
    
    friend_service.decline_friend_request(user_id, friendship_id)
    
    return jsonify({"success": True, "message": "Freundschaftsanfrage abgelehnt"}), 200


@bp.delete("/<int:friend_id>")
@auth_required
def remove_friend(friend_id: int):
    """
    Entfernt einen Freund.
    
    Requires: Authentication
    
    Args:
        friend_id: User-ID des Freunds
    
    Returns:
        200: {success: true}
        404: Friendship nicht gefunden
    """
    user_id = g.user_id
    
    container = get_container()
    friend_service = container.friend_service
    
    friend_service.remove_friend(user_id, friend_id)
    
    return jsonify({"success": True, "message": "Freund entfernt"}), 200
