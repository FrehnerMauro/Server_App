"""
Authentication Decorators für API-Routen.
"""
from functools import wraps
from flask import request, g

from backend.core.container import get_container
from backend.core.exceptions import MissingTokenError, InvalidTokenError, AuthorizationError
from backend.core.logging import get_logger

logger = get_logger(__name__)


def auth_required(fn):
    """
    Decorator für authentifizierte Routen.
    Validiert Token und lädt aktuellen User in Request-Context.
    
    Usage:
        @bp.get("/profile")
        @auth_required
        def get_profile():
            user = g.current_user
            return {"user": user}
    """
    
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Extrahiere Token aus Authorization Header
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header")
            raise MissingTokenError()
        
        token = auth_header.split(" ", 1)[1].strip()
        
        if not token:
            logger.warning("Empty token in Authorization header")
            raise MissingTokenError("Token ist leer")
        
        # Validiere Token
        container = get_container()
        auth_service = container.auth_service
        
        try:
            user = auth_service.validate_token(token)
        except InvalidTokenError:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise InvalidTokenError("Token-Validierung fehlgeschlagen")
        
        # Setze User im Request-Context
        g.current_user = user
        g.user_id = user.id
        
        # Für Abwärtskompatibilität mit altem Code
        request.uid = user.id
        request.user = user
        
        return fn(*args, **kwargs)
    
    return wrapper


def admin_required(fn):
    """
    Decorator für Admin-Routen.
    Validiert Token und prüft Admin-Berechtigung.
    
    Usage:
        @bp.get("/admin/users")
        @admin_required
        def list_all_users():
            # Nur Admins können diese Route aufrufen
            return {"users": [...]}
    """
    
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Erst normale Auth-Prüfung
        auth_header = request.headers.get("Authorization", "")
        
        if not auth_header.startswith("Bearer "):
            logger.warning("Missing or invalid Authorization header")
            raise MissingTokenError()
        
        token = auth_header.split(" ", 1)[1].strip()
        
        if not token:
            raise MissingTokenError("Token ist leer")
        
        # Validiere Token
        container = get_container()
        auth_service = container.auth_service
        
        try:
            user = auth_service.validate_token(token)
        except InvalidTokenError:
            raise
        except Exception as e:
            logger.error(f"Token validation error: {e}")
            raise InvalidTokenError("Token-Validierung fehlgeschlagen")
        
        # Prüfe Admin-Berechtigung
        if not user.is_admin:
            logger.warning(f"User {user.id} tried to access admin route without permission")
            raise AuthorizationError("Admin-Berechtigung erforderlich")
        
        # Setze User im Request-Context
        g.current_user = user
        g.user_id = user.id
        request.uid = user.id
        request.user = user
        
        return fn(*args, **kwargs)
    
    return wrapper


def optional_auth(fn):
    """
    Decorator für optional authentifizierte Routen.
    Lädt User wenn Token vorhanden, wirft aber keinen Fehler wenn nicht.
    
    Usage:
        @bp.get("/public-feed")
        @optional_auth
        def get_public_feed():
            user = g.get("current_user")  # Kann None sein
            # Zeige mehr wenn eingeloggt
            return {"feed": [...]}
    """
    
    @wraps(fn)
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            
            if token:
                try:
                    container = get_container()
                    auth_service = container.auth_service
                    user = auth_service.validate_token(token)
                    
                    g.current_user = user
                    g.user_id = user.id
                    request.uid = user.id
                    request.user = user
                except Exception as e:
                    logger.debug(f"Optional auth failed (ignored): {e}")
                    pass
        
        return fn(*args, **kwargs)
    
    return wrapper
