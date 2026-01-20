"""
Database Migration Script.
Erstellt/Updated Datenbank-Schema.
"""
import logging
from pathlib import Path

from backend.core.config import get_settings
from backend.core.logging import setup_logging, get_logger
from backend.core.database import get_db_cursor

logger = get_logger(__name__)


def load_schema_sql() -> str:
    """Lädt SQL-Schema aus Datei."""
    schema_file = Path(__file__).parent.parent / "common" / "schema.py"
    
    if not schema_file.exists():
        raise FileNotFoundError(f"Schema file not found: {schema_file}")
    
    # Lese schema.py und extrahiere SCHEMA string
    with open(schema_file, 'r') as f:
        content = f.read()
    
    # Simple Extraktion des SCHEMA strings
    start = content.find('SCHEMA = """') + len('SCHEMA = """')
    end = content.find('"""', start)
    
    if start == -1 or end == -1:
        raise ValueError("Could not extract SCHEMA from schema.py")
    
    return content[start:end].strip()


def run_migration():
    """Führt Datenbank-Migration aus."""
    setup_logging()
    settings = get_settings()
    
    logger.info("=" * 60)
    logger.info("Starting Database Migration")
    logger.info(f"Database: {settings.database_url.host}/{settings.database_url.path}")
    logger.info("=" * 60)
    
    try:
        # Lade Schema
        logger.info("Loading schema...")
        schema_sql = load_schema_sql()
        
        # Führe Migration aus
        logger.info("Executing migration...")
        
        with get_db_cursor(commit=True) as cursor:
            # Aktiviere Foreign Keys
            cursor.execute("SET CONSTRAINTS ALL DEFERRED;")
            
            # Führe Schema aus (Split by statements)
            statements = [s.strip() for s in schema_sql.split(';') if s.strip()]
            
            for i, statement in enumerate(statements, 1):
                if not statement:
                    continue
                
                logger.debug(f"Executing statement {i}/{len(statements)}...")
                
                try:
                    cursor.execute(statement)
                except Exception as e:
                    logger.warning(f"Statement {i} failed (might already exist): {e}")
        
        logger.info("=" * 60)
        logger.info("✅ Migration completed successfully!")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    run_migration()
