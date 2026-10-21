#the event stores hash map and sorted array together

from bisect import bisect_left, insort
from dataclasses import replace

from app.models.records import Event, MAX_DURATION


def _key(event: Event) -> tuple[int, int]:
    return (event.start, event.id)


class EventStore:
    def __init__(self):
        self._by_id: dict[int, Event] = {}   #hash map
        self._sorted: list[Event] = []       #sorted array
        self._next_id = 1

    def get(self, event_id: int) -> Event | None:
        return self._by_id.get(event_id)

    def all_sorted(self) -> list[Event]:
        return list(self._sorted)

    def sorted_events(self) -> list[Event]:
        """The live sorted list, not a copy. Read-only: never change it."""
        return self._sorted

    def __len__(self) -> int:
        return len(self._by_id)

    def events_in_window(self, window_start: int, window_end: int) -> list[Event]:
        earliest_possible_start = window_start - MAX_DURATION
        i = bisect_left(self._sorted, (earliest_possible_start,), key=_key)

        result = []
        while i < len(self._sorted) and self._sorted[i].start < window_end:
            event = self._sorted[i]
            if event.end > window_start:       
                result.append(event)
            i += 1
        return result


    def add(self, event: Event) -> Event:
        stored = replace(event, id=self._next_id)
        self._next_id += 1
        self._by_id[stored.id] = stored
        insort(self._sorted, stored, key=_key)
        return stored

    def remove(self, event_id: int) -> Event:
        event = self._by_id.pop(event_id)          
        i = bisect_left(self._sorted, _key(event), key=_key)
        del self._sorted[i]
        return event

    def update(self, new_event: Event) -> Event:
        self.remove(new_event.id)
        self._by_id[new_event.id] = new_event
        insort(self._sorted, new_event, key=_key)
        return new_event

    def load_sorted(self, events: list[Event]) -> None:
        if self._sorted:
            raise RuntimeError("load_sorted only works on an empty store")
        for event in events:
            if self._sorted and _key(event) < _key(self._sorted[-1]):
                raise ValueError("events must be given in start-time order")
            self._sorted.append(event)
            self._by_id[event.id] = event
        if events:
            self._next_id = max(self._by_id) + 1