"""
Datenbank-Verbindung und Connection Pool Management.
"""
import logging
from contextlib import contextmanager
from typing import Generator, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool
from psycopg2.extensions import connection as PgConnection, cursor as PgCursor

from backend.core.config import get_settings
from backend.core.exceptions import DatabaseError

logger = logging.getLogger(__name__)


class DatabasePool:
    """
    Connection Pool Manager für PostgreSQL.
    Singleton Pattern für globale Pool-Verwaltung.
    """
    
    _instance: Optional["DatabasePool"] = None
    _pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def initialize(self) -> None:
        """Initialisiert den Connection Pool."""
        if self._pool is not None:
            logger.warning("Database pool already initialized")
            return
        
        settings = get_settings()
        
        try:
            # Konvertiere PostgresDsn zu String für psycopg2
            db_url = str(settings.database_url)
            
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=settings.db_pool_size,
                dsn=db_url,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            logger.info(
                f"Database pool initialized: "
                f"min=1, max={settings.db_pool_size}"
            )
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise DatabaseError(f"Database pool initialization failed: {str(e)}")
    
    def close(self) -> None:
        """Schließt den Connection Pool."""
        if self._pool:
            self._pool.closeall()
            self._pool = None
            logger.info("Database pool closed")
    
    @contextmanager
    def get_connection(self) -> Generator[PgConnection, None, None]:
        """
        Context Manager für Datenbank-Verbindungen.
        
        Yields:
            PostgreSQL Connection aus dem Pool
            
        Raises:
            DatabaseError: Bei Verbindungsproblemen
        """
        if self._pool is None:
            raise DatabaseError("Database pool not initialized")
        
        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            if conn:
                conn.rollback()
            raise DatabaseError(f"Database operation failed: {str(e)}")
        finally:
            if conn:
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, commit: bool = False) -> Generator[PgCursor, None, None]:
        """
        Context Manager für Datenbank-Cursor mit optionalem Auto-Commit.
        
        Args:
            commit: Wenn True, wird automatisch committed
            
        Yields:
            PostgreSQL Cursor
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
                if commit:
                    conn.commit()
            except Exception:
                conn.rollback()
                raise
            finally:
                cursor.close()


# Globale Pool-Instanz
_db_pool = DatabasePool()


def init_database_pool() -> None:
    """Initialisiert den globalen Database Pool."""
    _db_pool.initialize()


def close_database_pool() -> None:
    """Schließt den globalen Database Pool."""
    _db_pool.close()


def get_db_connection() -> Generator[PgConnection, None, None]:
    """
    Gibt eine Datenbank-Verbindung aus dem Pool zurück.
    
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ...")
    """
    return _db_pool.get_connection()


def get_db_cursor(commit: bool = False) -> Generator[PgCursor, None, None]:
    """
    Gibt einen Datenbank-Cursor zurück.
    
    Args:
        commit: Wenn True, wird automatisch committed
    
    Usage:
        with get_db_cursor(commit=True) as cursor:
            cursor.execute("INSERT ...")
    """
    return _db_pool.get_cursor(commit=commit)
