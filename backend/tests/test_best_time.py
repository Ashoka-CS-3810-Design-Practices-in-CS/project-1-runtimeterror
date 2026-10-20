import pytest

from app.algorithms.best_time import (
    find_alternatives, find_best_slots, find_slots_for_task,
)
from app.models.records import Event, Preferences, Task
from app.models.timeconv import to_minutes
from app.store.event_store import EventStore

DAY = 9000   # an arbitrary day number; day * 1440 = minute that day starts


def t(hour, minute=0, day=0):
    """Absolute minute for a clock time on DAY + day."""
    return (DAY + day) * 1440 + hour * 60 + minute


def add(store, title, start, end, category="meeting", **kw):
    return store.add(Event(None, title, start, end, category, **kw))


def search(store, duration=90, priority="High", category="assignment",
           prefs=None, last_day=DAY, daily_start=9 * 60, daily_end=18 * 60, **extra):
    return find_best_slots(
        store, duration=duration, priority=priority, category=category,
        prefs=prefs or Preferences(), first_day=DAY, last_day=last_day,
        daily_start=daily_start, daily_end=daily_end, **extra)


# ---------- the shared search ----------

def test_empty_calendar_gives_one_slot_per_day_in_order():
    result = search(EventStore(), duration=60, priority="Medium", last_day=DAY + 2)
    starts = [s.start for s in result.slots]
    assert starts == [t(9), t(9, day=1), t(9, day=2)]


def test_worked_example_from_assignment_1():
    store = EventStore()
    add(store, "A", t(9), t(9, 30))
    add(store, "B", t(12), t(13))
    add(store, "C", t(12, 30), t(13, 30))
    add(store, "D", t(16), t(17))
    result = search(store)                      # 90 min, High, morning pref
    assert [(s.start, s.end) for s in result.slots] == [
        (t(9, 30), t(11)),                      # morning, earliest
        (t(13, 30), t(15)),                     # fits, outside morning
    ]
    assert result.slots[0].matches_preferred is True
    assert result.slots[1].matches_preferred is False


def test_slots_carry_reasons_from_the_explainer():
    store = EventStore()
    add(store, "A", t(9), t(9, 30))
    slot = search(store).slots[0]
    assert slot.reasons[0].startswith("Free for")
    assert any("morning preference" in r for r in slot.reasons)


def test_priority_rule_earliest_vs_best_fit():          # test T5
    store = EventStore()
    add(store, "busy", t(14, 30), t(16))
    kw = dict(duration=45, category="appointment",      # afternoon preference
              daily_start=12 * 60, daily_end=17 * 60)
    high = search(store, priority="High", **kw)
    medium = search(store, priority="Medium", **kw)
    assert high.slots[0].start == t(12)
    assert medium.slots[0].start == t(16)


def test_cutoff_strict_and_flexible():                  # test T6
    store = EventStore()
    add(store, "busy", t(18), t(21))
    kw = dict(duration=60, daily_start=18 * 60, daily_end=23 * 60)

    strict = search(store, prefs=Preferences(cutoff_mode="Strict"), **kw)
    assert strict.slots == ()
    assert "cutoff" in strict.no_slot_reason
    assert "Switch the cutoff to Flexible" in strict.try_instead

    flexible = search(store, **kw)
    assert [(s.start, s.end) for s in flexible.slots] == [(t(21), t(22))]
    assert flexible.slots[0].before_cutoff is False


def test_event_from_the_previous_night_blocks_the_morning():
    store = EventStore()
    add(store, "overnight", t(23, day=-1), t(10))       # crosses midnight
    result = search(store, duration=60)
    assert result.slots[0].start == t(10)


def test_not_before_hides_the_past():
    store = EventStore()
    assert search(store, not_before=t(13)).slots[0].start == t(13)
    assert search(store, not_before=t(19)).slots == ()


def test_no_slot_reason_when_calendar_is_full():
    store = EventStore()
    add(store, "all day", t(9), t(18))
    result = search(store)
    assert result.slots == ()
    assert result.no_slot_reason == "No 90-minute slot is free in this window."
    assert "Widen the window" in result.try_instead


def test_slots_never_overlap_events():
    store = EventStore()
    for h in (9, 11, 14, 16):
        add(store, f"e{h}", t(h), t(h, 45))
    for slot in search(store, duration=30, priority="Low").slots:
        assert not store.events_in_window(slot.start, slot.end)


# ---------- from a Task record ----------

def test_task_with_no_window_uses_two_weeks_and_working_hours():
    task = Task(None, "Write", "assignment", 60, "Medium")
    result = find_slots_for_task(EventStore(), task, Preferences(), today_day=DAY)
    assert len(result.slots) == 5                       # capped at max_slots
    assert all(DAY <= s.start // 1440 <= DAY + 13 for s in result.slots)


def test_task_with_its_own_window():
    task = Task(None, "Write", "assignment", 60, "High",
                from_date="2026-10-16", to_date="2026-10-16",
                daily_start=14 * 60, daily_end=17 * 60)
    result = find_slots_for_task(EventStore(), task, Preferences(), today_day=DAY)
    day = to_minutes("2026-10-16T00:00") // 1440
    assert len(result.slots) == 1
    assert result.slots[0].start == day * 1440 + 14 * 60


# ---------- conflict alternatives ----------

def test_alternatives_for_a_movable_event():
    store = EventStore()
    add(store, "Lecture", t(10), t(11, 30), "class")              # Fixed
    study = add(store, "Study", t(11), t(12), "assignment")       # Movable
    result = find_alternatives(store, study, Preferences())
    assert result.slots[0].start == t(9)                          # morning, fits
    for slot in result.slots:
        assert slot.end - slot.start == 60
        assert slot.start >= t(9) and slot.end <= t(18)
        assert not (slot.start < t(11, 30) and t(10) < slot.end)  # misses lecture


def test_alternatives_treat_the_event_itself_as_free_time():
    store = EventStore()
    only = add(store, "Study", t(10), t(11), "assignment")
    result = find_alternatives(store, only, Preferences())
    assert result.slots[0].gap_length == 9 * 60                   # whole working day


def test_alternatives_refuse_fixed_events():
    store = EventStore()
    lecture = add(store, "Lecture", t(10), t(11), "class")
    with pytest.raises(ValueError):
        find_alternatives(store, lecture, Preferences())


def test_alternatives_when_nothing_fits():
    store = EventStore()
    add(store, "Lunch", t(12), t(13), "class")
    long_one = add(store, "Marathon", t(9), t(18), "assignment")  # 9 hours
    result = find_alternatives(store, long_one, Preferences())
    assert result.slots == ()
    assert "No free 540-minute slot" in result.no_slot_reason