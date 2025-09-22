from datetime import datetime, timedelta

def malaysia_now() -> datetime:
    """
    Return current Malaysia time as a datetime object (UTC +8).
    """
    return datetime.utcnow() + timedelta(hours=8)


def malaysia_time_str() -> str:
    """
    Return current Malaysia time as ISO string: 'YYYY-MM-DDTHH:MM:SS'
    """
    return malaysia_now().strftime("%Y-%m-%dT%H:%M:%S")


def add_8_hours(timestamp: str) -> str:
    """
    Add +8 hours to any ISO datetime string.
    Example: '2025-09-10T01:53:23' -> '2025-09-10T09:53:23'
    """
    dt = datetime.fromisoformat(timestamp)
    dt_plus_8 = dt + timedelta(hours=8)
    return dt_plus_8.strftime("%Y-%m-%dT%H:%M:%S")
