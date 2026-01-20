"""
Flask Middleware für Request-Processing.
"""
import time
import uuid
from flask import Flask, request, g, jsonify
from typing import Any

from backend.core.logging import get_logger
from backend.core.exceptions import AppException

logger = get_logger(__name__)


def setup_request_id_middleware(app: Flask) -> None:
    """
    Fügt jedem Request eine eindeutige ID hinzu.
    
    Args:
        app: Flask App Instanz
    """
    
    @app.before_request
    def add_request_id():
        """Generiert Request-ID und fügt sie zum Request-Context hinzu."""
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        g.request_id = request_id
        
    @app.after_request
    def add_request_id_to_response(response):
        """Fügt Request-ID zum Response-Header hinzu."""
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id
        return response


def setup_logging_middleware(app: Flask) -> None:
    """
    Loggt alle Requests und Responses.
    
    Args:
        app: Flask App Instanz
    """
    
    @app.before_request
    def log_request():
        """Loggt eingehende Requests."""
        g.start_time = time.time()
        
        request_id = getattr(g, "request_id", "unknown")
        
        logger.info(
            f"[{request_id}] {request.method} {request.path} "
            f"from {request.remote_addr}"
        )
        
        # Log Request Body (nur für nicht-GET Requests)
        if request.method != "GET" and request.is_json:
            body = request.get_json(silent=True)
            if body:
                # Entferne sensible Daten
                safe_body = _sanitize_log_data(body)
                logger.debug(f"[{request_id}] Request Body: {safe_body}")
    
    @app.after_request
    def log_response(response):
        """Loggt ausgehende Responses."""
        request_id = getattr(g, "request_id", "unknown")
        
        # Berechne Request-Dauer
        duration = 0
        if hasattr(g, "start_time"):
            duration = (time.time() - g.start_time) * 1000  # in ms
        
        logger.info(
            f"[{request_id}] {request.method} {request.path} "
            f"-> {response.status_code} ({duration:.2f}ms)"
        )
        
        return response


def setup_error_handler(app: Flask) -> None:
    """
    Globaler Error Handler für strukturierte Fehler-Responses.
    
    Args:
        app: Flask App Instanz
    """
    
    @app.errorhandler(AppException)
    def handle_app_exception(error: AppException):
        """Handler für eigene AppExceptions."""
        request_id = getattr(g, "request_id", "unknown")
        
        logger.warning(
            f"[{request_id}] AppException: {error.code} - {error.message}",
            extra={"details": error.details}
        )
        
        response = {
            "error": error.code,
            "message": error.message,
            "request_id": request_id
        }
        
        if error.details:
            response["details"] = error.details
        
        return jsonify(response), error.status_code
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handler für 404 Not Found."""
        request_id = getattr(g, "request_id", "unknown")
        
        return jsonify({
            "error": "not_found",
            "message": "Die angeforderte Ressource wurde nicht gefunden",
            "request_id": request_id
        }), 404
    
    @app.errorhandler(405)
    def handle_method_not_allowed(error):
        """Handler für 405 Method Not Allowed."""
        request_id = getattr(g, "request_id", "unknown")
        
        return jsonify({
            "error": "method_not_allowed",
            "message": "Diese HTTP-Methode ist für diese Route nicht erlaubt",
            "request_id": request_id
        }), 405
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handler für 500 Internal Server Error."""
        request_id = getattr(g, "request_id", "unknown")
        
        logger.error(
            f"[{request_id}] Internal Server Error: {str(error)}",
            exc_info=True
        )
        
        return jsonify({
            "error": "internal_error",
            "message": "Ein interner Serverfehler ist aufgetreten",
            "request_id": request_id
        }), 500
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Handler für unerwartete Exceptions."""
        request_id = getattr(g, "request_id", "unknown")
        
        logger.error(
            f"[{request_id}] Unexpected error: {str(error)}",
            exc_info=True
        )
        
        return jsonify({
            "error": "unexpected_error",
            "message": "Ein unerwarteter Fehler ist aufgetreten",
            "request_id": request_id
        }), 500


def setup_cors_middleware(app: Flask) -> None:
    """
    Erweiterte CORS-Konfiguration.
    
    Args:
        app: Flask App Instanz
    """
    from backend.core.config import get_settings
    
    settings = get_settings()
    
    @app.after_request
    def add_cors_headers(response):
        """Fügt CORS-Header hinzu."""
        origin = request.headers.get("Origin")
        
        # Prüfe ob Origin erlaubt ist
        if origin in settings.cors_origins or "*" in settings.cors_origins:
            response.headers["Access-Control-Allow-Origin"] = origin or "*"
            response.headers["Access-Control-Allow-Credentials"] = str(
                settings.cors_allow_credentials
            ).lower()
            response.headers["Access-Control-Allow-Methods"] = ", ".join(
                settings.cors_allow_methods
            )
            response.headers["Access-Control-Allow-Headers"] = ", ".join(
                settings.cors_allow_headers
            )
        
        return response


def setup_security_headers(app: Flask) -> None:
    """
    Fügt Security-Header hinzu.
    
    Args:
        app: Flask App Instanz
    """
    
    @app.after_request
    def add_security_headers(response):
        """Fügt Security-Header hinzu."""
        # Verhindert Clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        
        # Verhindert MIME-Type Sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        
        # XSS-Protection
        response.headers["X-XSS-Protection"] = "1; mode=block"
        
        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response


def _sanitize_log_data(data: Any) -> Any:
    """
    Entfernt sensible Daten aus Log-Output.
    
    Args:
        data: Zu bereinigende Daten
    
    Returns:
        Bereinigte Daten
    """
    if isinstance(data, dict):
        sanitized = {}
        sensitive_keys = {"password", "token", "secret", "api_key", "device_token"}
        
        for key, value in data.items():
            if key.lower() in sensitive_keys:
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, (dict, list)):
                sanitized[key] = _sanitize_log_data(value)
            else:
                sanitized[key] = value
        
        return sanitized
    elif isinstance(data, list):
        return [_sanitize_log_data(item) for item in data]
    else:
        return data


def setup_all_middleware(app: Flask) -> None:
    """
    Konfiguriert alle Middleware.
    
    Args:
        app: Flask App Instanz
    """
    setup_request_id_middleware(app)
    setup_logging_middleware(app)
    setup_error_handler(app)
    setup_cors_middleware(app)
    setup_security_headers(app)
    
    logger.info("All middleware configured")
