"""Assignment 3, section 3.1: after any sequence of inserts, edits and deletes,
the sorted array must be in start-time order and hold exactly the same events
as the hash map.

The test keeps its own plain dictionary as the model and compares the store
against it after every single step.
"""
import random
from dataclasses import replace

import pytest

from app.models.records import Event
from app.store.event_store import EventStore
from samples.calendars import MINUTES_PER_DAY, RANDOM_FIRST_DAY, random_events


def key(event):
    return (event.start, event.id)


@pytest.mark.parametrize("seed", range(10))
def test_sorted_array_and_hash_map_stay_in_step(seed):
    rng = random.Random(seed)
    store = EventStore()
    model = {}                                   # id -> Event, the simple truth
    pool = random_events(400, seed, span_days=10)

    for _ in range(300):
        action = rng.choice(["add", "add", "update", "remove"])
        if action == "add" or not model:
            stored = store.add(pool.pop())
            model[stored.id] = stored
        elif action == "update":
            event_id = rng.choice(sorted(model))
            changed = replace(pool.pop(), id=event_id)
            store.update(changed)
            model[event_id] = changed
        else:
            event_id = rng.choice(sorted(model))
            assert store.remove(event_id) == model.pop(event_id)

        assert len(store) == len(model)
        assert store.all_sorted() == sorted(model.values(), key=key)     # order and content
        assert all(store.get(i) == e for i, e in model.items())          # hash map agrees
        ids_in_array = [e.id for e in store.sorted_events()]
        assert sorted(ids_in_array) == sorted(model)                     # same ids, no repeats

    # and the window query agrees with a plain filter on the final calendar
    base = RANDOM_FIRST_DAY * MINUTES_PER_DAY
    for _ in range(20):
        start = base + 5 * rng.randrange(10 * 288)
        end = start + 5 * rng.randrange(1, 600)
        expected = sorted((e for e in model.values() if e.start < end and e.end > start),
                          key=key)
        assert store.events_in_window(start, end) == expected


def test_ids_are_never_reused_after_a_delete():
    store = EventStore()
    first = store.add(Event(None, "a", 0, 60, "meeting"))
    store.remove(first.id)
    second = store.add(Event(None, "b", 0, 60, "meeting"))
    assert (first.id, second.id) == (1, 2)


def test_bulk_load_gives_the_same_store_as_adding_one_by_one():
    one_by_one = EventStore()
    for event in random_events(200, seed=3, span_days=10):
        one_by_one.add(event)

    bulk = EventStore()
    bulk.load_sorted(one_by_one.all_sorted())

    assert bulk.all_sorted() == one_by_one.all_sorted()
    assert all(bulk.get(e.id) == e for e in one_by_one.all_sorted())
    new = Event(None, "next", 0, 60, "meeting")
    assert bulk.add(new).id == one_by_one.add(new).id                    # ids carry on


def test_bulk_load_rejects_events_that_are_not_in_start_order():
    store = EventStore()
    events = [Event(1, "late", 500, 560, "meeting"), Event(2, "early", 100, 160, "meeting")]
    with pytest.raises(ValueError):
        store.load_sorted(events)