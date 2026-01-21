"""
Auth API Routes - Authentication Endpoints.
"""
from flask import Blueprint, request, jsonify, g
from pydantic import ValidationError as PydanticValidationError

from backend.api.decorators import auth_required
from backend.core.container import get_container
from backend.core.exceptions import AppException
from backend.core.logging import get_logger
from backend.schemas import LoginRequest, RegisterRequest

logger = get_logger(__name__)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.post("/register")
def register():
    """
    Registriert einen neuen Benutzer.
    
    Request Body:
        - vorname: str
        - name: str
        - email: str
        - password: str
        - avatar: str (optional)
        - nb_state: str (muss "accepted" sein)
    
    Returns:
        201: {token: str, user: UserResponse}
        400: Validation Error
        409: E-Mail existiert bereits
    """
    try:
        data = request.get_json(force=True) or {}
        register_request = RegisterRequest(**data)
    except PydanticValidationError as e:
        logger.warning(f"Registration validation error: {e.errors()}")
        return jsonify({
            "error": "validation_error",
            "message": "Eingabedaten ungültig",
            "details": e.errors()
        }), 400
    
    container = get_container()
    auth_service = container.auth_service
    
    response = auth_service.register(register_request)
    
    return jsonify(response.model_dump()), 201


@bp.post("/login")
def login():
    """
    Authentifiziert einen Benutzer.
    
    Request Body:
        - email: str
        - password: str
        - device_token: str (optional)
    
    Returns:
        200: {token: str, user: UserResponse}
        401: Login fehlgeschlagen
    """
    try:
        data = request.get_json(force=True) or {}
        login_request = LoginRequest(**data)
    except PydanticValidationError as e:
        logger.warning(f"Login validation error: {e.errors()}")
        return jsonify({
            "error": "validation_error",
            "message": "Eingabedaten ungültig",
            "details": e.errors()
        }), 400
    
    container = get_container()
    auth_service = container.auth_service
    
    response = auth_service.login(login_request)
    
    return jsonify(response.model_dump()), 200


@bp.post("/logout")
@auth_required
def logout():
    """
    Loggt einen Benutzer aus.
    
    Requires: Authentication
    
    Returns:
        200: {success: true}
    """
    # Token aus Header extrahieren
    auth_header = request.headers.get("Authorization", "")
    token = auth_header.split(" ", 1)[1].strip()
    
    container = get_container()
    auth_service = container.auth_service
    
    auth_service.logout(token)
    
    return jsonify({"success": True, "message": "Erfolgreich ausgeloggt"}), 200


@bp.get("/me")
@auth_required
def get_current_user():
    """
    Gibt aktuell eingeloggten User zurück.
    
    Requires: Authentication
    
    Returns:
        200: UserResponse
    """
    user = g.current_user
    
    from backend.schemas import UserResponse
    return jsonify(UserResponse.model_validate(user).model_dump()), 200


@bp.post("/refresh")
@auth_required
def refresh_token():
    """
    Erneuert das Auth-Token (optional).
    
    Requires: Authentication
    
    Returns:
        200: {token: str}
    """
    user = g.current_user
    
    container = get_container()
    auth_service = container.auth_service
    
    # Generiere neues Token
    new_token = auth_service.generate_token(user.id)
    
    # Speichere neues Token
    from datetime import datetime
    now = int(datetime.utcnow().timestamp() * 1000)
    
    container.auth_token_repo.create({
        "user_id": user.id,
        "token": new_token,
        "created_at": now
    })
    
    return jsonify({"token": new_token}), 200
