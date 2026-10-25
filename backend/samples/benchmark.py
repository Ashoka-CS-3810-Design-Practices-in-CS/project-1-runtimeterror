
import os
import random
import statistics
import tempfile
import time
from datetime import datetime, timedelta

from app.algorithms.best_time import find_slots_for_task
from app.algorithms.conflict_check import find_all_conflicts, find_conflicts_for_event
from app.controller.controller import Controller
from app.models.records import Event, Preferences, Task
from app.models.timeconv import to_minutes
from app.storage.sqlite_store import SQLiteStorage
from app.store.event_store import EventStore
from app.store.task_store import TaskStore
from samples.calendars import MINUTES_PER_DAY, random_events, sorted_by_start

TARGETS_MS = {"conflict_check": 500, "finder_2_weeks": 2000, "load_calendar": 3000}

NOW = datetime(2026, 10, 20, 10, 0)             
TODAY_DAY = to_minutes("2026-10-20T00:00") // MINUTES_PER_DAY
FIRST_DAY = TODAY_DAY - 90                      
SPAN_DAYS = 365                             


def median_ms(function, repeats):
    times = []
    for _ in range(repeats):
        started = time.perf_counter()
        function()
        times.append((time.perf_counter() - started) * 1000)
    return statistics.median(times)


def fresh_controller(db_path):
    storage = SQLiteStorage(db_path)
    controller = Controller(EventStore(), TaskStore(), clock=lambda: NOW)
    return controller, storage


def measure(n, db_path, seed=7):

    events = sorted_by_start(random_events(n, seed, span_days=SPAN_DAYS, first_day=FIRST_DAY))

    # Save once (setup), then time the startup load several times.
    setup_storage = SQLiteStorage(db_path)
    setup_storage.save_events(events)
    setup_storage.close()

    def load_once():
        controller, storage = fresh_controller(db_path)
        controller.attach_storage(storage)      # read rows, build both structures
        storage.close()

    results = {"events": n, "load_calendar_ms": median_ms(load_once, 3)}

    controller, storage = fresh_controller(db_path)
    controller.attach_storage(storage)
    store = controller.events
    assert len(store) == n

    rng = random.Random(seed + 1)
    span_minutes = SPAN_DAYS * 288

    def random_query():
        start = FIRST_DAY * MINUTES_PER_DAY + 5 * rng.randrange(span_minutes)
        return start, start + 5 * rng.randrange(6, 37)          # 30 to 180 minutes

    queries = [random_query() for _ in range(200)]
    query_iter = iter(queries)
    results["conflict_check_ms"] = median_ms(
        lambda: find_conflicts_for_event(store.sorted_events(), *next(query_iter)), 200)

    results["full_scan_ms"] = median_ms(
        lambda: find_all_conflicts(store.sorted_events()), 5)

    prefs = Preferences()
    high = Task(None, "bench", "assignment", 90, "High")
    medium = Task(None, "bench", "assignment", 90, "Medium")
    results["finder_2_weeks_ms"] = max(
        median_ms(lambda: find_slots_for_task(store, task, prefs, TODAY_DAY), 10)
        for task in (high, medium))

    def insert_and_remove():
        start, end = random_query()
        stored = store.add(Event(None, "bench", start, end, "personal"))
        store.remove(stored.id)

    results["insert_delete_ms"] = median_ms(insert_and_remove, 50)

    # End to end: validate + store + save to SQLite + conflict check.
    day_rng = random.Random(seed + 2)

    def create_one():
        day = (NOW + timedelta(days=1 + day_rng.randrange(90))).date()
        hour = 8 + day_rng.randrange(10)
        controller.create_event({
            "title": "Bench", "category": "personal",
            "start": f"{day.isoformat()}T{hour:02d}:00",
            "end": f"{day.isoformat()}T{hour + 1:02d}:00"})

    results["create_event_ms"] = median_ms(create_one, 20)
    storage.close()
    return results


def main():
    rows = []
    with tempfile.TemporaryDirectory() as folder:
        for n in (1000, 5000):
            rows.append(measure(n, os.path.join(folder, f"bench{n}.db")))

    lines = [
        "| Operation | Target | " + " | ".join(f"{r['events']} events" for r in rows) + " |",
        "|---|---|" + "---|" * len(rows),
    ]
    table = [
        ("Conflict check after one change (Algorithm 3)", "under 500 ms", "conflict_check_ms"),
        ("Create an event end to end (validate, store, save, check)", "under 500 ms", "create_event_ms"),
        ("Best-time finder, 2-week window", "under 2000 ms", "finder_2_weeks_ms"),
        ("Load the saved calendar at startup", "under 3000 ms", "load_calendar_ms"),
        ("Full-calendar conflict scan (Algorithm 4)", "none set", "full_scan_ms"),
        ("Insert plus delete one event (sorted array)", "none set", "insert_delete_ms"),
    ]
    for label, target, key in table:
        cells = " | ".join(f"{r[key]:.3f} ms" for r in rows)
        lines.append(f"| {label} | {target} | {cells} |")

    text = "\n".join(lines)
    print(text)
    with open("perf_results.md", "w", encoding="utf-8") as out:
        out.write("# Performance results\n\n"
                  "Median of repeated runs, seeded random calendars, run by "
                  "`python -m samples.benchmark`.\n\n" + text + "\n")
    print("\nWritten to perf_results.md")


if __name__ == "__main__":
    main()