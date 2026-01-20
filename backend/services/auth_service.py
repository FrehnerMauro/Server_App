"""
Authentication Service - Business Logic für Auth-Operationen.
"""
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional

from backend.core.config import get_settings
from backend.core.exceptions import (
    AuthenticationError,
    InvalidTokenError,
    ResourceAlreadyExistsError,
    ValidationError,
)
from backend.core.logging import get_logger
from backend.domain.models import User, AuthToken, UserRole
from backend.repositories import UserRepository, AuthTokenRepository
from backend.schemas import LoginRequest, RegisterRequest, AuthResponse, UserResponse

logger = get_logger(__name__)


class AuthService:
    """Service für Authentication und Authorization."""
    
    def __init__(
        self,
        user_repo: Optional[UserRepository] = None,
        token_repo: Optional[AuthTokenRepository] = None
    ):
        self.user_repo = user_repo or UserRepository()
        self.token_repo = token_repo or AuthTokenRepository()
        self.settings = get_settings()
    
    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hashed Passwort mit SHA256.
        
        Args:
            password: Klartext-Passwort
        
        Returns:
            Gehashtes Passwort
        """
        return hashlib.sha256(password.encode("utf-8")).hexdigest()
    
    @staticmethod
    def generate_token(user_id: int) -> str:
        """
        Generiert einen sicheren Auth-Token.
        
        Args:
            user_id: User-ID
        
        Returns:
            Token-String
        """
        timestamp = int(datetime.utcnow().timestamp() * 1000)
        random_part = secrets.token_urlsafe(32)
        return f"token-{user_id}-{timestamp}-{random_part}"
    
    def register(self, request: RegisterRequest) -> AuthResponse:
        """
        Registriert einen neuen Benutzer.
        
        Args:
            request: Registrierungs-Daten
        
        Returns:
            Auth-Response mit Token und User
        
        Raises:
            ResourceAlreadyExistsError: E-Mail existiert bereits
            ValidationError: Nutzungsbedingungen nicht akzeptiert
        """
        logger.info(f"Register attempt for email: {request.email}")
        
        # Prüfe ob E-Mail existiert
        if self.user_repo.email_exists(request.email):
            logger.warning(f"Registration failed: email {request.email} already exists")
            raise ResourceAlreadyExistsError(
                "User",
                details={"field": "email", "message": "E-Mail bereits registriert"}
            )
        
        # Prüfe Nutzungsbedingungen
        if request.nb_state != "accepted":
            raise ValidationError(
                "Nutzungsbedingungen müssen akzeptiert werden",
                details={"field": "nb_state", "required": "accepted"}
            )
        
        # Erstelle User
        now = int(datetime.utcnow().timestamp() * 1000)
        username = f"{request.vorname.lower()}.{request.name.lower()}"
        
        user = self.user_repo.create({
            "username": username,
            "display_name": f"{request.vorname} {request.name}",
            "email": request.email,
            "avatar_url": request.avatar,
            "password": self.hash_password(request.password),
            "is_admin": 0,
            "role": UserRole.USER.value,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        })
        
        # Erstelle Token
        token_str = self.generate_token(user.id)
        self.token_repo.create({
            "user_id": user.id,
            "token": token_str,
            "device": None,
            "created_at": now
        })
        
        logger.info(f"User registered successfully: id={user.id}, email={user.email}")
        
        return AuthResponse(
            token=token_str,
            user=UserResponse.model_validate(user)
        )
    
    def login(self, request: LoginRequest) -> AuthResponse:
        """
        Authentifiziert einen Benutzer.
        
        Args:
            request: Login-Daten
        
        Returns:
            Auth-Response mit Token und User
        
        Raises:
            AuthenticationError: Login fehlgeschlagen
        """
        logger.info(f"Login attempt for email: {request.email}")
        
        # Finde User
        user = self.user_repo.find_by_email(request.email)
        if not user:
            logger.warning(f"Login failed: user not found for {request.email}")
            raise AuthenticationError("E-Mail oder Passwort falsch")
        
        # Prüfe Passwort
        if not self._verify_password(request.password, user):
            logger.warning(f"Login failed: invalid password for {request.email}")
            raise AuthenticationError("E-Mail oder Passwort falsch")
        
        # Prüfe ob User aktiv
        if not user.is_active:
            logger.warning(f"Login failed: user {user.id} is inactive")
            raise AuthenticationError("Benutzer ist deaktiviert")
        
        # Finde oder erstelle Token
        tokens = self.token_repo.find_by_user_id(user.id)
        
        if tokens:
            # Verwende existierenden Token
            token_str = tokens[0].token
            logger.info(f"Reusing existing token for user {user.id}")
        else:
            # Erstelle neuen Token
            token_str = self.generate_token(user.id)
            now = int(datetime.utcnow().timestamp() * 1000)
            
            self.token_repo.create({
                "user_id": user.id,
                "token": token_str,
                "device": request.device_token,
                "created_at": now
            })
            logger.info(f"Created new token for user {user.id}")
        
        logger.info(f"User logged in successfully: id={user.id}, email={user.email}")
        
        return AuthResponse(
            token=token_str,
            user=UserResponse.model_validate(user)
        )
    
    def _verify_password(self, password: str, user: User) -> bool:
        """
        Verifiziert Passwort gegen User.
        
        Args:
            password: Klartext-Passwort
            user: User Domain Model
        
        Returns:
            True wenn Passwort korrekt
        """
        # Wir müssen das Password-Feld aus der DB laden
        from backend.core.database import get_db_cursor
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute("SELECT password FROM users WHERE id = %s", (user.id,))
                row = cursor.fetchone()
                
                if row and row.get("password"):
                    return row["password"] == self.hash_password(password)
                
                return False
        except Exception as e:
            logger.error(f"Error verifying password: {e}")
            return False
    
    def validate_token(self, token: str) -> User:
        """
        Validiert einen Auth-Token und gibt User zurück.
        
        Args:
            token: Token-String
        
        Returns:
            User Domain Model
        
        Raises:
            InvalidTokenError: Token ungültig oder abgelaufen
        """
        auth_token = self.token_repo.find_by_token(token)
        
        if not auth_token:
            logger.warning(f"Token validation failed: token not found")
            raise InvalidTokenError()
        
        # Prüfe Ablaufdatum (falls gesetzt)
        if auth_token.expires_at and auth_token.expires_at < datetime.utcnow():
            logger.warning(f"Token validation failed: token expired")
            raise InvalidTokenError("Token ist abgelaufen")
        
        # Lade User
        user = self.user_repo.find_by_id(auth_token.user_id)
        
        if not user:
            logger.error(f"Token validation failed: user {auth_token.user_id} not found")
            raise InvalidTokenError("Benutzer nicht gefunden")
        
        if not user.is_active:
            logger.warning(f"Token validation failed: user {user.id} is inactive")
            raise InvalidTokenError("Benutzer ist deaktiviert")
        
        return user
    
    def logout(self, token: str) -> bool:
        """
        Loggt einen Benutzer aus (löscht Token).
        
        Args:
            token: Token-String
        
        Returns:
            True wenn erfolgreich
        """
        deleted = self.token_repo.delete_by_token(token)
        
        if deleted:
            logger.info(f"User logged out successfully")
        
        return deleted
    
    def revoke_all_tokens(self, user_id: int) -> int:
        """
        Widerruft alle Tokens eines Users.
        
        Args:
            user_id: User-ID
        
        Returns:
            Anzahl widerrufener Tokens
        """
        count = self.token_repo.delete_by_user_id(user_id)
        logger.info(f"Revoked {count} tokens for user {user_id}")
        return count
