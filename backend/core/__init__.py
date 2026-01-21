"""
Core-Modul mit zentralen Komponenten.
"""
from backend.core.config import get_settings, settings
from backend.core.logging import setup_logging, get_logger

__all__ = [
    "get_settings",
    "settings",
    "setup_logging",
    "get_logger",
]
