from datetime import date

import pytest

from app.controller.errors import ValidationError
from app.controller.validation import (
    supported_date_range, validate_event, validate_preferences, validate_task,
)
from app.models.records import Preferences
from app.models.timeconv import to_minutes

TODAY = date(2026, 10, 20)

def event_data(**changes):
    data = {"title": "Group Project Meeting", "category": "meeting",
            "start": "2026-10-21T11:00", "end": "2026-10-21T12:00"}
    data.update(changes)
    return data

def task_data(**changes):
    data = {"name": "Write report", "category": "assignment",
            "duration_minutes": 90, "priority": "High"}
    data.update(changes)
    return data


def rejected(fn, *args):
    with pytest.raises(ValidationError) as info:
        fn(*args)
    return info.value

def test_supported_date_range():
    assert supported_date_range(TODAY) == (date(2026, 4, 20), date(2027, 10, 20))
    assert supported_date_range(date(2028, 2, 29)) == (date(2027, 8, 29), date(2029, 2, 28))



def test_valid_event_becomes_a_record():
    event = validate_event(event_data(priority="Medium"), TODAY)
    assert event.id is None
    assert event.start == to_minutes("2026-10-21T11:00")
    assert event.end == to_minutes("2026-10-21T12:00")
    assert event.priority == "Medium"
    assert event.movable is False                    


def test_movable_default_and_override():
    assert validate_event(event_data(category="assignment"), TODAY).movable is True
    assert validate_event(event_data(movable=True), TODAY).movable is True


def test_title_is_trimmed_and_priority_optional():
    event = validate_event(event_data(title="  Lab  "), TODAY)
    assert event.title == "Lab" and event.priority is None

@pytest.mark.parametrize("changes, field", [
    ({"title": ""}, "title"),
    ({"title": "   "}, "title"),
    ({"title": None}, "title"),
    ({"category": "party"}, "category"),
    ({"priority": "Urgent"}, "priority"),
    ({"movable": "yes"}, "movable"),
    ({"description": 5}, "description"),
])
def test_er4_bad_fields(changes, field):
    err = rejected(validate_event, event_data(**changes), TODAY)
    assert (err.code, err.field) == ("ER4", field)

@pytest.mark.parametrize("changes, field", [
    ({"start": "2026-10-21T25:70"}, "start"),
    ({"end": "tomorrow"}, "end"),
    ({"start": None}, "start"),
    ({"end": "2026-10-21T11:00"}, "end"),           
    ({"end": "2026-10-21T10:00"}, "end"),            
])
def test_er1_bad_times(changes, field):
    err = rejected(validate_event, event_data(**changes), TODAY)
    assert (err.code, err.field) == ("ER1", field)


def test_t7_end_before_start_message():
    err = rejected(validate_event,
                   event_data(start="2026-10-21T14:00", end="2026-10-21T13:00"), TODAY)
    assert err.detail == "End time must be after start time."


@pytest.mark.parametrize("end, ok", [
    ("2026-10-21T11:04", False),    
    ("2026-10-21T11:05", True),     
    ("2026-10-22T11:00", True),      
    ("2026-10-22T11:01", False),    
])
def test_er2_duration_limits(end, ok):
    if ok:
        assert validate_event(event_data(end=end), TODAY).end == to_minutes(end)
    else:
        err = rejected(validate_event, event_data(end=end), TODAY)
        assert (err.code, err.field) == ("ER2", "end")
        assert err.detail == "Events must be between 5 minutes and 24 hours long."

@pytest.mark.parametrize("start, end, ok", [
    ("2026-04-20T10:00", "2026-04-20T11:00", True),    
    ("2026-04-19T10:00", "2026-04-19T11:00", False),   
    ("2027-10-20T10:00", "2027-10-20T11:00", True),    
    ("2027-10-21T10:00", "2027-10-21T11:00", False),   
    ("2027-10-20T23:00", "2027-10-21T01:00", True),    
])
def test_er3_date_range(start, end, ok):
    data = event_data(start=start, end=end)
    if ok:
        assert validate_event(data, TODAY).start == to_minutes(start)
    else:
        err = rejected(validate_event, data, TODAY)
        assert (err.code, err.field) == ("ER3", "start")

def test_valid_task_without_a_window_keeps_none():
    task = validate_task(task_data(), Preferences(), TODAY)
    assert (task.name, task.duration, task.priority) == ("Write report", 90, "High")
    assert (task.from_date, task.to_date, task.daily_start, task.daily_end) == (None,) * 4


def test_valid_task_with_a_window():
    task = validate_task(task_data(from_date="2026-10-16", to_date="2026-10-17",
                                   daily_start="09:00", daily_end="18:00"),
                         Preferences(), TODAY)
    assert (task.from_date, task.to_date) == ("2026-10-16", "2026-10-17")
    assert (task.daily_start, task.daily_end) == (540, 1080)


@pytest.mark.parametrize("changes, field", [
    ({"name": ""}, "name"),
    ({"category": "party"}, "category"),
    ({"priority": None}, "priority"),           
    ({"priority": "Urgent"}, "priority"),
])
def test_task_er4(changes, field):
    err = rejected(validate_task, task_data(**changes), Preferences(), TODAY)
    assert (err.code, err.field) == ("ER4", field)


@pytest.mark.parametrize("duration", [0, -5, 4, 1441, "90", True, 90.0])
def test_task_er5_bad_duration(duration):
    err = rejected(validate_task, task_data(duration_minutes=duration),
                   Preferences(), TODAY)
    assert (err.code, err.field) == ("ER5", "duration_minutes")


def test_task_er5_window_ends_before_it_starts():
    err = rejected(validate_task,
                   task_data(daily_start="18:00", daily_end="09:00"),
                   Preferences(), TODAY)
    assert (err.code, err.field) == ("ER5", "daily_end")


def test_task_er5_window_shorter_than_task():
    err = rejected(validate_task,
                   task_data(daily_start="09:00", daily_end="10:00"),
                   Preferences(), TODAY)
    assert (err.code, err.field) == ("ER5", "duration_minutes")
    assert err.detail == ("Your window is 60 minutes, but the task needs 90. "
                          "Shorten the task or widen the window.")


def test_task_window_falls_back_to_working_hours():
    prefs = Preferences(working_start=9 * 60, working_end=10 * 60)
    err = rejected(validate_task, task_data(), prefs, TODAY)
    assert err.field == "duration_minutes"


def test_task_er5_last_date_before_first():
    err = rejected(validate_task,
                   task_data(from_date="2026-10-18", to_date="2026-10-16"),
                   Preferences(), TODAY)
    assert (err.code, err.field) == ("ER5", "to_date")


def test_task_bad_and_out_of_range_dates():
    err = rejected(validate_task, task_data(from_date="2026-13-45"),
                   Preferences(), TODAY)
    assert (err.code, err.field) == ("ER5", "from_date")
    err = rejected(validate_task, task_data(to_date="2030-01-01"),
                   Preferences(), TODAY)
    assert (err.code, err.field) == ("ER3", "to_date")

def test_empty_preferences_give_the_defaults():
    assert validate_preferences({}) == Preferences()


def test_valid_preferences():
    prefs = validate_preferences({
        "preferred_time": {"personal": "morning"},
        "cutoff": "22:30", "cutoff_mode": "Strict",
        "working_hours": {"start": "08:00", "end": "17:00"},
    })
    assert prefs.preferred_time["personal"] == "morning"
    assert prefs.preferred_time["meeting"] == "morning"    
    assert prefs.cutoff == 22 * 60 + 30
    assert prefs.cutoff_mode == "Strict"
    assert (prefs.working_start, prefs.working_end) == (480, 1020)


@pytest.mark.parametrize("data, field", [
    ({"cutoff": "25:61"}, "cutoff"),
    ({"cutoff": "nine pm"}, "cutoff"),
    ({"cutoff": None}, "cutoff"),
    ({"cutoff_mode": "Soft"}, "cutoff_mode"),
    ({"preferred_time": {"meeting": "dawn"}}, "preferred_time"),
    ({"preferred_time": {"party": "morning"}}, "preferred_time"),
    ({"working_hours": {"start": "18:00", "end": "09:00"}}, "working_hours"),
])
def test_er8_bad_preferences(data, field):
    err = rejected(validate_preferences, data)
    assert (err.code, err.field) == ("ER8", field)


def test_error_to_dict_matches_the_contract():
    err = rejected(validate_event, event_data(title=""), TODAY)
    assert err.status == 422
    assert set(err.to_dict()["error"]) == {"code", "field", "message", "detail"}