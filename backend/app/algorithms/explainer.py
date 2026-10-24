"""Explainer: turns a ranked slot's data into plain sentences.

Pure function. It only reads the ranking data Algorithm 2 attached to the
slot, so a sentence can never contradict the ranking.
"""

CATEGORY_LABEL = {
    "meeting": "meetings",
    "class": "classes",
    "appointment": "appointments",
    "assignment": "assignments",
    "personal": "personal tasks",
}


def format_duration(minutes: int) -> str:
    hours, mins = divmod(minutes, 60)
    parts = []
    if hours:
        parts.append(f"{hours} hour" + ("s" if hours != 1 else ""))
    if mins:
        parts.append(f"{mins} minute" + ("s" if mins != 1 else ""))
    return " ".join(parts) or "0 minutes"


def format_clock(minute_of_day: int) -> str:
    hour, mins = divmod(minute_of_day, 60)
    hour %= 24
    suffix = "AM" if hour < 12 else "PM"
    hour12 = hour % 12 or 12
    return f"{hour12} {suffix}" if mins == 0 else f"{hour12}:{mins:02d} {suffix}"


def explain_slot(slot, duration, priority, category, preferred_time, cutoff_minutes):
    """Return the list of reason sentences for one ranked slot (a dict from Algo 2)."""
    reasons = [
        f"Free for {format_duration(slot['gap_length'])}, "
        f"which fits your {duration}-minute task."
    ]

    # Rule 2 of the ranking: preferred time of day (skipped if no preference).
    if preferred_time is not None:
        label = CATEGORY_LABEL[category]
        if slot["matches_preferred"]:
            reasons.append(f"Matches your {preferred_time} preference for {label}.")
        else:
            reasons.append(f"Outside your {preferred_time} preference for {label}.")

    # Rule 1 of the ranking: cutoff (only worth saying when it was missed).
    if not slot["before_cutoff"]:
        reasons.append(
            f"This ends after your {format_clock(cutoff_minutes)} cutoff, "
            "so it is ranked below every slot that finishes by the cutoff."
        )

    # Rule 3 of the ranking: priority rule.
    if slot["priority_rule"] == "earliest_start":
        reasons.append(f"Ranked by earliest start, which suits a {priority} priority task.")
    elif slot["leftover"] == 0:
        reasons.append("A perfect fit, so no free time is wasted.")
    else:
        reasons.append(
            f"Best fit: only {format_duration(slot['leftover'])} left over, "
            "which keeps larger gaps free for longer tasks."
        )

    return reasons