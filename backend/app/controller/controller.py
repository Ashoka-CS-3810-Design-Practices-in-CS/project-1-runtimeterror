#The Controller: the single coordination point between the layers.


from dataclasses import dataclass, replace
from datetime import datetime

from app.algorithms.best_time import (
    find_alternatives, find_slots_for_task,
)
from app.algorithms.conflict_check import (
    find_all_conflicts, find_conflicts_for_event, overlap_range,
)
from app.controller.errors import NotFoundError, SlotTakenError, ValidationError
from app.controller.validation import (
    parse_time, validate_event, validate_preferences, validate_task,
)
from app.models.records import PRIORITIES, Event, Preferences, Task
from app.models.timeconv import FORMAT, to_minutes

MINUTES_PER_DAY = 24 * 60


@dataclass(frozen=True)
class Conflict:
    """One overlapping pair. event_a starts at or before event_b."""
    event_a: Event
    event_b: Event
    overlap_start: int
    overlap_end: int

    @property
    def overlap_minutes(self) -> int:
        return self.overlap_end - self.overlap_start


@dataclass(frozen=True)
class EventResult:
    event: Event
    conflicts: list


@dataclass(frozen=True)
class Booking:
    event: Event
    conflicts: list
    removed_task_id: int


class Controller:
    def __init__(self, events, tasks, prefs=None, clock=datetime.now):
        self.events = events                    # EventStore
        self.tasks = tasks                      # TaskStore
        self.prefs = prefs or Preferences()
        self._clock = clock

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def list_events(self, start_text, end_text):
        """Events in the visible range, and the conflicts among them."""
        start = parse_time(start_text, "start")
        end = parse_time(end_text, "end")
        if end <= start:
            raise ValidationError("ER1", "end", "Invalid end time",
                                  "End time must be after start time.")
        events = self.events.events_in_window(start, end)     # sorted by start
        conflicts = [Conflict(a, b, s, e) for a, b, s, e in find_all_conflicts(events)]
        return events, conflicts

    def create_event(self, data):
        event = validate_event(data, self._today())
        stored = self.events.add(event)
        if self.storage:
            self.storage.save_event(stored)
        return EventResult(stored, self._conflicts_for(stored))

    def update_event(self, event_id, data):
        """Edit, move or resize: the same path, a full replacement."""
        self._event_or_404(event_id)
        event = replace(validate_event(data, self._today()), id=event_id)
        self.events.update(event)
        if self.storage:
            self.storage.save_event(event)
        return EventResult(event, self._conflicts_for(event))

    def delete_event(self, event_id):
        self._event_or_404(event_id)
        self.events.remove(event_id)
        if self.storage:
            self.storage.delete_event(event_id)
        return event_id

    def alternatives(self, event_id):
        event = self._event_or_404(event_id)
        if not event.movable:
            raise ValidationError("FIXED", None,
                                  "Fixed, cannot be moved by the planner",
                                  "This event is Fixed, so the planner will not "
                                  "suggest a new time for it.")
        return find_alternatives(self.events, event, self.prefs)

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def create_task(self, data):
        task = validate_task(data, self.prefs, self._today())
        stored = self.tasks.add(task)
        if self.storage:
            self.storage.save_task(stored)
        return stored

    def list_tasks(self, priority=None):
        if priority in (None, "All"):
            return self.tasks.by_priority()
        if priority not in PRIORITIES:
            raise ValidationError("ER4", "priority", "Invalid priority",
                                  "Filter by High, Medium, Low or All.")
        return self.tasks.by_priority(priority)

    def delete_task(self, task_id):
        self._task_or_404(task_id)
        self.tasks.remove(task_id)
        if self.storage:
            self.storage.delete_task(task_id)
        return task_id

    def suggest(self, task_id):
        """The best-time finder for one saved task."""
        task = self._task_or_404(task_id)
        now = self._now_minutes()
        return find_slots_for_task(self.events, task, self.prefs,
                                   today_day=now // MINUTES_PER_DAY, not_before=now)

    def accept_slot(self, task_id, data):
        """Book a suggested slot. Re-checks that it is still free (test T9)."""
        task = self._task_or_404(task_id)

        # The new event goes through the same validation as any event.
        event = validate_event({
            "title": task.name, "category": task.category,
            "start": data.get("start"), "end": data.get("end"),
            "priority": task.priority,
        }, self._today())
        if event.duration != task.duration:
            raise ValidationError("ER2", "end", "Wrong slot length",
                                  f"The slot must be exactly {task.duration} minutes long.")

        # T9: the calendar may have changed since the slots were shown.
        if find_conflicts_for_event(self.events.sorted_events(), event.start, event.end):
            raise SlotTakenError("SLOT_TAKEN", None, "That slot is no longer free",
                                 "Something was added to the calendar after these "
                                 "suggestions were made. Please pick another slot.")

        stored = self.events.add(event)
        self.tasks.remove(task_id)
        if self.storage:
            self.storage.save_booking(stored, task_id)   # one transaction
        return Booking(stored, [], task_id)

    # ------------------------------------------------------------------
    # Preferences
    # ------------------------------------------------------------------

    def get_preferences(self):
        return self.prefs

    def set_preferences(self, data):
        self.prefs = validate_preferences(data)         # raises before anything changes
        if self.storage:
            self.storage.save_preferences(self.prefs)
        return self.prefs

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _conflicts_for(self, event):
        """Every pair that includes this event (Algorithm 3, incremental)."""
        others = find_conflicts_for_event(
            self.events.sorted_events(), event.start, event.end, exclude_id=event.id)
        result = []
        for other in others:
            first, second = sorted((event, other), key=lambda e: (e.start, e.id))
            start, end = overlap_range(first.start, first.end, second.start, second.end)
            result.append(Conflict(first, second, start, end))
        return result

    def _event_or_404(self, event_id):
        event = self.events.get(event_id)
        if event is None:
            raise NotFoundError("ER7", None, "This event no longer exists",
                                "The event was already deleted. The calendar will refresh.")
        return event

    def _task_or_404(self, task_id):
        task = self.tasks.get(task_id)
        if task is None:
            raise NotFoundError("ER7", None, "This task no longer exists",
                                "The task was already removed. The list will refresh.")
        return task

    def _today(self):
        return self._clock().date()

    def _now_minutes(self):
        return to_minutes(self._clock().strftime(FORMAT))

    def __init__(self, events, tasks, prefs=None, clock=datetime.now, storage=None):
        self.events = events                    # EventStore
        self.tasks = tasks                      # TaskStore
        self.prefs = prefs or Preferences()
        self._clock = clock
        self.storage = storage                  # SQLiteStorage, or None (memory only)

    def attach_storage(self, storage):
        """Load everything saved so far, then save every change from now on."""
        self.events.load_sorted(storage.load_events())     # already in start order
        self.tasks.load(storage.load_tasks())
        saved = storage.load_preferences()
        if saved is not None:
            self.prefs = saved
        self.storage = storage