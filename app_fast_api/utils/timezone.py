"""
Timezone utilities for Argentina (UTC-3)
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

# Argentina timezone (UTC-3)
ARGENTINA_TZ = timezone(timedelta(hours=-3))


def now_argentina() -> datetime:
    """
    Get current datetime in Argentina timezone.

    Returns:
        datetime: Current time in Argentina (UTC-3)
    """
    return datetime.now(ARGENTINA_TZ)


def to_argentina_tz(dt: Optional[datetime]) -> Optional[datetime]:
    """
    Convert datetime to Argentina timezone.

    Args:
        dt: Datetime to convert (can be naive or aware)

    Returns:
        datetime: Datetime in Argentina timezone, or None if input is None
    """
    if dt is None:
        return None

    # If naive, assume it's already in Argentina timezone (server timezone)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ARGENTINA_TZ)
        return dt

    # If timezone-aware, convert to Argentina timezone
    return dt.astimezone(ARGENTINA_TZ)


def format_argentina_datetime(dt: Optional[datetime], format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """
    Format datetime in Argentina timezone.

    Args:
        dt: Datetime to format
        format_str: strftime format string

    Returns:
        str: Formatted datetime string in Argentina time
    """
    if dt is None:
        return "N/A"

    argentina_dt = to_argentina_tz(dt)
    return argentina_dt.strftime(format_str)


def format_argentina_time(dt: Optional[datetime]) -> str:
    """
    Format time only (HH:MM:SS) in Argentina timezone.

    Args:
        dt: Datetime to format

    Returns:
        str: Formatted time string (HH:MM:SS)
    """
    return format_argentina_datetime(dt, '%H:%M:%S')


def format_argentina_date(dt: Optional[datetime]) -> str:
    """
    Format date only (YYYY-MM-DD) in Argentina timezone.

    Args:
        dt: Datetime to format

    Returns:
        str: Formatted date string (YYYY-MM-DD)
    """
    return format_argentina_datetime(dt, '%Y-%m-%d')


def to_argentina_isoformat(dt: Optional[datetime]) -> Optional[str]:
    """
    Convert datetime to Argentina timezone and return ISO format string.

    Args:
        dt: Datetime to convert (can be naive or aware)

    Returns:
        str: ISO format string with Argentina timezone, or None if input is None

    Example:
        >>> dt = datetime(2026, 2, 9, 8, 13, 5)  # UTC naive
        >>> to_argentina_isoformat(dt)
        '2026-02-09T05:13:05-03:00'
    """
    if dt is None:
        return None

    argentina_dt = to_argentina_tz(dt)
    return argentina_dt.isoformat()
