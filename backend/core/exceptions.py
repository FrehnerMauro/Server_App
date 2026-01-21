"""
Custom Exceptions für die Anwendung.
"""
from typing import Any, Optional


class AppException(Exception):
    """Basis-Exception für alle App-spezifischen Fehler."""
    
    def __init__(
        self,
        message: str,
        code: str = "internal_error",
        status_code: int = 500,
        details: Optional[dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


# Authentication & Authorization
class AuthenticationError(AppException):
    """Fehler bei der Authentifizierung."""
    
    def __init__(self, message: str = "Authentication failed", details: Optional[dict] = None):
        super().__init__(message, code="authentication_error", status_code=401, details=details)


class InvalidTokenError(AuthenticationError):
    """Token ist ungültig oder abgelaufen."""
    
    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(message, details={"code": "invalid_token"})


class MissingTokenError(AuthenticationError):
    """Token fehlt im Request."""
    
    def __init__(self, message: str = "Authentication token missing"):
        super().__init__(message, details={"code": "missing_token"})


class AuthorizationError(AppException):
    """Fehler bei der Autorisierung."""
    
    def __init__(self, message: str = "Insufficient permissions", details: Optional[dict] = None):
        super().__init__(message, code="authorization_error", status_code=403, details=details)


# Validation
class ValidationError(AppException):
    """Fehler bei der Validierung von Eingabedaten."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, code="validation_error", status_code=400, details=details)


class InvalidInputError(ValidationError):
    """Eingabedaten sind ungültig."""
    
    def __init__(self, field: str, message: str):
        super().__init__(
            message=f"Invalid input for field '{field}': {message}",
            details={"field": field, "message": message}
        )


# Resources
class ResourceNotFoundError(AppException):
    """Ressource wurde nicht gefunden."""
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            message=f"{resource_type} with id '{resource_id}' not found",
            code="not_found",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": str(resource_id)}
        )


class ResourceAlreadyExistsError(AppException):
    """Ressource existiert bereits."""
    
    def __init__(self, resource_type: str, details: Optional[dict] = None):
        super().__init__(
            message=f"{resource_type} already exists",
            code="already_exists",
            status_code=409,
            details=details
        )


class ResourceConflictError(AppException):
    """Konflikt bei der Ressourcen-Operation."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, code="conflict", status_code=409, details=details)


# Business Logic
class BusinessLogicError(AppException):
    """Fehler in der Business-Logik."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, code="business_logic_error", status_code=422, details=details)


class InsufficientPermissionsError(BusinessLogicError):
    """Unzureichende Berechtigungen für die Operation."""
    
    def __init__(self, message: str = "Insufficient permissions for this operation"):
        super().__init__(message, details={"code": "insufficient_permissions"})


# Database
class DatabaseError(AppException):
    """Fehler bei Datenbankoperationen."""
    
    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message, code="database_error", status_code=500, details=details)


# External Services
class ExternalServiceError(AppException):
    """Fehler bei der Kommunikation mit externen Services."""
    
    def __init__(self, service_name: str, message: str, details: Optional[dict] = None):
        super().__init__(
            message=f"Error communicating with {service_name}: {message}",
            code="external_service_error",
            status_code=503,
            details={"service": service_name, **(details or {})}
        )


class RateLimitError(AppException):
    """Rate-Limit wurde überschritten."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        details = {"retry_after": retry_after} if retry_after else {}
        super().__init__(message, code="rate_limit_exceeded", status_code=429, details=details)
