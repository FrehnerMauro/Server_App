"""
User Repository - Datenbankzugriff für User-Entitäten.
"""
from datetime import datetime
from typing import Optional

from psycopg2.extras import RealDictRow

from backend.domain.models import User, UserRole, AuthToken
from backend.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository für User-Operationen."""
    
    def __init__(self):
        super().__init__("users", User)
    
    def _row_to_model(self, row: RealDictRow) -> User:
        """Konvertiert DB-Row zu User Domain Model."""
        return User(
            id=row["id"],
            username=row["username"],
            email=row["email"],
            display_name=row.get("display_name"),
            avatar_url=row.get("avatar_url"),
            role=UserRole(row.get("role", "user")) if row.get("is_admin") != 1 else UserRole.ADMIN,
            is_active=bool(row.get("is_active", True)),
            created_at=self._timestamp_to_datetime(row["created_at"]),
            updated_at=self._timestamp_to_datetime(row["updated_at"])
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Millisekunden-Timestamp zu datetime."""
        if timestamp > 10**12:  # Millisekunden
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def find_by_email(self, email: str) -> Optional[User]:
        """
        Sucht User anhand der E-Mail (case-insensitive).
        
        Args:
            email: E-Mail-Adresse
        
        Returns:
            User oder None
        """
        return self.find_one_where("LOWER(email) = LOWER(%s)", (email,))
    
    def find_by_username(self, username: str) -> Optional[User]:
        """
        Sucht User anhand des Usernames.
        
        Args:
            username: Username
        
        Returns:
            User oder None
        """
        return self.find_one_where("LOWER(username) = LOWER(%s)", (username,))
    
    def email_exists(self, email: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        Prüft ob E-Mail bereits existiert.
        
        Args:
            email: E-Mail-Adresse
            exclude_user_id: Optional User-ID die ausgeschlossen werden soll
        
        Returns:
            True wenn E-Mail existiert
        """
        where = "LOWER(email) = LOWER(%s)"
        params = [email]
        
        if exclude_user_id:
            where += " AND id != %s"
            params.append(exclude_user_id)
        
        return self.count(where, tuple(params)) > 0
    
    def username_exists(self, username: str, exclude_user_id: Optional[int] = None) -> bool:
        """
        Prüft ob Username bereits existiert.
        
        Args:
            username: Username
            exclude_user_id: Optional User-ID die ausgeschlossen werden soll
        
        Returns:
            True wenn Username existiert
        """
        where = "LOWER(username) = LOWER(%s)"
        params = [username]
        
        if exclude_user_id:
            where += " AND id != %s"
            params.append(exclude_user_id)
        
        return self.count(where, tuple(params)) > 0
    
    def search_users(self, query: str, limit: int = 20) -> list[User]:
        """
        Sucht User anhand von Name oder E-Mail.
        
        Args:
            query: Suchbegriff
            limit: Max. Anzahl Ergebnisse
        
        Returns:
            Liste von Users
        """
        where = """
            LOWER(username) LIKE LOWER(%s) OR 
            LOWER(email) LIKE LOWER(%s) OR 
            LOWER(display_name) LIKE LOWER(%s)
        """
        search_pattern = f"%{query}%"
        
        return self.find_where(
            where,
            (search_pattern, search_pattern, search_pattern),
            limit=limit,
            order_by="username ASC"
        )


class AuthTokenRepository(BaseRepository[AuthToken]):
    """Repository für Authentication Tokens."""
    
    def __init__(self):
        super().__init__("auth_tokens", AuthToken)
    
    def _row_to_model(self, row: RealDictRow) -> AuthToken:
        """Konvertiert DB-Row zu AuthToken Domain Model."""
        return AuthToken(
            id=row["id"],
            user_id=row["user_id"],
            token=row["token"],
            device=row.get("device"),
            expires_at=self._timestamp_to_datetime(row["expires_at"]) if row.get("expires_at") else None,
            created_at=self._timestamp_to_datetime(row["created_at"])
        )
    
    @staticmethod
    def _timestamp_to_datetime(timestamp: int) -> datetime:
        """Konvertiert Millisekunden-Timestamp zu datetime."""
        if timestamp > 10**12:
            return datetime.fromtimestamp(timestamp / 1000)
        return datetime.fromtimestamp(timestamp)
    
    def find_by_token(self, token: str) -> Optional[AuthToken]:
        """
        Sucht Token anhand des Token-Strings.
        
        Args:
            token: Token-String
        
        Returns:
            AuthToken oder None
        """
        return self.find_one_where("token = %s", (token,))
    
    def find_by_user_id(self, user_id: int) -> list[AuthToken]:
        """
        Gibt alle Tokens eines Users zurück.
        
        Args:
            user_id: User-ID
        
        Returns:
            Liste von AuthTokens
        """
        return self.find_where(
            "user_id = %s",
            (user_id,),
            order_by="created_at DESC"
        )
    
    def delete_by_token(self, token: str) -> bool:
        """
        Löscht Token anhand des Token-Strings.
        
        Args:
            token: Token-String
        
        Returns:
            True wenn gelöscht
        """
        from backend.core.database import get_db_cursor
        
        sql = f"DELETE FROM {self.table_name} WHERE token = %s"
        
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(sql, (token,))
                return cursor.rowcount > 0
        except Exception as e:
            from backend.core.exceptions import DatabaseError
            raise DatabaseError(f"Error deleting token: {str(e)}")
    
    def delete_by_user_id(self, user_id: int) -> int:
        """
        Löscht alle Tokens eines Users.
        
        Args:
            user_id: User-ID
        
        Returns:
            Anzahl gelöschter Tokens
        """
        from backend.core.database import get_db_cursor
        
        sql = f"DELETE FROM {self.table_name} WHERE user_id = %s"
        
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(sql, (user_id,))
                return cursor.rowcount
        except Exception as e:
            from backend.core.exceptions import DatabaseError
            raise DatabaseError(f"Error deleting tokens for user: {str(e)}")
