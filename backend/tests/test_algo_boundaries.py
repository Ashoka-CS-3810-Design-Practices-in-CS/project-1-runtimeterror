
from collections import namedtuple

import pytest

from app.algorithms.best_time import find_best_slots
from app.algorithms.conflict_check import (
    _first_index_starting_at_or_after, find_all_conflicts, find_conflicts_for_event,
)
from app.algorithms.interval_scan import find_busy_blocks_and_free_gaps
from app.algorithms.slot_ranking import rank_slots
from app.models.records import Event, Preferences
from app.store.event_store import EventStore

Ev = namedtuple("Ev", ["id", "start", "end"])
DAY = 1440


def hm(hour, minute=0):
    return hour * 60 + minute


def pairs(found):
    """(earlier id, later id, overlap minutes) for each reported pair."""
    return {(a.id, b.id, end - start) for a, b, start, end in found}


# ----------------------------------------------------------------------
# Intervals: touching, identical, nested, overnight, three at once
# ----------------------------------------------------------------------

def test_touching_events_are_not_conflicts():                        # T1
    events = [Ev(1, hm(10), hm(11)), Ev(2, hm(11), hm(12))]
    assert find_all_conflicts(events) == []
    assert find_conflicts_for_event(events, hm(11), hm(12), exclude_id=2) == []


def test_identical_events_overlap_for_their_whole_length():
    events = [Ev(1, hm(10), hm(11)), Ev(2, hm(10), hm(11))]
    assert pairs(find_all_conflicts(events)) == {(1, 2, 60)}


def test_nested_event_overlaps_for_its_own_length():
    events = [Ev(1, hm(9), hm(14)), Ev(2, hm(10), hm(11))]
    assert pairs(find_all_conflicts(events)) == {(1, 2, 60)}


def test_overnight_events_work_like_any_other():
    night_shift = Ev(1, hm(23), DAY + hm(1))              # 23:00 to 01:00 next day
    late_call = Ev(2, DAY + hm(0, 30), DAY + hm(2))       # 00:30 to 02:00 next day
    found = find_all_conflicts([night_shift, late_call])
    assert [(s, e) for _, _, s, e in found] == [(DAY + hm(0, 30), DAY + hm(1))]
    assert pairs(found) == {(1, 2, 30)}


def test_three_events_overlapping_at_once_report_every_pair_once():     # T3
    events = [Ev(1, hm(9), hm(11)), Ev(2, hm(10), hm(12)), Ev(3, hm(10, 30), hm(11, 30))]
    found = find_all_conflicts(events)
    assert len(found) == 3
    assert pairs(found) == {(1, 2, 60), (1, 3, 30), (2, 3, 60)}


def test_an_event_does_not_conflict_with_itself():
    events = [Ev(1, hm(10), hm(11))]
    assert find_conflicts_for_event(events, hm(10), hm(11)) == events
    assert find_conflicts_for_event(events, hm(10), hm(11), exclude_id=1) == []


# ----------------------------------------------------------------------
# The 24-hour lookback in Algorithm 3
# ----------------------------------------------------------------------

def test_24_hour_event_ending_exactly_when_the_new_event_starts():
    events = [Ev(1, 0, DAY)]                              # a full day
    assert find_conflicts_for_event(events, DAY, DAY + 60) == []


def test_24_hour_event_ending_one_minute_after_the_new_event_starts():
    events = [Ev(1, 1, DAY + 1)]
    found = find_conflicts_for_event(events, DAY, DAY + 60)
    assert [e.id for e in found] == [1]


def test_lookback_is_found_among_many_earlier_events():
    # lots of short events well before the query, plus two 24-hour events at the edge
    filler = [Ev(i, i * 10, i * 10 + 5) for i in range(1, 200)]
    query = (5 * DAY, 5 * DAY + 60)
    ends_exactly = Ev(1000, query[0] - DAY, query[0])               # no conflict
    ends_later = Ev(1001, query[0] - DAY + 1, query[0] + 1)         # conflict
    events = sorted(filler + [ends_exactly, ends_later], key=lambda e: (e.start, e.id))
    found = find_conflicts_for_event(events, *query)
    assert [e.id for e in found] == [1001]


@pytest.mark.parametrize("starts, target, expected", [
    ([10, 20, 20, 30], 20, 1),        # first event starting at or after the target
    ([10, 20, 20, 30], 21, 3),
    ([10, 20, 20, 30], 5, 0),
    ([10, 20, 20, 30], 31, 4),        # past the end
    ([], 5, 0),                       # empty list
])
def test_binary_search_finds_the_first_start_at_or_after(starts, target, expected):
    events = [Ev(i, s, s + 5) for i, s in enumerate(starts)]
    assert _first_index_starting_at_or_after(events, target) == expected


# ----------------------------------------------------------------------
# Search window: Algorithm 1
# ----------------------------------------------------------------------

WINDOW = (hm(9), hm(18))


def scan(events):
    return find_busy_blocks_and_free_gaps(events, *WINDOW)


def test_empty_calendar_is_one_free_gap():
    assert scan([]) == ([], [(hm(9), hm(18))])


def test_one_event_covering_the_whole_window_leaves_no_gap():
    assert scan([Ev(1, hm(8), hm(19))]) == ([(hm(9), hm(18))], [])


def test_event_starting_before_the_window_is_clipped():               # T4
    assert scan([Ev(1, hm(8), hm(10))]) == ([(hm(9), hm(10))], [(hm(10), hm(18))])


def test_event_ending_after_the_window_is_clipped():
    assert scan([Ev(1, hm(17), hm(19))]) == ([(hm(17), hm(18))], [(hm(9), hm(17))])


def test_events_outside_the_window_are_ignored():
    before = Ev(1, hm(6), hm(8))
    ends_exactly_at_window_start = Ev(2, hm(8), hm(9))
    assert scan([before, ends_exactly_at_window_start]) == ([], [(hm(9), hm(18))])


def test_touching_events_merge_and_a_nested_event_does_not_shrink_the_block():
    assert scan([Ev(1, hm(10), hm(11)), Ev(2, hm(11), hm(12))])[0] == [(hm(10), hm(12))]
    assert scan([Ev(1, hm(10), hm(14)), Ev(2, hm(11), hm(12))])[0] == [(hm(10), hm(14))]


def test_worked_example_from_assignment_1():
    events = [Ev(1, hm(9), hm(9, 30)), Ev(2, hm(12), hm(13)),
              Ev(3, hm(12, 30), hm(13, 30)), Ev(4, hm(16), hm(17))]
    busy, gaps = scan(events)
    assert busy == [(hm(9), hm(9, 30)), (hm(12), hm(13, 30)), (hm(16), hm(17))]
    assert gaps == [(hm(9, 30), hm(12)), (hm(13, 30), hm(16)), (hm(17), hm(18))]


# ----------------------------------------------------------------------
# A gap exactly as long as the task
# ----------------------------------------------------------------------

def finder(store, duration, priority="Medium", prefs=None):
    return find_best_slots(
        store, duration=duration, priority=priority, category="assignment",
        prefs=prefs or Preferences(), first_day=100, last_day=100,
        daily_start=hm(9), daily_end=hm(18))


def store_with(*spans):
    store = EventStore()
    for start, end in spans:
        store.add(Event(None, "busy", 100 * DAY + start, 100 * DAY + end, "meeting"))
    return store


def test_gap_exactly_as_long_as_the_task_fits_with_nothing_left_over():
    store = store_with((hm(9), hm(10, 30)), (hm(12), hm(18)))       # free 10:30 to 12:00
    slot = finder(store, 90).slots[0]
    assert (slot.start, slot.end) == (100 * DAY + hm(10, 30), 100 * DAY + hm(12))
    assert slot.leftover == 0
    assert "perfect fit" in " ".join(slot.reasons)


def test_gap_one_minute_too_short_gives_no_slot():
    store = store_with((hm(9), hm(10, 31)), (hm(12), hm(18)))       # free 89 minutes
    result = finder(store, 90)
    assert result.slots == ()
    assert result.no_slot_reason == "No 90-minute slot is free in this window."


# ----------------------------------------------------------------------
# Cutoff: Algorithm 2
# ----------------------------------------------------------------------

CUTOFF = hm(21)


def test_slot_ending_exactly_at_the_cutoff_counts_as_before_the_cutoff():
    slots = rank_slots([(hm(20), hm(22))], 60, "High", None, CUTOFF, "Strict")
    assert [(s["start"], s["end"], s["before_cutoff"]) for s in slots] == \
        [(hm(20), hm(21), True)]


def test_strict_mode_drops_a_task_that_would_end_after_the_cutoff():
    assert rank_slots([(hm(20), hm(22))], 61, "High", None, CUTOFF, "Strict") == []


def test_flexible_mode_keeps_late_slots_but_ranks_them_last():
    slots = rank_slots([(hm(20), hm(22))], 60, "High", None, CUTOFF, "Flexible")
    assert [(s["start"], s["before_cutoff"]) for s in slots] == \
        [(hm(20), True), (hm(21), False)]


def test_flexible_mode_lets_a_task_run_past_the_cutoff_as_a_last_resort():
    # 90 minutes does not fit before a 9 PM cutoff in a free 8 PM to 10 PM gap
    slots = rank_slots([(hm(20), hm(22))], 90, "High", None, CUTOFF, "Flexible")
    assert [(s["start"], s["end"], s["before_cutoff"]) for s in slots] == \
        [(hm(20), hm(21, 30), False)]


def test_strict_mode_never_lets_a_task_run_past_the_cutoff():
    assert rank_slots([(hm(20), hm(22))], 90, "High", None, CUTOFF, "Strict") == []


def test_a_slot_that_runs_past_the_cutoff_ranks_below_one_that_ends_by_it():
    gaps = [(hm(20), hm(22)), (hm(10), hm(12))]
    slots = rank_slots(gaps, 90, "High", None, CUTOFF, "Flexible")
    assert [(s["start"], s["before_cutoff"]) for s in slots] == \
        [(hm(10), True), (hm(20), False)]


def test_straddling_slot_starts_at_the_beginning_of_the_gap():
    # starting at the gap start keeps the overrun as small as possible
    slot = rank_slots([(hm(19), hm(23))], 150, "Medium", None, CUTOFF, "Flexible")[0]
    assert (slot["start"], slot["end"]) == (hm(19), hm(21, 30))
    assert slot["gap_length"] == hm(4)                      # the whole free gap is reported