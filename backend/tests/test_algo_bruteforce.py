import random
import pytest

from app.algorithms.best_time import find_best_slots
from app.algorithms.conflict_check import find_all_conflicts, find_conflicts_for_event
from app.algorithms.interval_scan import find_busy_blocks_and_free_gaps
from app.models.records import CATEGORIES, Preferences
from app.store.event_store import EventStore
from samples.calendars import MINUTES_PER_DAY, RANDOM_FIRST_DAY, random_events

SEEDS = range(20)
BASE = RANDOM_FIRST_DAY * MINUTES_PER_DAY

DENSE = (60, 2, 600)       
SPARSE = (40, 30, 240)    
SHAPES = [DENSE, SPARSE]

def build_store(seed, shape):
    n, span_days, max_duration = shape
    store = EventStore()
    for event in random_events(n, seed, span_days=span_days, max_duration=max_duration):
        store.add(event)
    return store


def brute_overlap(a_start, a_end, b_start, b_end):
    low, high = max(a_start, b_start), min(a_end, b_end)
    return (low, high) if low < high else None


def brute_pairs(events):
    pairs = {}
    for i, a in enumerate(events):
        for b in events[i + 1:]:
            overlap = brute_overlap(a.start, a.end, b.start, b.end)
            if overlap:
                pairs[frozenset((a.id, b.id))] = overlap
    return pairs

@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("seed", SEEDS)
def test_full_scan_reports_exactly_the_pairs_brute_force_finds(seed, shape):
    events = build_store(seed, shape).sorted_events()
    found = find_all_conflicts(events)

    reported = {frozenset((a.id, b.id)): (start, end) for a, b, start, end in found}
    assert len(found) == len(reported)                 
    assert reported == brute_pairs(events)             
    assert all(a.start <= b.start for a, b, _, _ in found)

@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("seed", SEEDS)
def test_incremental_check_matches_brute_force_for_random_queries(seed, shape):
    events = build_store(seed, shape).sorted_events()
    span_days = shape[1]
    rng = random.Random(seed + 1000)

    for _ in range(60):
        start = BASE - MINUTES_PER_DAY + 5 * rng.randrange((span_days + 2) * 288)
        end = start + 5 * rng.randrange(1, 289)         
        found = {e.id for e in find_conflicts_for_event(events, start, end)}
        expected = {e.id for e in events if brute_overlap(start, end, e.start, e.end)}
        assert found == expected


@pytest.mark.parametrize("shape", SHAPES)
@pytest.mark.parametrize("seed", SEEDS)
def test_incremental_and_full_scan_report_the_same_conflicts(seed, shape):
    events = build_store(seed, shape).sorted_events()

    from_incremental = set()
    for event in events:
        for other in find_conflicts_for_event(events, event.start, event.end,
                                              exclude_id=event.id):
            from_incremental.add(frozenset((event.id, other.id)))

    from_full_scan = {frozenset((a.id, b.id)) for a, b, _, _ in find_all_conflicts(events)}
    assert from_incremental == from_full_scan

@pytest.mark.parametrize("seed", SEEDS)
def test_gaps_and_blocks_match_a_minute_by_minute_check(seed):
    store = build_store(seed, (12, 1, 180))
    all_events = store.sorted_events()
    rng = random.Random(seed + 2000)

    for _ in range(8):
        window_start = BASE + 5 * rng.randrange(200)
        window_end = window_start + 5 * rng.randrange(12, 120)     

        in_window = store.events_in_window(window_start, window_end)
        brute_in_window = sorted(
            (e for e in all_events if e.start < window_end and e.end > window_start),
            key=lambda e: (e.start, e.id))
        assert in_window == brute_in_window

        busy, gaps = find_busy_blocks_and_free_gaps(in_window, window_start, window_end)

        for start, end in busy + gaps:
            assert window_start <= start < end <= window_end
        assert busy == sorted(busy) and gaps == sorted(gaps)
        for (_, earlier_end), (later_start, _) in zip(busy, busy[1:]):
            assert earlier_end < later_start           

        busy_minutes = {m for s, e in busy for m in range(s, e)}
        gap_minutes = {m for s, e in gaps for m in range(s, e)}
        assert sum(e - s for s, e in busy) + sum(e - s for s, e in gaps) \
            == window_end - window_start
        assert busy_minutes | gap_minutes == set(range(window_start, window_end))
        assert not busy_minutes & gap_minutes

        truly_busy = {m for e in in_window
                      for m in range(max(e.start, window_start), min(e.end, window_end))}
        assert busy_minutes == truly_busy


def rank_key(slot):
    priority_key = slot.start if slot.priority_rule == "earliest_start" else slot.leftover
    return (not slot.before_cutoff, not slot.matches_preferred, priority_key, slot.start)


@pytest.mark.parametrize("mode", ["Flexible", "Strict"])
@pytest.mark.parametrize("seed", SEEDS)
def test_slot_guarantees_on_random_calendars(seed, mode):
    rng = random.Random(seed)
    store = build_store(seed, (25, 3, 240))
    events = store.sorted_events()

    first_day = RANDOM_FIRST_DAY
    last_day = first_day + 2
    prefs = Preferences(cutoff=rng.choice([17 * 60, 19 * 60, 21 * 60]), cutoff_mode=mode)
    daily_start = rng.choice([6 * 60, 9 * 60])
    daily_end = rng.choice([17 * 60, 18 * 60, 22 * 60])

    for _ in range(5):
        duration = 5 * rng.randrange(1, 49)             
        priority = rng.choice(["High", "Medium", "Low"])
        category = rng.choice(CATEGORIES)

        def search():
            return find_best_slots(
                store, duration=duration, priority=priority, category=category,
                prefs=prefs, first_day=first_day, last_day=last_day,
                daily_start=daily_start, daily_end=daily_end)

        result = search()
        assert search() == result                       

        assert len(result.slots) <= 5
        for slot in result.slots:
            day = slot.start // MINUTES_PER_DAY
            cutoff = day * MINUTES_PER_DAY + prefs.cutoff

            assert slot.end - slot.start == duration                         # exact length
            assert not any(e.start < slot.end and slot.start < e.end         # never overlaps
                           for e in events)
            assert first_day <= day <= last_day                              # inside the window
            assert day * MINUTES_PER_DAY + daily_start <= slot.start
            assert slot.end <= day * MINUTES_PER_DAY + daily_end
            assert slot.before_cutoff == (slot.end <= cutoff)                # label is honest
            if mode == "Strict":
                assert slot.end <= cutoff                                    # never past cutoff
            expected_rule = "earliest_start" if priority == "High" else "best_fit"
            assert slot.priority_rule == expected_rule

        keys = [rank_key(s) for s in result.slots]
        assert keys == sorted(keys)                     # the rules are applied in order


@pytest.mark.parametrize("mode", ["Flexible", "Strict"])
@pytest.mark.parametrize("seed", SEEDS)
def test_finder_never_misses_a_slot_that_exists(seed, mode):
    rng = random.Random(seed + 500)
    store = build_store(seed, (25, 3, 240))
    events = store.sorted_events()

    first_day = RANDOM_FIRST_DAY
    last_day = first_day + 2
    prefs = Preferences(cutoff=rng.choice([17 * 60, 19 * 60, 21 * 60]), cutoff_mode=mode)
    daily_start, daily_end = 9 * 60, rng.choice([18 * 60, 22 * 60])

    for _ in range(5):
        duration = 5 * rng.randrange(1, 49)
        result = find_best_slots(
            store, duration=duration, priority="Medium", category="assignment",
            prefs=prefs, first_day=first_day, last_day=last_day,
            daily_start=daily_start, daily_end=daily_end)

        feasible = False
        for day in range(first_day, last_day + 1):
            day_start = day * MINUTES_PER_DAY
            cutoff = day_start + prefs.cutoff
            for start in range(day_start + daily_start, day_start + daily_end - duration + 1, 5):
                end = start + duration
                if mode == "Strict" and end > cutoff:
                    continue
                if any(e.start < end and start < e.end for e in events):
                    continue
                feasible = True
                break
            if feasible:
                break

        assert bool(result.slots) == feasible