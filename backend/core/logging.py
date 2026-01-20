"""
Logging-Konfiguration für die gesamte Anwendung.
"""
import logging
import sys
from pathlib import Path
from typing import Optional

from backend.core.config import get_settings


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None
) -> None:
    """
    Konfiguriert das Logging für die Anwendung.
    
    Args:
        log_level: Log-Level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optionaler Pfad zu einer Log-Datei
    """
    settings = get_settings()
    
    level = log_level or settings.log_level
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Root Logger konfigurieren
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Entferne existierende Handler
    root_logger.handlers.clear()
    
    # Formatter
    formatter = logging.Formatter(
        fmt=settings.log_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # File Handler (optional)
    file_path = log_file or settings.log_file
    if file_path:
        log_path = Path(file_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Externe Libraries leiser machen
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging konfiguriert: Level={level}, File={file_path or 'None'}, "
        f"Environment={settings.environment}"
    )


def get_logger(name: str) -> logging.Logger:
    """
    Gibt einen Logger mit dem angegebenen Namen zurück.
    
    Args:
        name: Name des Loggers (üblicherweise __name__)
    
    Returns:
        Konfigurierter Logger
    """
    return logging.getLogger(name)
