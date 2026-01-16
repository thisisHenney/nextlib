import time
from datetime import datetime

def seconds_to_time(seconds: int) -> tuple[int, int, int, int]:
    if seconds < 0:
        raise ValueError("Seconds cannot be negative")

    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    return hours, minutes, secs

def get_date() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def get_time(msec: bool = True, show_split: bool = False) -> str:
    now = datetime.now()
    if not msec:
        return now.strftime("%H%M%S")

    if show_split:
        return now.strftime("%H:%M:%S.%f")[:9]  # HH:MM:SS.mmm
    else:
        return now.strftime("%H:%M:%S.%f")

def get_datetime(msec: bool = True) -> str:
    return f"{get_date()}_{get_time(msec)}"

def delay_time(second=0.1):
    time.sleep(second)
