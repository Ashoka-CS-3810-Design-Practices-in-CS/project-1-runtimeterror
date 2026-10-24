"""Sample inputs for the demo, the tests and the benchmarks.

Two kinds of calendar:
  * Named calendars (demo_events / demo_tasks): one hand-made case per day of a
    week, so every tricky situation can be shown on screen.
  * Seeded random calendars (random_events): the same seed always gives the
    same events, so tests and timings can be repeated.
"""
import random
from datetime import timedelta

from app.models.records import CATEGORIES, PRIORITIES, Event
from app.models.timeconv import to_minutes

MINUTES_PER_DAY = 24 * 60
RANDOM_FIRST_DAY = to_minutes("2026-10-01T00:00") // MINUTES_PER_DAY


# ----------------------------------------------------------------------
# Seeded random calendars (for tests and benchmarks)
# ----------------------------------------------------------------------

def random_events(n, seed, span_days=30, first_day=RANDOM_FIRST_DAY, max_duration=240):
    """
    n random events with ids 1..n, in creation order (NOT sorted by start).

    Every time is a multiple of 5 minutes, so touching and identical events
    happen often. About 3 in 100 events are long (10 to 24 hours), which
    exercises the 24-hour lookback in Algorithm 3.
    """
    rng = random.Random(seed)
    base = first_day * MINUTES_PER_DAY
    priorities = (*PRIORITIES, None)
    events = []
    for i in range(1, n + 1):
        start = base + 5 * rng.randrange(span_days * 288)       # 288 five-minute steps a day
        if rng.random() < 0.03:
            duration = 5 * rng.randrange(120, 289)               # 10h to 24h
        else:
            duration = 5 * rng.randrange(1, max_duration // 5 + 1)
        events.append(Event(
            id=i, title=f"Sample {i}", start=start, end=start + duration,
            category=rng.choice(CATEGORIES), priority=rng.choice(priorities)))
    return events


def sorted_by_start(events):
    return sorted(events, key=lambda e: (e.start, e.id))


# ----------------------------------------------------------------------
# The demo week (one case per day), written as API-style input
# ----------------------------------------------------------------------

def _event(title, category, day, start, end, end_day=None, priority=None,
           movable=None, location=""):
    data = {"title": title, "category": category, "location": location,
            "start": f"{day.isoformat()}T{start}",
            "end": f"{(end_day or day).isoformat()}T{end}"}
    if priority:
        data["priority"] = priority
    if movable is not None:
        data["movable"] = movable
    return data


def demo_events(monday):
    """
    monday: a datetime.date. Returns the demo events for that week.

      Mon  touching events        no conflict (half-open intervals)
      Tue  nested + identical     two conflicts of 60 minutes
      Wed  overnight              Night shift 23:00 to 01:00 overlaps a call at 00:30
      Thu  three at once          three pairs: 60, 30 and 60 minutes
      Fri  best-time worked example from Assignment 1 (section 5.4.3)
      Sat  Fixed class vs Movable study session (use cases UC1 and UC3)
    """
    mon, tue, wed, thu, fri, sat = (monday + timedelta(days=i) for i in range(6))
    return [
        # Monday: touching
        _event("Statistics Lecture", "class", mon, "10:00", "11:00", priority="High"),
        _event("Statistics Lab", "class", mon, "11:00", "12:00", priority="Medium"),

        # Tuesday: nested, then identical
        _event("Team Workshop", "meeting", tue, "09:00", "13:00", priority="Medium"),
        _event("Quick Call", "meeting", tue, "10:00", "11:00", priority="Low"),
        _event("Dentist", "appointment", tue, "16:00", "17:00", priority="High"),
        _event("Dentist (booked twice)", "appointment", tue, "16:00", "17:00"),

        # Wednesday to Thursday: overnight
        _event("Night Shift", "personal", wed, "23:00", "01:00", end_day=thu,
               priority="Medium"),
        _event("Late Call", "meeting", thu, "00:30", "02:00", priority="Low"),

        # Thursday: three events overlapping at once
        _event("Project A", "assignment", thu, "09:00", "11:00", priority="High"),
        _event("Project B", "assignment", thu, "10:00", "12:00", priority="Medium"),
        _event("Project C", "assignment", thu, "10:30", "11:30", priority="Low"),

        # Friday: the worked example (B and C overlap and merge into one busy block)
        _event("Advisor Check-in", "appointment", fri, "09:00", "09:30", priority="Medium"),
        _event("Seminar", "meeting", fri, "12:00", "13:00", priority="Medium"),
        _event("Reading Group", "meeting", fri, "12:30", "13:30", priority="Low"),
        _event("Gym", "personal", fri, "16:00", "17:00", priority="Low"),

        # Saturday: Fixed against Movable
        _event("Chemistry Class", "class", sat, "10:00", "11:30", priority="High",
               location="Lab 2"),
        _event("Study Session", "assignment", sat, "11:00", "12:00", priority="Medium"),
    ]


def demo_tasks(monday):
    """Flexible tasks. The first one is the Assignment 1 example (Friday, 90 minutes)."""
    friday = (monday + timedelta(days=4)).isoformat()
    return [
        {"name": "Write report", "category": "assignment", "duration_minutes": 90,
         "priority": "High", "from_date": friday, "to_date": friday,
         "daily_start": "09:00", "daily_end": "18:00"},
        {"name": "Read chapter 4", "category": "assignment", "duration_minutes": 45,
         "priority": "Medium"},
        {"name": "Call advisor", "category": "meeting", "duration_minutes": 30,
         "priority": "High"},
        {"name": "Evening walk", "category": "personal", "duration_minutes": 60,
         "priority": "Low"},
    ]