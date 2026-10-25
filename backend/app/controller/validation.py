
import calendar
from datetime import date, timedelta

from app.controller.errors import ValidationError
from app.models.records import (
    CATEGORIES, CUTOFF_MODES, MAX_DURATION, MIN_DURATION, PRIORITIES,
    TIMES_OF_DAY, Event, Preferences, Task,
)
from app.models.timeconv import REFERENCE, clock_to_minutes, from_minutes, to_minutes

MINUTES_PER_DAY = 24 * 60
TIME_FORMAT_HINT = "Use the format YYYY-MM-DDTHH:MM, for example 2026-10-13T10:00."
RANGE_DETAIL = "Dates must be within 6 months before and 1 year after today."

def validate_event(data, today):
    title = data.get("title")
    if not isinstance(title, str) or not title.strip():
        raise ValidationError("ER4", "title", "Title is required",
                              "Title cannot be empty.")

    category = data.get("category")
    if category not in CATEGORIES:
        raise ValidationError("ER4", "category", "Invalid category",
                              f"Category must be one of: {', '.join(CATEGORIES)}.")

    priority = data.get("priority")
    if priority is not None and priority not in PRIORITIES:
        raise ValidationError("ER4", "priority", "Invalid priority",
                              "Priority must be High, Medium, Low, or not set.")

    movable = data.get("movable")
    if movable is not None and not isinstance(movable, bool):
        raise ValidationError("ER4", "movable", "Invalid Movable setting",
                              "Choose Movable or Fixed.")

    description = _text(data, "description")
    location = _text(data, "location")

    start = parse_time(data.get("start"), "start")
    end = parse_time(data.get("end"), "end")
    if end <= start:
        raise ValidationError("ER1", "end", "Invalid end time",
                              "End time must be after start time.")

    if not MIN_DURATION <= end - start <= MAX_DURATION:
        raise ValidationError("ER2", "end", "Invalid duration",
                              "Events must be between 5 minutes and 24 hours long.")

    _check_in_range(start, "start", today)    # only the start day counts

    return Event(id=None, title=title.strip(), start=start, end=end,
                 category=category, description=description, location=location,
                 priority=priority, movable=movable)


def validate_task(data, prefs, today):
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("ER4", "name", "Name is required",
                              "Task name cannot be empty.")

    category = data.get("category")
    if category not in CATEGORIES:
        raise ValidationError("ER4", "category", "Invalid category",
                              f"Category must be one of: {', '.join(CATEGORIES)}.")

    priority = data.get("priority")
    if priority not in PRIORITIES:          
        raise ValidationError("ER4", "priority", "Priority is required",
                              "Choose High, Medium or Low.")

    duration = data.get("duration_minutes")
    if (isinstance(duration, bool) or not isinstance(duration, int)
            or not MIN_DURATION <= duration <= MAX_DURATION):
        raise ValidationError("ER5", "duration_minutes", "Invalid duration",
                              "Tasks must be between 5 minutes and 24 hours long.")

    from_date = _parse_date(data.get("from_date"), "from_date", today)
    to_date = _parse_date(data.get("to_date"), "to_date", today)
    if from_date and to_date and _day_number(to_date) < _day_number(from_date):
        raise ValidationError("ER5", "to_date", "Invalid window",
                              "The last date must not be before the first date.")

    daily_start = _parse_clock(data.get("daily_start"), "daily_start", "ER5")
    daily_end = _parse_clock(data.get("daily_end"), "daily_end", "ER5")

    window_start = daily_start if daily_start is not None else prefs.working_start
    window_end = daily_end if daily_end is not None else prefs.working_end
    if window_end <= window_start:
        raise ValidationError("ER5", "daily_end", "Invalid window",
                              "The daily end time must be after the daily start time.")
    window_length = window_end - window_start
    if duration > window_length:
        raise ValidationError(
            "ER5", "duration_minutes", "Task does not fit the window",
            f"Your window is {window_length} minutes, but the task needs "
            f"{duration}. Shorten the task or widen the window.")


    return Task(id=None, name=name.strip(), category=category, duration=duration,
                priority=priority, from_date=from_date, to_date=to_date,
                daily_start=daily_start, daily_end=daily_end)

def validate_preferences(data):
    defaults = Preferences()

    preferred = dict(defaults.preferred_time)
    given = data.get("preferred_time", {})
    if not isinstance(given, dict):
        raise _er8("preferred_time", "Invalid preferred times",
                   "Preferred times must be given per category.")
    for category, time_of_day in given.items():
        if category not in CATEGORIES or time_of_day not in TIMES_OF_DAY:
            raise _er8("preferred_time", "Invalid preferred time",
                       "Use morning, afternoon or night for each category.")
        preferred[category] = time_of_day

    cutoff = defaults.cutoff
    if "cutoff" in data:
        cutoff = _parse_clock(data["cutoff"], "cutoff", "ER8", required=True)

    cutoff_mode = data.get("cutoff_mode", defaults.cutoff_mode)
    if cutoff_mode not in CUTOFF_MODES:
        raise _er8("cutoff_mode", "Invalid cutoff mode", "Choose Flexible or Strict.")

    working_start, working_end = defaults.working_start, defaults.working_end
    hours = data.get("working_hours", {})
    if not isinstance(hours, dict):
        raise _er8("working_hours", "Invalid working hours",
                   "Give a start and an end time.")
    if "start" in hours:
        working_start = _parse_clock(hours["start"], "working_hours", "ER8", required=True)
    if "end" in hours:
        working_end = _parse_clock(hours["end"], "working_hours", "ER8", required=True)
    if working_end <= working_start:
        raise _er8("working_hours", "Invalid working hours",
                   "Working hours must end after they start.")

    return Preferences(preferred_time=preferred, cutoff=cutoff,
                       cutoff_mode=cutoff_mode, working_start=working_start,
                       working_end=working_end)


def _er8(field, message, detail):
    return ValidationError("ER8", field, message, detail)

def supported_date_range(today):
    return _shift_months(today, -6), _shift_months(today, 12)


def _shift_months(day, months):
    year, month_index = divmod(day.year * 12 + (day.month - 1) + months, 12)
    month = month_index + 1
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(day.day, last_day))   # Feb 29 -> Feb 28 etc.


def _check_in_range(minutes, field, today):
    day = REFERENCE.date() + timedelta(days=minutes // MINUTES_PER_DAY)
    low, high = supported_date_range(today)
    if not low <= day <= high:
        raise ValidationError("ER3", field, "Date out of range", RANGE_DETAIL)


def parse_time(value, field):
    try:
        return to_minutes(value)
    except (ValueError, TypeError):
        raise ValidationError("ER1", field, f"Invalid {field} time",
                              f"Could not read the {field} time. {TIME_FORMAT_HINT}") from None


def _parse_date(value, field, today):
    if value is None:
        return None
    try:
        minutes = to_minutes(f"{value}T00:00")
    except (ValueError, TypeError):
        raise ValidationError("ER5", field, "Invalid date",
                              "Use the format YYYY-MM-DD, for example 2026-10-16.") from None
    _check_in_range(minutes, field, today)
    return from_minutes(minutes)[:10]


def _day_number(date_text):
    return to_minutes(f"{date_text}T00:00") // MINUTES_PER_DAY


def _parse_clock(value, field, code, required=False):
    if value is None and not required:
        return None
    try:
        return clock_to_minutes(value)
    except (ValueError, TypeError):
        raise ValidationError(code, field, "Invalid time",
                              "Use the format HH:MM, for example 21:00.") from None


def _text(data, field):
    value = data.get(field)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError("ER4", field, f"Invalid {field}",
                              f"The {field} must be text.")
    return value