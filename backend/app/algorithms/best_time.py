from dataclasses import dataclass

from app.algorithms.explainer import explain_slot, format_clock
from app.algorithms.interval_scan import find_busy_blocks_and_free_gaps
from app.algorithms.slot_ranking import rank_slots
from app.models.records import Slot
from app.models.timeconv import to_minutes

MINUTES_PER_DAY = 24 * 60
DEFAULT_SEARCH_DAYS = 14       


@dataclass(frozen=True)
class SlotSearch:
    slots: tuple[Slot, ...]
    no_slot_reason: str | None = None
    try_instead: tuple[str, ...] = ()


def find_slots_for_task(store, task, prefs, today_day, not_before=None, max_slots=5):
    first_day, last_day, daily_start, daily_end = resolve_task_window(
        task, prefs, today_day)
    return find_best_slots(
        store, duration=task.duration, priority=task.priority,
        category=task.category, prefs=prefs,
        first_day=first_day, last_day=last_day,
        daily_start=daily_start, daily_end=daily_end,
        not_before=not_before, max_slots=max_slots)


def resolve_task_window(task, prefs, today_day):
    first_day = (_day_of(task.from_date) if task.from_date else today_day)
    last_day = (_day_of(task.to_date) if task.to_date
                else first_day + DEFAULT_SEARCH_DAYS - 1)
    daily_start = task.daily_start if task.daily_start is not None else prefs.working_start
    daily_end = task.daily_end if task.daily_end is not None else prefs.working_end
    return first_day, last_day, daily_start, daily_end


def _day_of(date_text):
    return to_minutes(f"{date_text}T00:00") // MINUTES_PER_DAY


def find_best_slots(store, *, duration, priority, category, prefs,
                    first_day, last_day, daily_start, daily_end,
                    not_before=None, max_slots=5):
    slots = _search(store.events_in_window, duration, priority, category, prefs,
                    first_day, last_day, daily_start, daily_end,
                    not_before, max_slots)
    if slots:
        return SlotSearch(tuple(slots))

    reason = f"No {duration}-minute slot is free"
    tips = ["Shorten the task", "Widen the window"]
    if prefs.cutoff_mode == "Strict":
        reason += f" before your {format_clock(prefs.cutoff)} cutoff"
        tips.append("Switch the cutoff to Flexible")
    return SlotSearch((), reason + " in this window.", tuple(tips))


def find_alternatives(store, event, prefs, max_slots=5):
    if not event.movable:
        raise ValueError("Fixed, cannot be moved by the planner")

    day = event.start // MINUTES_PER_DAY

    def others(window_start, window_end):
        return [e for e in store.events_in_window(window_start, window_end)
                if e.id != event.id]

    slots = _search(others, event.duration, event.priority, event.category, prefs,
                    day, day, prefs.working_start, prefs.working_end,
                    None, max_slots)
    if slots:
        return SlotSearch(tuple(slots))
    return SlotSearch(
        (),
        f"No free {event.duration}-minute slot on that day within your working hours.",
        ("Shorten the event", "Move it to another day by hand"))


def _search(get_events, duration, priority, category, prefs,
            first_day, last_day, daily_start, daily_end, not_before, max_slots):
    all_gaps = []
    for day in range(first_day, last_day + 1):
        window_start = day * MINUTES_PER_DAY + daily_start
        window_end = day * MINUTES_PER_DAY + daily_end
        if not_before is not None:
            window_start = max(window_start, not_before)
        if window_start >= window_end:
            continue
        _, gaps = find_busy_blocks_and_free_gaps(
            get_events(window_start, window_end), window_start, window_end)
        all_gaps.extend(gaps)

    preferred = prefs.preferred_time.get(category)
    ranked = rank_slots(all_gaps, duration, priority, preferred,
                        prefs.cutoff, prefs.cutoff_mode, max_slots)

    return [
        Slot(
            start=c["start"], end=c["end"],
            gap_start=c["gap_start"], gap_end=c["gap_end"],
            gap_length=c["gap_length"], leftover=c["leftover"],
            before_cutoff=c["before_cutoff"],
            matches_preferred=c["matches_preferred"],
            priority_rule=c["priority_rule"],
            reasons=tuple(explain_slot(c, duration, priority, category,
                                       preferred, prefs.cutoff)),
        )
        for c in ranked
    ]