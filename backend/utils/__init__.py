"""
Utils Module - Utility Functions.
"""
from backend.utils.db_utils import (
    now_ms,
    timestamp_to_datetime,
    datetime_to_timestamp,
    sanitize_dict,
    chunk_list,
)
from backend.utils.avatar_generator import (
    get_initials,
    get_avatar_color,
    generate_avatar_jpeg,
    generate_avatar_data_uri,
    get_or_create_avatar,
)

__all__ = [
    "now_ms",
    "timestamp_to_datetime",
    "datetime_to_timestamp",
    "sanitize_dict",
    "chunk_list",
    "get_initials",
    "get_avatar_color",
    "generate_avatar_jpeg",
    "generate_avatar_data_uri",
    "get_or_create_avatar",
]
