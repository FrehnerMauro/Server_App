"""
User API Routes - User Management Endpoints.
"""
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError as PydanticValidationError

from backend.api.decorators import auth_required
from backend.core.container import get_container
from backend.core.logging import get_logger
from backend.schemas import UpdateUserRequest, PaginationParams

logger = get_logger(__name__)

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.get("/me")
@auth_required
def get_my_profile():
    """
    Gibt eigenes Profil mit Statistiken zurück.
    
    Requires: Authentication
    
    Returns:
        200: UserProfileResponse
    """
    user_id = g.user_id
    
    container = get_container()
    user_service = container.user_service
    
    profile = user_service.get_user_profile(user_id)
    
    return jsonify(profile.model_dump()), 200


@bp.get("/<int:user_id>")
@auth_required
def get_user(user_id: int):
    """
    Gibt User anhand der ID zurück.
    
    Requires: Authentication
    
    Args:
        user_id: User-ID
    
    Returns:
        200: UserResponse
        404: User nicht gefunden
    """
    container = get_container()
    user_service = container.user_service
    
    user = user_service.get_user_by_id(user_id)
    
    return jsonify(user.model_dump()), 200


@bp.patch("/me")
@auth_required
def update_my_profile():
    """
    Aktualisiert eigenes Profil.
    
    Requires: Authentication
    
    Request Body:
        - display_name: str (optional)
        - avatar_url: str (optional)
        - email: str (optional)
    
    Returns:
        200: UserResponse
        400: Validation Error
        409: E-Mail bereits vergeben
    """
    user_id = g.user_id
    
    try:
        data = request.get_json(force=True) or {}
        update_request = UpdateUserRequest(**data)
    except PydanticValidationError as e:
        return jsonify({
            "error": "validation_error",
            "message": "Eingabedaten ungültig",
            "details": e.errors()
        }), 400
    
    container = get_container()
    user_service = container.user_service
    
    user = user_service.update_user(user_id, update_request)
    
    return jsonify(user.model_dump()), 200


@bp.get("/search")
@auth_required
def search_users():
    """
    Sucht User anhand von Query-Parameter.
    
    Requires: Authentication
    
    Query Params:
        - q: str (Suchbegriff, min. 2 Zeichen)
        - limit: int (optional, default: 20)
    
    Returns:
        200: [UserResponse]
        400: Query zu kurz
    """
    query = request.args.get("q", "").strip()
    limit = min(int(request.args.get("limit", 20)), 100)
    
    if not query or len(query) < 2:
        return jsonify({
            "error": "validation_error",
            "message": "Suchbegriff muss mindestens 2 Zeichen lang sein"
        }), 400
    
    container = get_container()
    user_service = container.user_service
    
    users = user_service.search_users(query, limit=limit)
    
    return jsonify([u.model_dump() for u in users]), 200


@bp.get("")
@auth_required
def list_users():
    """
    Listet alle User auf (mit Pagination).
    
    Requires: Authentication
    
    Query Params:
        - page: int (default: 1)
        - page_size: int (default: 20, max: 100)
    
    Returns:
        200: [UserResponse]
    """
    try:
        page = int(request.args.get("page", 1))
        page_size = min(int(request.args.get("page_size", 20)), 100)
        
        pagination = PaginationParams(page=page, page_size=page_size)
    except ValueError:
        return jsonify({
            "error": "validation_error",
            "message": "Ungültige Pagination-Parameter"
        }), 400
    
    container = get_container()
    user_service = container.user_service
    
    users = user_service.list_users(pagination)
    
    return jsonify([u.model_dump() for u in users]), 200
