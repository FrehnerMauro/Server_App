"""
Challenge API Routes - Challenge Management Endpoints.
"""
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError as PydanticValidationError

from backend.api.decorators import auth_required
from backend.core.container import get_container
from backend.core.logging import get_logger
from backend.schemas import (
    CreateChallengeRequest,
    ConfirmChallengeRequest,
    ChatMessageRequest,
)

logger = get_logger(__name__)

bp = Blueprint("challenges", __name__, url_prefix="/api/challenges")


@bp.post("")
@auth_required
def create_challenge():
    """
    Erstellt eine neue Challenge.
    
    Requires: Authentication
    
    Request Body:
        - name: str
        - beschreibung: str (optional)
        - startAt: int (optional, timestamp)
        - faelligeWochentage: list[int]
        - dauerTage: int (default: 30)
        - erlaubteFailsTage: int (default: 0)
        - friendsToAdd: list[int] (optional)
    
    Returns:
        201: ChallengeDetailResponse
        400: Validation Error
    """
    try:
        data = request.get_json(force=True) or {}
        create_request = CreateChallengeRequest(**data)
    except PydanticValidationError as e:
        return jsonify({
            "error": "validation_error",
            "message": "Eingabedaten ungültig",
            "details": e.errors()
        }), 400
    
    user_id = g.user_id
    
    container = get_container()
    challenge_service = container.challenge_service
    
    challenge = challenge_service.create_challenge(user_id, create_request)
    
    return jsonify(challenge.model_dump()), 201


@bp.get("")
@auth_required
def list_challenges():
    """
    Listet alle Challenges des eingeloggten Users auf.
    
    Requires: Authentication
    
    Returns:
        200: [ChallengeResponse]
    """
    user_id = g.user_id
    
    container = get_container()
    challenge_service = container.challenge_service
    
    challenges = challenge_service.list_user_challenges(user_id)
    
    return jsonify([c.model_dump() for c in challenges]), 200


@bp.get("/<int:challenge_id>")
@auth_required
def get_challenge(challenge_id: int):
    """
    Gibt Challenge-Details zurück.
    
    Requires: Authentication
    
    Args:
        challenge_id: Challenge-ID
    
    Returns:
        200: ChallengeDetailResponse
        404: Challenge nicht gefunden
    """
    user_id = g.user_id
    
    container = get_container()
    challenge_service = container.challenge_service
    
    challenge = challenge_service.get_challenge(challenge_id, user_id)
    
    return jsonify(challenge.model_dump()), 200


@bp.post("/<int:challenge_id>/confirm")
@auth_required
def confirm_challenge(challenge_id: int):
    """
    Bestätigt Challenge-Aktivität für einen Tag.
    
    Requires: Authentication
    
    Args:
        challenge_id: Challenge-ID
    
    Request Body:
        - imageUrl: str
        - caption: str (optional)
        - visibility: str (optional, default: "freunde")
    
    Returns:
        201: ConfirmationResponse
        400: Validation Error
        403: Nicht Mitglied der Challenge
        404: Challenge nicht gefunden
    """
    try:
        data = request.get_json(force=True) or {}
        confirm_request = ConfirmChallengeRequest(**data)
    except PydanticValidationError as e:
        return jsonify({
            "error": "validation_error",
            "message": "Eingabedaten ungültig",
            "details": e.errors()
        }), 400
    
    user_id = g.user_id
    
    container = get_container()
    challenge_service = container.challenge_service
    
    confirmation = challenge_service.confirm_challenge(
        challenge_id,
        user_id,
        confirm_request
    )
    
    return jsonify(confirmation.model_dump()), 201


@bp.get("/<int:challenge_id>/chat")
@auth_required
def get_challenge_chat(challenge_id: int):
    """
    Gibt Challenge-Chat zurück.
    
    Requires: Authentication
    
    Args:
        challenge_id: Challenge-ID
    
    Query Params:
        - limit: int (optional, default: 50)
    
    Returns:
        200: [ChatMessageResponse]
        403: Nicht Mitglied der Challenge
        404: Challenge nicht gefunden
    """
    user_id = g.user_id
    limit = min(int(request.args.get("limit", 50)), 200)
    
    container = get_container()
    challenge_service = container.challenge_service
    
    messages = challenge_service.get_challenge_chat(challenge_id, user_id, limit)
    
    return jsonify([m.model_dump() for m in messages]), 200


@bp.post("/<int:challenge_id>/chat")
@auth_required
def post_chat_message(challenge_id: int):
    """
    Postet Chat-Nachricht in Challenge.
    
    Requires: Authentication
    
    Args:
        challenge_id: Challenge-ID
    
    Request Body:
        - text: str
    
    Returns:
        201: ChatMessageResponse
        400: Validation Error
        403: Nicht Mitglied der Challenge
        404: Challenge nicht gefunden
    """
    try:
        data = request.get_json(force=True) or {}
        chat_request = ChatMessageRequest(**data)
    except PydanticValidationError as e:
        return jsonify({
            "error": "validation_error",
            "message": "Eingabedaten ungültig",
            "details": e.errors()
        }), 400
    
    user_id = g.user_id
    
    container = get_container()
    challenge_service = container.challenge_service
    
    message = challenge_service.post_chat_message(challenge_id, user_id, chat_request)
    
    return jsonify(message.model_dump()), 201


@bp.get("/<int:challenge_id>/members")
@auth_required
def get_challenge_members(challenge_id: int):
    """
    Gibt Mitglieder einer Challenge zurück.
    
    Requires: Authentication
    
    Args:
        challenge_id: Challenge-ID
    
    Returns:
        200: [ChallengeMemberResponse]
        404: Challenge nicht gefunden
    """
    container = get_container()
    member_repo = container.member_repo
    user_repo = container.user_repo
    
    # Prüfe ob Challenge existiert
    challenge = container.challenge_repo.find_by_id(challenge_id)
    if not challenge:
        from backend.core.exceptions import ResourceNotFoundError
        raise ResourceNotFoundError("Challenge", challenge_id)
    
    # Lade Mitglieder
    members = member_repo.find_by_challenge(challenge_id, active_only=True)
    
    # Lade User-Daten
    user_ids = [m.user_id for m in members]
    users = {u.id: u for u in [user_repo.find_by_id(uid) for uid in user_ids] if u}
    
    from backend.schemas import ChallengeMemberResponse, UserResponse
    
    result = [
        ChallengeMemberResponse(
            **m.__dict__,
            user=UserResponse.model_validate(users[m.user_id]) if m.user_id in users else None
        )
        for m in members
    ]
    
    return jsonify([r.model_dump() for r in result]), 200
