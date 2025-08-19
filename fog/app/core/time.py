"""
Time utilities for fog service
"""

import time
from datetime import datetime, timezone
from typing import Optional


def get_current_timestamp() -> float:
    """Get current timestamp in seconds"""
    return time.time()


def get_current_iso_timestamp() -> str:
    """Get current timestamp in ISO format"""
    return datetime.now(timezone.utc).isoformat()


def parse_iso_timestamp(timestamp_str: str) -> Optional[float]:
    """
    Parse ISO timestamp string to seconds
    
    Args:
        timestamp_str: ISO timestamp string
        
    Returns:
        Timestamp in seconds or None if invalid
    """
    try:
        dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        return dt.timestamp()
    except (ValueError, TypeError):
        return None


def is_timestamp_valid(timestamp_str: str, window_seconds: int = 120) -> bool:
    """
    Check if timestamp is within valid window
    
    Args:
        timestamp_str: ISO timestamp string
        window_seconds: Allowed time window in seconds
        
    Returns:
        True if timestamp is valid
    """
    timestamp = parse_iso_timestamp(timestamp_str)
    if timestamp is None:
        return False
    
    current_time = get_current_timestamp()
    time_diff = abs(current_time - timestamp)
    
    return time_diff <= window_seconds


def get_timestamp_age(timestamp_str: str) -> Optional[float]:
    """
    Get age of timestamp in seconds
    
    Args:
        timestamp_str: ISO timestamp string
        
    Returns:
        Age in seconds or None if invalid
    """
    timestamp = parse_iso_timestamp(timestamp_str)
    if timestamp is None:
        return None
    
    current_time = get_current_timestamp()
    return current_time - timestamp