from datetime import date, datetime, timedelta

import pytest

from app.controller.controller import Controller
from app.controller.errors import ValidationError
from app.models.timeconv import to_minutes
from app.store.event_store import EventStore
from app.store.task_store import TaskStore
from samples.calendars import demo_events, demo_tasks, random_events
from samples.load_demo import default_monday, populate

MONDAY = date(2026, 10, 19)
NOW = datetime(2026, 10, 19, 8, 0)            


@pytest.fixture
def ctl():
    controller = Controller(EventStore(), TaskStore(), clock=lambda: NOW)
    populate(controller, MONDAY)
    return controller


def at(day_offset, clock):
    return f"{(MONDAY + timedelta(days=day_offset)).isoformat()}T{clock}"


def conflicts_between(ctl, start, end):
    events, conflicts = ctl.list_events(start, end)
    return events, conflicts


def minutes(conflicts):
    return sorted(c.overlap_minutes for c in conflicts)


def test_the_whole_demo_loads_without_a_validation_error(ctl):
    assert len(ctl.events) == len(demo_events(MONDAY))
    assert len(ctl.list_tasks()) == len(demo_tasks(MONDAY))


def test_monday_touching_events_do_not_conflict(ctl):
    events, conflicts = conflicts_between(ctl, at(0, "00:00"), at(1, "00:00"))
    assert len(events) == 2 and conflicts == []


def test_tuesday_nested_and_identical_events(ctl):
    events, conflicts = conflicts_between(ctl, at(1, "00:00"), at(2, "00:00"))
    assert len(events) == 4
    assert minutes(conflicts) == [60, 60]          


def test_wednesday_night_shift_overlaps_the_late_call_after_midnight(ctl):
    events, conflicts = conflicts_between(ctl, at(2, "23:00"), at(3, "03:00"))
    assert len(events) == 2 and len(conflicts) == 1
    conflict = conflicts[0]
    assert conflict.overlap_minutes == 30
    assert conflict.overlap_start == to_minutes(at(3, "00:30"))
    assert conflict.overlap_end == to_minutes(at(3, "01:00"))


def test_thursday_three_projects_overlap_at_once(ctl):
    events, conflicts = conflicts_between(ctl, at(3, "05:00"), at(4, "00:00"))
    assert len(events) == 3
    assert minutes(conflicts) == [30, 60, 60]


def test_friday_worked_example_gives_the_two_slots_from_assignment_1(ctl):
    task = next(t for t in ctl.list_tasks() if t.name == "Write report")
    slots = ctl.suggest(task.id).slots
    assert [(s.start, s.end) for s in slots] == [
        (to_minutes(at(4, "09:30")), to_minutes(at(4, "11:00"))),
        (to_minutes(at(4, "13:30")), to_minutes(at(4, "15:00"))),
    ]
    assert slots[0].matches_preferred is True and slots[1].matches_preferred is False


def test_saturday_fixed_class_against_movable_study_session(ctl):
    events, conflicts = conflicts_between(ctl, at(5, "00:00"), at(6, "00:00"))
    assert minutes(conflicts) == [30]
    by_title = {e.title: e for e in events}

    with pytest.raises(ValidationError):                      
        ctl.alternatives(by_title["Chemistry Class"].id)

    alternatives = ctl.alternatives(by_title["Study Session"].id).slots
    assert alternatives[0].start == to_minutes(at(5, "09:00"))  
    class_start, class_end = to_minutes(at(5, "10:00")), to_minutes(at(5, "11:30"))
    assert all(not (s.start < class_end and class_start < s.end) for s in alternatives)


def test_the_whole_week_has_eight_conflicts(ctl):
    _, conflicts = ctl.list_events(at(0, "00:00"), at(7, "00:00"))
    assert len(conflicts) == 8


def test_default_week_is_this_monday_or_next_monday_at_the_weekend():
    assert default_monday(date(2026, 10, 21)) == date(2026, 10, 19)  
    assert default_monday(date(2026, 10, 19)) == date(2026, 10, 19)    
    assert default_monday(date(2026, 10, 24)) == date(2026, 10, 26)    


def test_random_calendars_repeat_exactly_for_the_same_seed():
    assert random_events(100, seed=5) == random_events(100, seed=5)
    assert random_events(100, seed=5) != random_events(100, seed=6)


def test_random_events_respect_the_duration_limits():
    for event in random_events(2000, seed=1, span_days=30):
        assert 5 <= event.duration <= 24 * 60