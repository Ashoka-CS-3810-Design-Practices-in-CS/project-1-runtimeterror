import sqlite3
from datetime import datetime

import pytest

from app.controller.controller import Controller
from app.models.records import Event, Preferences, Task
from app.storage.sqlite_store import SQLiteStorage
from app.store.event_store import EventStore
from app.store.task_store import TaskStore

NOW = datetime(2026, 10, 20, 10, 0)


@pytest.fixture
def storage(tmp_path):                       # a temporary file, never real data
    s = SQLiteStorage(str(tmp_path / "test.db"))
    yield s
    s.close()


def make_event(event_id, start, **changes):
    fields = dict(id=event_id, title=f"e{event_id}", start=start, end=start + 60,
                  category="class", description="notes", location="Room 1",
                  priority="High", movable=False)
    fields.update(changes)
    return Event(**fields)


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


# ---------- the storage class on its own ----------

def test_event_round_trip(storage):
    a = make_event(1, 100)
    b = make_event(2, 200, priority=None, movable=True, description="", location="")
    storage.save_event(a)
    storage.save_event(b)
    assert storage.load_events() == [a, b]


def test_events_load_in_start_time_order(storage):
    for e in (make_event(1, 500), make_event(2, 100), make_event(3, 500)):
        storage.save_event(e)
    assert [e.id for e in storage.load_events()] == [2, 1, 3]


def test_saving_an_existing_id_replaces_it(storage):
    storage.save_event(make_event(1, 100))
    moved = make_event(1, 900)
    storage.save_event(moved)
    assert storage.load_events() == [moved]


def test_delete_event(storage):
    storage.save_event(make_event(1, 100))
    storage.delete_event(1)
    assert storage.load_events() == []


def test_task_round_trip_and_delete(storage):
    plain = Task(1, "Write", "assignment", 90, "High")
    windowed = Task(2, "Read", "personal", 30, "Low", from_date="2026-10-21",
                    to_date="2026-10-22", daily_start=540, daily_end=600)
    storage.save_task(plain)
    storage.save_task(windowed)
    assert storage.load_tasks() == [plain, windowed]
    storage.delete_task(1)
    assert storage.load_tasks() == [windowed]


def test_preferences_round_trip(storage):
    assert storage.load_preferences() is None
    prefs = Preferences(cutoff=22 * 60, cutoff_mode="Strict")
    prefs.preferred_time["personal"] = "morning"
    storage.save_preferences(prefs)
    assert storage.load_preferences() == prefs
    storage.save_preferences(Preferences())               # saving again replaces
    assert storage.load_preferences() == Preferences()


def test_booking_adds_the_event_and_removes_the_task(storage):
    storage.save_task(Task(1, "Write", "assignment", 60, "High"))
    event = make_event(1, 100)
    storage.save_booking(event, 1)
    assert storage.load_events() == [event]
    assert storage.load_tasks() == []


def test_start_time_index_exists(tmp_path):
    path = str(tmp_path / "idx.db")
    SQLiteStorage(path).close()
    db = sqlite3.connect(path)
    names = {row[0] for row in db.execute(
        "SELECT name FROM sqlite_master WHERE type = 'index'")}
    db.close()
    assert "idx_events_start" in names


# ---------- Controller + storage together (A3 "save and reload") ----------

def reopen(path):
    storage = SQLiteStorage(path)
    ctl = Controller(EventStore(), TaskStore(), clock=lambda: NOW)
    ctl.attach_storage(storage)
    return ctl, storage


def test_every_change_survives_a_restart(tmp_path):
    path = str(tmp_path / "app.db")
    ctl, storage = reopen(path)

    a = ctl.create_event(ev()).event
    b = ctl.create_event(ev(start="2026-10-21T12:00", end="2026-10-21T13:00")).event
    ctl.update_event(b.id, ev(start="2026-10-21T15:00", end="2026-10-21T16:00"))
    ctl.delete_event(a.id)
    ctl.create_task(task(name="stays"))
    booked = ctl.create_task(task(name="gets booked"))
    ctl.accept_slot(booked.id, {"start": "2026-10-22T09:00", "end": "2026-10-22T10:00"})
    ctl.set_preferences({"cutoff": "22:00"})
    storage.close()

    ctl2, storage2 = reopen(path)
    assert ctl2.events.all_sorted() == ctl.events.all_sorted()
    assert ctl2.tasks.by_priority() == ctl.tasks.by_priority()
    assert ctl2.get_preferences() == ctl.get_preferences()
    assert [t.name for t in ctl2.tasks.by_priority()] == ["stays"]
    # new ids carry on after the highest saved id
    new = ctl2.create_event(ev(start="2026-10-23T10:00", end="2026-10-23T11:00"))
    assert new.event.id == 4
    storage2.close()


def test_bulk_save_events(storage):
    events = [make_event(i, i * 100) for i in range(1, 51)]
    storage.save_events(events)
    assert storage.load_events() == events