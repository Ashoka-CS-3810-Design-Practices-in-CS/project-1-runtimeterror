#converting between date time strings and whole minutes.
from datetime import datetime, timedelta

REFERENCE = datetime(2000, 1, 1)   
FORMAT = "%Y-%m-%dT%H:%M"         


def to_minutes(text: str) -> int:
    moment = datetime.strptime(text, FORMAT)
    return int((moment - REFERENCE).total_seconds() // 60)


def from_minutes(minutes: int) -> str:
    return (REFERENCE + timedelta(minutes=minutes)).strftime(FORMAT)


def clock_to_minutes(text: str) -> int:
    moment = datetime.strptime(text, "%H:%M")
    return moment.hour * 60 + moment.minute