"""
User Service - Business Logic für User-Operationen.
"""
from typing import Optional

from backend.core.exceptions import (
    ResourceNotFoundError,
    ResourceAlreadyExistsError,
    ValidationError,
)
from backend.core.logging import get_logger
from backend.domain.models import User
from backend.repositories import UserRepository
from backend.schemas import (
    UserResponse,
    UserProfileResponse,
    UpdateUserRequest,
    PaginationParams,
)

logger = get_logger(__name__)


class UserService:
    """Service für User-Operationen."""
    
    def __init__(self, user_repo: Optional[UserRepository] = None):
        self.user_repo = user_repo or UserRepository()
    
    def get_user_by_id(self, user_id: int) -> UserResponse:
        """
        Gibt User anhand der ID zurück.
        
        Args:
            user_id: User-ID
        
        Returns:
            User Response
        
        Raises:
            ResourceNotFoundError: User nicht gefunden
        """
        user = self.user_repo.find_by_id(user_id)
        
        if not user:
            raise ResourceNotFoundError("User", user_id)
        
        return UserResponse.model_validate(user)
    
    def get_user_profile(self, user_id: int) -> UserProfileResponse:
        """
        Gibt erweitertes User-Profil mit Statistiken zurück.
        
        Args:
            user_id: User-ID
        
        Returns:
            User Profile Response mit Statistiken
        
        Raises:
            ResourceNotFoundError: User nicht gefunden
        """
        user = self.user_repo.find_by_id(user_id)
        
        if not user:
            raise ResourceNotFoundError("User", user_id)
        
        # Lade Statistiken
        from backend.repositories import FriendshipRepository, ChallengeMemberRepository, ConfirmationRepository
        
        friend_repo = FriendshipRepository()
        member_repo = ChallengeMemberRepository()
        confirm_repo = ConfirmationRepository()
        
        friends_count = friend_repo.count_friends(user_id)
        challenges_count = len(member_repo.find_by_user(user_id, active_only=True))
        confirmations_count = len(confirm_repo.find_by_user(user_id))
        
        return UserProfileResponse(
            **user.__dict__,
            friends_count=friends_count,
            challenges_count=challenges_count,
            confirmations_count=confirmations_count
        )
    
    def update_user(self, user_id: int, request: UpdateUserRequest) -> UserResponse:
        """
        Aktualisiert User-Daten.
        
        Args:
            user_id: User-ID
            request: Update-Daten
        
        Returns:
            Aktualisierter User
        
        Raises:
            ResourceNotFoundError: User nicht gefunden
            ResourceAlreadyExistsError: E-Mail bereits vergeben
        """
        user = self.user_repo.find_by_id(user_id)
        
        if not user:
            raise ResourceNotFoundError("User", user_id)
        
        # Sammle Update-Daten
        update_data = {}
        
        if request.display_name is not None:
            update_data["display_name"] = request.display_name
        
        if request.avatar_url is not None:
            update_data["avatar_url"] = request.avatar_url
        
        if request.email is not None:
            # Prüfe ob E-Mail bereits existiert
            if self.user_repo.email_exists(request.email, exclude_user_id=user_id):
                raise ResourceAlreadyExistsError(
                    "User",
                    details={"field": "email", "message": "E-Mail bereits vergeben"}
                )
            update_data["email"] = request.email
        
        if not update_data:
            return UserResponse.model_validate(user)
        
        # Aktualisiere User
        updated_user = self.user_repo.update(user_id, update_data)
        
        if not updated_user:
            raise ResourceNotFoundError("User", user_id)
        
        logger.info(f"User {user_id} updated: {list(update_data.keys())}")
        
        return UserResponse.model_validate(updated_user)
    
    def search_users(self, query: str, limit: int = 20) -> list[UserResponse]:
        """
        Sucht User anhand von Query.
        
        Args:
            query: Suchbegriff
            limit: Max. Anzahl Ergebnisse
        
        Returns:
            Liste von Users
        """
        if not query or len(query) < 2:
            raise ValidationError(
                "Suchbegriff muss mindestens 2 Zeichen lang sein",
                details={"field": "query", "min_length": 2}
            )
        
        users = self.user_repo.search_users(query, limit=limit)
        
        return [UserResponse.model_validate(user) for user in users]
    
    def list_users(self, pagination: PaginationParams) -> list[UserResponse]:
        """
        Listet alle User auf (mit Pagination).
        
        Args:
            pagination: Pagination-Parameter
        
        Returns:
            Liste von Users
        """
        users = self.user_repo.find_all(
            limit=pagination.limit,
            offset=pagination.offset,
            order_by="created_at DESC"
        )
        
        return [UserResponse.model_validate(user) for user in users]
    
    def delete_user(self, user_id: int) -> bool:
        """
        Löscht einen User.
        
        Args:
            user_id: User-ID
        
        Returns:
            True wenn erfolgreich
        
        Raises:
            ResourceNotFoundError: User nicht gefunden
        """
        user = self.user_repo.find_by_id(user_id)
        
        if not user:
            raise ResourceNotFoundError("User", user_id)
        
        # Lösche User (CASCADE sollte alle Relationen löschen)
        deleted = self.user_repo.delete(user_id)
        
        if deleted:
            logger.info(f"User {user_id} deleted")
        
        return deleted
