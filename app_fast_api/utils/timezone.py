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

    # If naive, assume it's UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    # Convert to Argentina timezone
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
