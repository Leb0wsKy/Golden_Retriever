"""
General helper functions.

Common utility functions used throughout the application.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


def generate_id(prefix: str = None) -> str:
    """
    Generate a unique identifier.
    
    Args:
        prefix: Optional prefix for the ID.
        
    Returns:
        Unique string identifier.
    """
    unique_id = str(uuid.uuid4())
    if prefix:
        return f"{prefix}-{unique_id[:8]}"
    return unique_id


def format_timestamp(dt: datetime = None, format_str: str = None) -> str:
    """
    Format a datetime to ISO string.
    
    Args:
        dt: Datetime to format (defaults to now).
        format_str: Optional custom format string.
        
    Returns:
        Formatted timestamp string.
    """
    dt = dt or datetime.utcnow()
    if format_str:
        return dt.strftime(format_str)
    return dt.isoformat() + "Z"


def chunk_list(items: List[Any], chunk_size: int) -> List[List[Any]]:
    """
    Split a list into chunks of specified size.
    
    Args:
        items: List to chunk.
        chunk_size: Size of each chunk.
        
    Returns:
        List of chunks.
    """
    return [
        items[i:i + chunk_size]
        for i in range(0, len(items), chunk_size)
    ]


def deep_merge(base: Dict, override: Dict) -> Dict:
    """
    Deep merge two dictionaries.
    
    Args:
        base: Base dictionary.
        override: Dictionary with override values.
        
    Returns:
        Merged dictionary.
    """
    result = base.copy()
    
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def safe_get(data: Dict, *keys, default: Any = None) -> Any:
    """
    Safely get nested dictionary value.
    
    Args:
        data: Dictionary to search.
        *keys: Keys to traverse.
        default: Default value if not found.
        
    Returns:
        Value at nested path or default.
    """
    result = data
    
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
        else:
            return default
        
        if result is None:
            return default
    
    return result


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.
    
    Args:
        text: Text to truncate.
        max_length: Maximum length including suffix.
        suffix: Suffix to add if truncated.
        
    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix
