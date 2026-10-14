"""
Algorithm 3: Binary-Search Incremental Conflict Checker (+ full-calendar scan).

PURE FUNCTIONS: plain data in, plain data out. No UI, no database, no Flask.

Time convention (same as Algorithms 1 and 2):
    Times are whole minutes since a fixed reference date.
    Intervals are half-open [start, end), so events that only touch
    (10:00-11:00 and 11:00-12:00) are NOT a conflict.

Input events:
    Any object with .start and .end (and .id if you want to use exclude_id).
    The list MUST be sorted by start time (the sorted array, DS2).

Two functions:
    find_conflicts_for_event(...)  -> used after ONE event is created/moved/resized
    find_all_conflicts(...)        -> used for the whole calendar (app start, bulk adds)
"""

MAX_EVENT_DURATION = 24 * 60  # Assumption A3: an event is at most 24 hours


# ----------------------------------------------------------------------
# Overlap rule (the one rule everything else is built on)
# ----------------------------------------------------------------------

def overlap_range(start_a, end_a, start_b, end_b):
    """
    Return (overlap_start, overlap_end) if the two intervals overlap,
    otherwise None. Touching intervals give None (the "<" is strict).
    """
    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)
    if overlap_start < overlap_end:
        return (overlap_start, overlap_end)
    return None


# ----------------------------------------------------------------------
# Incremental check: ONE event against the sorted calendar
# ----------------------------------------------------------------------

def find_conflicts_for_event(sorted_events, start, end,
                             max_duration=MAX_EVENT_DURATION, exclude_id=None):
    """
    Return the list of existing events that overlap [start, end).

    sorted_events: events sorted by start time
    start, end:    the new or changed event's interval
    max_duration:  longest allowed event (24 hours), used to skip far-away events
    exclude_id:    id of the event being checked, if it is already inside
                   sorted_events (for example after a move), so it is not
                   reported as conflicting with itself
    """
    # Any event that starts earlier than (start - max_duration) must have
    # ended before `start`, so it cannot overlap. Binary search skips them all.
    earliest_possible_start = start - max_duration
    index = _first_index_starting_at_or_after(sorted_events, earliest_possible_start)

    conflicts = []
    # Scan forward. Once an event starts at or after `end`, every later event
    # does too (sorted order), so none of them can overlap. Stop there.
    while index < len(sorted_events) and sorted_events[index].start < end:
        candidate = sorted_events[index]
        is_itself = exclude_id is not None and candidate.id == exclude_id
        if not is_itself and overlap_range(start, end, candidate.start, candidate.end):
            conflicts.append(candidate)
        index += 1

    return conflicts


def _first_index_starting_at_or_after(sorted_events, target_time):
    """
    Binary search: index of the first event with start >= target_time
    (returns len(sorted_events) if there is none).
    """
    low, high = 0, len(sorted_events)
    while low < high:
        middle = (low + high) // 2
        if sorted_events[middle].start < target_time:
            low = middle + 1      # the answer is to the right of middle
        else:
            high = middle         # middle could be the answer, keep it
    return low


# ----------------------------------------------------------------------
# Full-calendar scan: EVERY conflicting pair, each reported once
# ----------------------------------------------------------------------

def find_all_conflicts(sorted_events):
    """
    Return a list of (earlier_event, later_event, overlap_start, overlap_end),
    one entry per conflicting pair. Overlap length in minutes is
    overlap_end - overlap_start.
    """
    conflicts = []

    for i, current in enumerate(sorted_events):
        # Only look at events AFTER current, so no pair is reported twice.
        j = i + 1
        # Sorted by start: a later event overlaps `current` exactly when it
        # starts before `current` ends. The first one that doesn't means every
        # event after it doesn't either, so we stop.
        while j < len(sorted_events) and sorted_events[j].start < current.end:
            later = sorted_events[j]
            overlap_start = later.start                  # later starts at/after current
            overlap_end = min(current.end, later.end)    # whichever ends first
            conflicts.append((current, later, overlap_start, overlap_end))
            j += 1

    return conflicts