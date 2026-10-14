#unit tests for the stores

"""what is being tsted is that after any sequence of inserts, edits and deletes,
the sorted array must still be in start time order and must contain
exactly the same event ids as the hash map.
"""
import random
from dataclasses import replace

import pytest

from app.models.records import Event, Task
from app.models.timeconv import to_minutes
from app.store.event_store import EventStore
from app.store.task_store import TaskStore


def make_event(start_text, end_text, title="E", category="meeting"):
    return Event(id=None, title=title, start=to_minutes(start_text),
                 end=to_minutes(end_text), category=category)


def check_invariants(store: EventStore):
    events = store.all_sorted()
    starts = [(e.start, e.id) for e in events]
    assert starts == sorted(starts), "sorted array is out of order"
    assert {e.id for e in events} == set(store._by_id), "DS1 and DS2 disagree"


def test_movable_default_comes_from_category():
    assert make_event("2026-10-13T10:00", "2026-10-13T11:00", category="class").movable is False
    assert make_event("2026-10-13T10:00", "2026-10-13T11:00", category="assignment").movable is True


def test_events_cannot_be_changed_in_place():
    event = make_event("2026-10-13T10:00", "2026-10-13T11:00")
    with pytest.raises(Exception):
        event.start = 0          

def test_add_assigns_ids_and_keeps_order():
    store = EventStore()
    late = store.add(make_event("2026-10-13T15:00", "2026-10-13T16:00"))
    early = store.add(make_event("2026-10-13T09:00", "2026-10-13T10:00"))
    assert (late.id, early.id) == (1, 2)
    assert [e.id for e in store.all_sorted()] == [2, 1]   
    assert store.get(1) is late
    check_invariants(store)


def test_remove():
    store = EventStore()
    a = store.add(make_event("2026-10-13T09:00", "2026-10-13T10:00"))
    b = store.add(make_event("2026-10-13T09:00", "2026-10-13T10:00")) 
    store.remove(a.id)
    assert store.get(a.id) is None
    assert [e.id for e in store.all_sorted()] == [b.id]
    check_invariants(store)


def test_remove_missing_id_raises():
    with pytest.raises(KeyError):      
        EventStore().remove(99)


def test_update_moves_event_to_new_position():
    store = EventStore()
    a = store.add(make_event("2026-10-13T09:00", "2026-10-13T10:00", title="A"))
    store.add(make_event("2026-10-13T12:00", "2026-10-13T13:00", title="B"))
    moved = replace(a, start=to_minutes("2026-10-13T14:00"), end=to_minutes("2026-10-13T15:00"))
    store.update(moved)
    assert [e.title for e in store.all_sorted()] == ["B", "A"]
    assert store.get(a.id).start == to_minutes("2026-10-13T14:00")
    check_invariants(store)


def test_window_includes_event_starting_before_window():
    store = EventStore()
    store.add(make_event("2026-10-13T08:00", "2026-10-13T10:00"))
    found = store.events_in_window(to_minutes("2026-10-13T09:00"), to_minutes("2026-10-13T18:00"))
    assert len(found) == 1


def test_window_excludes_touching_events():
    store = EventStore()
    store.add(make_event("2026-10-13T08:00", "2026-10-13T09:00"))
    store.add(make_event("2026-10-13T18:00", "2026-10-13T19:00"))
    found = store.events_in_window(to_minutes("2026-10-13T09:00"), to_minutes("2026-10-13T18:00"))
    assert found == []


def test_window_finds_24_hour_event_from_previous_day():
    store = EventStore()
    store.add(make_event("2026-10-12T10:00", "2026-10-13T10:00"))   # exactly 24h
    found = store.events_in_window(to_minutes("2026-10-13T09:00"), to_minutes("2026-10-13T18:00"))
    assert len(found) == 1


def test_load_sorted_bulk():
    events = [Event(id=i, title="E", start=i * 60, end=i * 60 + 30, category="meeting")
              for i in range(1, 6)]
    store = EventStore()
    store.load_sorted(events)
    assert len(store) == 5
    assert store.add(make_event("2026-10-13T09:00", "2026-10-13T10:00")).id == 6
    check_invariants(store)


def test_load_sorted_rejects_unsorted_input():
    events = [Event(id=1, title="E", start=100, end=200, category="meeting"),
              Event(id=2, title="E", start=50, end=80, category="meeting")]
    with pytest.raises(ValueError):
        EventStore().load_sorted(events)


def test_random_operations_keep_invariants():
    rng = random.Random(42)
    store = EventStore()
    for _ in range(2000):
        action = rng.choice(["add", "add", "update", "remove"])
        ids = [e.id for e in store.all_sorted()]
        if action == "add" or not ids:
            start = rng.randrange(0, 10_000)
            store.add(Event(id=None, title="E", start=start,
                            end=start + rng.randrange(5, 1441), category="meeting"))
        elif action == "update":
            old = store.get(rng.choice(ids))
            start = rng.randrange(0, 10_000)
            store.update(replace(old, start=start, end=start + old.duration))
        else:
            store.remove(rng.choice(ids))
        check_invariants(store)


def test_window_matches_simple_check_on_random_calendar():
    rng = random.Random(7)
    store = EventStore()
    for _ in range(500):
        start = rng.randrange(0, 20_000)
        store.add(Event(id=None, title="E", start=start,
                        end=start + rng.randrange(5, 1441), category="meeting"))
    for _ in range(200):
        ws = rng.randrange(0, 20_000)
        we = ws + rng.randrange(1, 3000)
        fast = {e.id for e in store.events_in_window(ws, we)}
        slow = {e.id for e in store.all_sorted() if e.start < we and e.end > ws}
        assert fast == slow

def test_tasks_sorted_and_filtered_by_priority():
    store = TaskStore()
    for name, priority in [("a", "Low"), ("b", "High"), ("c", "Medium"), ("d", "High")]:
        store.add(Task(id=None, name=name, category="assignment",
                       duration=60, priority=priority))
    assert [t.name for t in store.by_priority()] == ["b", "d", "c", "a"]
    assert [t.name for t in store.by_priority("High")] == ["b", "d"]
    assert store.by_priority("Medium")[0].name == "c"