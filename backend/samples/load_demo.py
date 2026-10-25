
import argparse
import os
from dataclasses import replace
from datetime import date, datetime, timedelta

from app.controller.controller import Controller
from app.storage.sqlite_store import SQLiteStorage
from app.store.event_store import EventStore
from app.store.task_store import TaskStore
from samples.calendars import demo_events, demo_tasks, random_events


def default_monday(today):

    monday = today - timedelta(days=today.weekday())
    return monday + timedelta(days=7) if today.weekday() >= 5 else monday


def populate(controller, monday):

    for data in demo_events(monday):
        controller.create_event(data)
    for data in demo_tasks(monday):
        controller.create_task(data)


def add_big_calendar(storage, controller, count, today):

    first_day = (datetime.combine(today, datetime.min.time()) - datetime(2000, 1, 1)).days - 90
    next_id = max((e.id for e in controller.events.sorted_events()), default=0) + 1
    events = [replace(e, id=next_id + i)
              for i, e in enumerate(random_events(count, seed=42, span_days=300,
                                                  first_day=first_day))]
    storage.save_events(events)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--db", default=os.environ.get("CALENDAR_DB", "calendar.db"))
    parser.add_argument("--reset", action="store_true", help="delete the database first")
    parser.add_argument("--big", type=int, default=0, metavar="N",
                        help="also add N generated events")
    parser.add_argument("--monday", help="Monday of the demo week, YYYY-MM-DD")
    args = parser.parse_args()

    today = date.today()
    monday = date.fromisoformat(args.monday) if args.monday else default_monday(today)
    if monday.weekday() != 0:
        parser.error("--monday must be a Monday")

    if args.reset and os.path.exists(args.db):
        os.remove(args.db)

    storage = SQLiteStorage(args.db)
    controller = Controller(EventStore(), TaskStore())
    controller.attach_storage(storage)

    populate(controller, monday)
    if args.big:
        add_big_calendar(storage, controller, args.big, today)
    storage.close()

    print(f"Loaded the demo week starting {monday} into {args.db}")
    if args.big:
        print(f"Added {args.big} generated events")


if __name__ == "__main__":
    main()