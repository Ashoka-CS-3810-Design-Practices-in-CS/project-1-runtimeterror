#converting between date time strings and whole minutes so comparison easier
from datetime import datetime, timedelta

REFERENCE = datetime(2000, 1, 1)   
FORMAT = "%Y-%m-%dT%H:%M"         
#number is minutes since 1 jan 2000

def to_minutes(text: str) -> int:
    moment = datetime.strptime(text, FORMAT)
    return int((moment - REFERENCE).total_seconds() // 60)

#reverse so api can send back orret time
def from_minutes(minutes: int) -> str:
    return (REFERENCE + timedelta(minutes=minutes)).strftime(FORMAT)


def clock_to_minutes(text: str) -> int:
    moment = datetime.strptime(text, "%H:%M")
    return moment.hour * 60 + moment.minute