"""
Base Repository mit generischen CRUD-Operationen.
"""
from abc import ABC, abstractmethod
from typing import Any, Generic, Optional, TypeVar, Type
from datetime import datetime

from psycopg2.extras import RealDictRow

from backend.core.database import get_db_cursor
from backend.core.exceptions import DatabaseError, ResourceNotFoundError

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """
    Abstract Base Repository mit generischen CRUD-Operationen.
    
    Alle Repositories erben von dieser Klasse und implementieren
    spezifische Business-Logik für ihre Entity.
    """
    
    def __init__(self, table_name: str, model_class: Type[T]):
        """
        Initialisiert das Repository.
        
        Args:
            table_name: Name der Datenbank-Tabelle
            model_class: Domain Model Klasse für Type-Mapping
        """
        self.table_name = table_name
        self.model_class = model_class
    
    @abstractmethod
    def _row_to_model(self, row: RealDictRow) -> T:
        """
        Konvertiert eine Datenbank-Row zum Domain Model.
        Muss in Subklassen implementiert werden.
        
        Args:
            row: Datenbank-Row (RealDictRow)
        
        Returns:
            Domain Model Instanz
        """
        pass
    
    def _model_to_dict(self, model: T) -> dict[str, Any]:
        """
        Konvertiert Domain Model zu Dict für DB-Insert/Update.
        Kann in Subklassen überschrieben werden.
        
        Args:
            model: Domain Model Instanz
        
        Returns:
            Dictionary mit DB-Feldern
        """
        if hasattr(model, "__dict__"):
            data = {k: v for k, v in model.__dict__.items() if not k.startswith("_")}
            # Konvertiere datetime zu int (milliseconds)
            for key, value in data.items():
                if isinstance(value, datetime):
                    data[key] = int(value.timestamp() * 1000)
            return data
        return {}
    
    def find_by_id(self, entity_id: int) -> Optional[T]:
        """
        Sucht Entity anhand der ID.
        
        Args:
            entity_id: ID der Entity
        
        Returns:
            Domain Model oder None
        """
        sql = f"SELECT * FROM {self.table_name} WHERE id = %s"
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute(sql, (entity_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_model(row)
                return None
        except Exception as e:
            raise DatabaseError(f"Error finding {self.table_name} by id: {str(e)}")
    
    def find_all(
        self,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        order_by: str = "id DESC"
    ) -> list[T]:
        """
        Gibt alle Entities zurück.
        
        Args:
            limit: Maximale Anzahl Ergebnisse
            offset: Offset für Pagination
            order_by: Sortierung (z.B. "created_at DESC")
        
        Returns:
            Liste von Domain Models
        """
        sql = f"SELECT * FROM {self.table_name} ORDER BY {order_by}"
        params: list[Any] = []
        
        if limit:
            sql += " LIMIT %s"
            params.append(limit)
        
        if offset:
            sql += " OFFSET %s"
            params.append(offset)
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Error finding all {self.table_name}: {str(e)}")
    
    def create(self, data: dict[str, Any]) -> T:
        """
        Erstellt eine neue Entity.
        
        Args:
            data: Daten für die neue Entity
        
        Returns:
            Erstelltes Domain Model
        """
        keys = ", ".join(data.keys())
        placeholders = ", ".join(["%s"] * len(data))
        sql = f"INSERT INTO {self.table_name} ({keys}) VALUES ({placeholders}) RETURNING *"
        
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(sql, list(data.values()))
                row = cursor.fetchone()
                
                if not row:
                    raise DatabaseError(f"Failed to create {self.table_name}")
                
                return self._row_to_model(row)
        except Exception as e:
            raise DatabaseError(f"Error creating {self.table_name}: {str(e)}")
    
    def update(self, entity_id: int, data: dict[str, Any]) -> Optional[T]:
        """
        Aktualisiert eine Entity.
        
        Args:
            entity_id: ID der Entity
            data: Zu aktualisierende Felder
        
        Returns:
            Aktualisiertes Domain Model oder None
        """
        if not data:
            return self.find_by_id(entity_id)
        
        # updated_at automatisch setzen
        data["updated_at"] = int(datetime.utcnow().timestamp() * 1000)
        
        sets = ", ".join([f"{k} = %s" for k in data.keys()])
        sql = f"UPDATE {self.table_name} SET {sets} WHERE id = %s RETURNING *"
        
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(sql, list(data.values()) + [entity_id])
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_model(row)
                return None
        except Exception as e:
            raise DatabaseError(f"Error updating {self.table_name}: {str(e)}")
    
    def delete(self, entity_id: int) -> bool:
        """
        Löscht eine Entity.
        
        Args:
            entity_id: ID der Entity
        
        Returns:
            True wenn gelöscht, False wenn nicht gefunden
        """
        sql = f"DELETE FROM {self.table_name} WHERE id = %s"
        
        try:
            with get_db_cursor(commit=True) as cursor:
                cursor.execute(sql, (entity_id,))
                return cursor.rowcount > 0
        except Exception as e:
            raise DatabaseError(f"Error deleting {self.table_name}: {str(e)}")
    
    def exists(self, entity_id: int) -> bool:
        """
        Prüft ob Entity existiert.
        
        Args:
            entity_id: ID der Entity
        
        Returns:
            True wenn existiert
        """
        sql = f"SELECT 1 FROM {self.table_name} WHERE id = %s"
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute(sql, (entity_id,))
                return cursor.fetchone() is not None
        except Exception as e:
            raise DatabaseError(f"Error checking existence of {self.table_name}: {str(e)}")
    
    def count(self, where: Optional[str] = None, params: Optional[tuple] = None) -> int:
        """
        Zählt Entities.
        
        Args:
            where: Optional WHERE-Klausel
            params: Parameter für WHERE-Klausel
        
        Returns:
            Anzahl der Entities
        """
        sql = f"SELECT COUNT(*) as count FROM {self.table_name}"
        
        if where:
            sql += f" WHERE {where}"
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute(sql, params or ())
                result = cursor.fetchone()
                return result["count"] if result else 0
        except Exception as e:
            raise DatabaseError(f"Error counting {self.table_name}: {str(e)}")
    
    def find_where(
        self,
        where: str,
        params: tuple,
        limit: Optional[int] = None,
        order_by: str = "id DESC"
    ) -> list[T]:
        """
        Sucht Entities mit WHERE-Bedingung.
        
        Args:
            where: WHERE-Klausel (ohne WHERE keyword)
            params: Parameter für WHERE-Klausel
            limit: Maximale Anzahl Ergebnisse
            order_by: Sortierung
        
        Returns:
            Liste von Domain Models
        """
        sql = f"SELECT * FROM {self.table_name} WHERE {where} ORDER BY {order_by}"
        
        if limit:
            sql += f" LIMIT {limit}"
        
        try:
            with get_db_cursor() as cursor:
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [self._row_to_model(row) for row in rows]
        except Exception as e:
            raise DatabaseError(f"Error finding {self.table_name} where {where}: {str(e)}")
    
    def find_one_where(self, where: str, params: tuple) -> Optional[T]:
        """
        Sucht eine Entity mit WHERE-Bedingung.
        
        Args:
            where: WHERE-Klausel (ohne WHERE keyword)
            params: Parameter für WHERE-Klausel
        
        Returns:
            Domain Model oder None
        """
        results = self.find_where(where, params, limit=1)
        return results[0] if results else None
