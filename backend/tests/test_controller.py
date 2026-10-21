from datetime import datetime

import pytest

from app.controller.controller import Controller
from app.controller.errors import NotFoundError, SlotTakenError, ValidationError
from app.models.records import Preferences
from app.models.timeconv import from_minutes, to_minutes
from app.store.event_store import EventStore
from app.store.task_store import TaskStore

NOW = datetime(2026, 10, 20, 10, 0)       # the frozen "now" for every test


@pytest.fixture
def ctl():
    return Controller(EventStore(), TaskStore(), clock=lambda: NOW)


def ev(**changes):
    data = {"title": "Meeting", "category": "meeting",
            "start": "2026-10-21T10:00", "end": "2026-10-21T11:00"}
    data.update(changes)
    return data


def task(**changes):
    data = {"name": "Write report", "category": "assignment",
            "duration_minutes": 60, "priority": "Medium"}
    data.update(changes)
    return data


# ---------- create ----------

def test_create_saves_in_both_structures(ctl):
    result = ctl.create_event(ev())
    assert ctl.events.get(result.event.id) == result.event
    assert [e.id for e in ctl.events.sorted_events()] == [result.event.id]
    assert result.conflicts == []


def test_t2_conflicting_event_is_saved_and_reported(ctl):
    lecture = ctl.create_event(ev(title="Lecture", category="class",
                                  start="2026-10-21T10:00", end="2026-10-21T11:30")).event
    result = ctl.create_event(ev(title="Group", priority="Medium",
                                 start="2026-10-21T11:00", end="2026-10-21T12:00"))
    assert len(ctl.events) == 2                       # saved anyway (A1)
    assert len(result.conflicts) == 1
    c = result.conflicts[0]
    assert (c.event_a.id, c.event_b.id) == (lecture.id, result.event.id)
    assert c.overlap_start == to_minutes("2026-10-21T11:00")
    assert c.overlap_end == to_minutes("2026-10-21T11:30")
    assert c.overlap_minutes == 30


def test_t1_touching_events_do_not_conflict(ctl):
    ctl.create_event(ev(start="2026-10-21T10:00", end="2026-10-21T11:00"))
    result = ctl.create_event(ev(start="2026-10-21T11:00", end="2026-10-21T12:00"))
    assert result.conflicts == []


def test_rejected_create_changes_nothing(ctl):
    with pytest.raises(ValidationError):
        ctl.create_event(ev(start="2026-10-21T14:00", end="2026-10-21T13:00"))
    assert len(ctl.events) == 0


# ---------- update (edit, move, resize) ----------

def test_move_clears_old_conflict_and_finds_new_one(ctl):
    a = ctl.create_event(ev()).event                                   # 10-11
    b = ctl.create_event(ev(start="2026-10-21T12:00", end="2026-10-21T13:00")).event

    moved = ctl.update_event(b.id, ev(start="2026-10-21T10:30", end="2026-10-21T11:30"))
    assert moved.event.id == b.id
    assert [(c.event_a.id, c.event_b.id) for c in moved.conflicts] == [(a.id, b.id)]

    back = ctl.update_event(b.id, ev(start="2026-10-21T12:00", end="2026-10-21T13:00"))
    assert back.conflicts == []
    starts = [e.start for e in ctl.events.sorted_events()]
    assert starts == sorted(starts) and len(ctl.events) == 2


def test_an_event_never_conflicts_with_itself(ctl):
    a = ctl.create_event(ev()).event
    assert ctl.update_event(a.id, ev()).conflicts == []


def test_rejected_update_keeps_the_original(ctl):
    a = ctl.create_event(ev()).event
    before = ctl.events.get(a.id)
    with pytest.raises(ValidationError):
        ctl.update_event(a.id, ev(title=""))
    assert ctl.events.get(a.id) == before


def test_update_or_delete_missing_event(ctl):                          # ER7
    with pytest.raises(NotFoundError) as info:
        ctl.update_event(99, ev())
    assert info.value.code == "ER7" and info.value.status == 404
    with pytest.raises(NotFoundError):
        ctl.delete_event(99)


# ---------- delete and list ----------

def test_delete_clears_the_conflict_for_the_other_event(ctl):
    ctl.create_event(ev())
    b = ctl.create_event(ev(start="2026-10-21T10:30", end="2026-10-21T11:30")).event
    _, conflicts = ctl.list_events("2026-10-21T00:00", "2026-10-22T00:00")
    assert len(conflicts) == 1

    ctl.delete_event(b.id)
    events, conflicts = ctl.list_events("2026-10-21T00:00", "2026-10-22T00:00")
    assert len(events) == 1 and conflicts == []


def test_list_events_only_returns_the_range(ctl):
    ctl.create_event(ev())
    ctl.create_event(ev(start="2026-10-25T10:00", end="2026-10-25T11:00"))
    events, _ = ctl.list_events("2026-10-21T00:00", "2026-10-22T00:00")
    assert len(events) == 1


def test_list_events_bad_range(ctl):
    with pytest.raises(ValidationError):
        ctl.list_events("2026-10-22T00:00", "2026-10-21T00:00")


# ---------- alternatives ----------

def test_alternatives_refuse_fixed_events(ctl):
    lecture = ctl.create_event(ev(category="class")).event
    with pytest.raises(ValidationError) as info:
        ctl.alternatives(lecture.id)
    assert info.value.message == "Fixed, cannot be moved by the planner"


def test_alternatives_for_a_movable_event(ctl):
    ctl.create_event(ev(title="Lecture", category="class"))             # 10-11 Fixed
    study = ctl.create_event(ev(title="Study", category="assignment",
                                start="2026-10-21T10:30", end="2026-10-21T11:30")).event
    result = ctl.alternatives(study.id)
    assert result.slots and all(s.end - s.start == 60 for s in result.slots)


# ---------- tasks ----------

def test_tasks_sorted_and_filtered_by_priority(ctl):
    ctl.create_task(task(name="low", priority="Low"))
    ctl.create_task(task(name="high", priority="High"))
    ctl.create_task(task(name="mid", priority="Medium"))
    assert [t.name for t in ctl.list_tasks()] == ["high", "mid", "low"]
    assert [t.name for t in ctl.list_tasks("All")] == ["high", "mid", "low"]
    assert [t.name for t in ctl.list_tasks("High")] == ["high"]
    with pytest.raises(ValidationError):
        ctl.list_tasks("Urgent")


def test_invalid_task_is_rejected_and_not_stored(ctl):
    with pytest.raises(ValidationError):
        ctl.create_task(task(duration_minutes=0))
    assert ctl.list_tasks() == []


def test_delete_missing_task(ctl):
    with pytest.raises(NotFoundError):
        ctl.delete_task(5)


# ---------- suggestions ----------

def test_suggestions_never_start_in_the_past(ctl):
    t = ctl.create_task(task())
    result = ctl.suggest(t.id)
    assert result.slots
    assert all(s.start >= to_minutes("2026-10-20T10:00") for s in result.slots)
    assert result.slots[0].start == to_minutes("2026-10-20T10:00")


def test_suggest_missing_task(ctl):
    with pytest.raises(NotFoundError):
        ctl.suggest(5)


def test_freed_time_appears_in_the_next_search(ctl):
    t = ctl.create_task(task(from_date="2026-10-21", to_date="2026-10-21",
                             daily_start="09:00", daily_end="10:00"))
    blocker = ctl.create_event(ev(start="2026-10-21T09:00", end="2026-10-21T10:00")).event
    assert ctl.suggest(t.id).slots == ()
    ctl.delete_event(blocker.id)
    assert len(ctl.suggest(t.id).slots) == 1


# ---------- accepting a slot ----------

def test_accept_books_the_event_and_removes_the_task(ctl):
    t = ctl.create_task(task())
    slot = ctl.suggest(t.id).slots[0]
    booking = ctl.accept_slot(t.id, {"start": from_minutes(slot.start),
                                     "end": from_minutes(slot.end)})
    assert booking.removed_task_id == t.id
    assert booking.event.title == "Write report"
    assert (booking.event.start, booking.event.end) == (slot.start, slot.end)
    assert booking.conflicts == []
    assert ctl.tasks.get(t.id) is None
    assert ctl.events.get(booking.event.id) == booking.event


def test_t9_slot_taken_in_the_meantime(ctl):
    t = ctl.create_task(task(duration_minutes=90, priority="High"))
    slot = ctl.suggest(t.id).slots[0]
    ctl.create_event(ev(title="Surprise", category="personal",
                        start=from_minutes(slot.start),
                        end=from_minutes(slot.start + 30)))
    events_before = len(ctl.events)

    with pytest.raises(SlotTakenError) as info:
        ctl.accept_slot(t.id, {"start": from_minutes(slot.start),
                               "end": from_minutes(slot.end)})
    assert info.value.status == 409
    assert ctl.tasks.get(t.id) is not None            # task stays in the list
    assert len(ctl.events) == events_before           # nothing was booked


def test_accept_slot_must_match_the_task_length(ctl):
    t = ctl.create_task(task(duration_minutes=60))
    with pytest.raises(ValidationError) as info:
        ctl.accept_slot(t.id, {"start": "2026-10-21T10:00", "end": "2026-10-21T10:30"})
    assert info.value.code == "ER2"
    assert ctl.tasks.get(t.id) is not None


def test_accept_for_missing_task(ctl):
    with pytest.raises(NotFoundError):
        ctl.accept_slot(7, {"start": "2026-10-21T10:00", "end": "2026-10-21T11:00"})


# ---------- preferences ----------

def test_preferences_default_then_update(ctl):
    assert ctl.get_preferences() == Preferences()
    updated = ctl.set_preferences({"cutoff": "22:00", "cutoff_mode": "Strict"})
    assert updated.cutoff == 22 * 60 and ctl.get_preferences().cutoff_mode == "Strict"


def test_invalid_preferences_change_nothing(ctl):
    with pytest.raises(ValidationError):
        ctl.set_preferences({"cutoff": "25:61"})
    assert ctl.get_preferences() == Preferences()


def test_saved_preferences_drive_the_finder(ctl):
    ctl.set_preferences({"cutoff_mode": "Strict", "cutoff": "10:00"})
    t = ctl.create_task(task(from_date="2026-10-21", to_date="2026-10-21",
                             daily_start="11:00", daily_end="13:00"))
    result = ctl.suggest(t.id)
    assert result.slots == () and "cutoff" in result.no_slot_reason