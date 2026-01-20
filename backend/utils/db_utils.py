"""
Database Utilities - Helper functions for database operations.
"""
from datetime import datetime
from typing import Any


def now_ms() -> int:
    """
    Gibt aktuellen Timestamp in Millisekunden zurück.
    
    Returns:
        Timestamp in Millisekunden
    """
    return int(datetime.utcnow().timestamp() * 1000)


def timestamp_to_datetime(timestamp: int) -> datetime:
    """
    Konvertiert Timestamp (ms oder s) zu datetime.
    
    Args:
        timestamp: Timestamp in Millisekunden oder Sekunden
    
    Returns:
        datetime Objekt
    """
    if timestamp > 10**12:  # Millisekunden
        return datetime.fromtimestamp(timestamp / 1000)
    return datetime.fromtimestamp(timestamp)


def datetime_to_timestamp(dt: datetime) -> int:
    """
    Konvertiert datetime zu Timestamp in Millisekunden.
    
    Args:
        dt: datetime Objekt
    
    Returns:
        Timestamp in Millisekunden
    """
    return int(dt.timestamp() * 1000)


def sanitize_dict(data: dict[str, Any], remove_none: bool = True) -> dict[str, Any]:
    """
    Bereinigt Dictionary von None-Werten und leeren Strings.
    
    Args:
        data: Zu bereinigendes Dictionary
        remove_none: Entferne None-Werte
    
    Returns:
        Bereinigtes Dictionary
    """
    result = {}
    
    for key, value in data.items():
        if remove_none and value is None:
            continue
        if isinstance(value, str) and value == "":
            continue
        result[key] = value
    
    return result


def chunk_list(lst: list, chunk_size: int) -> list[list]:
    """
    Teilt Liste in Chunks auf.
    
    Args:
        lst: Liste
        chunk_size: Größe der Chunks
    
    Returns:
        Liste von Chunks
    """
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]
