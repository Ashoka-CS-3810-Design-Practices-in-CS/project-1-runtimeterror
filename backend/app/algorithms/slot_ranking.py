"""
Algorithm 2: Greedy Best-Fit Slot Ranking.

PURE FUNCTION: plain data in, plain data out. No UI, no database, no Flask.

Input:  the free gaps from Algorithm 1, plus the task's duration/priority and
        the user's saved preferences.
Output: a ranked list of candidate slots (best first). Each slot is a dict that
        also carries the REASONS for its rank, so the Explainer can build its
        sentences from the same data (the explanation can never contradict the
        ranking).

Time convention (same as Algorithm 1):
    Times are whole minutes since a fixed reference date.
    ASSUMPTION: the reference date starts at midnight, so
    (time % 1440) is the minute of the day and (time // 1440) is the day number.
    Intervals are half-open [start, end).

Ranking rules, applied in this fixed order (a later rule only breaks ties
left by earlier ones):
    1. Before the cutoff beats after the cutoff
    2. Matches the preferred time of day beats not matching
    3. Priority rule: High   -> earliest start
                      Others -> best fit (smallest leftover space in the gap)
    4. Tie-breaker: earliest start
"""

MINUTES_PER_DAY = 24 * 60

# Assumption A9 from Assignment 1: (start, end) as minutes of the day.
TIME_OF_DAY = {
    "morning": (6 * 60, 12 * 60),      # 6 AM  - 12 PM
    "afternoon": (12 * 60, 17 * 60),   # 12 PM - 5 PM
    "night": (17 * 60, 24 * 60),       # 5 PM  - midnight
}


def rank_slots(free_gaps, duration, priority, preferred_time,
               cutoff_minutes, cutoff_mode, max_slots=5):
    """
    free_gaps:      list of (start, end) from Algorithm 1
    duration:       task length in minutes
    priority:       "High", "Medium" or "Low"
    preferred_time: "morning", "afternoon", "night", or None (no preference)
                    (the Controller looks this up from the preferences using
                    the task's category)
    cutoff_minutes: the daily cutoff as minutes of the day (9 PM = 21 * 60)
    cutoff_mode:    "Strict" or "Flexible"
    max_slots:      N, how many slots to return

    Returns a list of dicts, best first. Empty list = "no suitable slot found".
    """
    if cutoff_mode not in ("Strict", "Flexible"):
        raise ValueError("cutoff_mode must be 'Strict' or 'Flexible'")

    is_high = str(priority).lower() == "high"
    candidates = []

    for gap_start, gap_end in free_gaps:
        # The cutoff is a time of day, so find it on the day this gap is on.
        day_start = (gap_start // MINUTES_PER_DAY) * MINUTES_PER_DAY
        cutoff = day_start + cutoff_minutes

        for piece_start, piece_end, is_before_cutoff in _split_at_cutoff(
                gap_start, gap_end, cutoff, cutoff_mode, duration):

            # Fit check: the piece must be long enough for the task.
            piece_length = piece_end - piece_start
            if piece_length < duration:
                continue

            # Place the task inside this piece.
            window = _preferred_window(piece_start, piece_end, preferred_time)
            slot_start = _choose_start(piece_start, piece_end, duration, window)
            slot_end = slot_start + duration

            # Does the whole slot sit inside the preferred time of day?
            matches_preferred = (
                window is not None
                and slot_start >= window[0]
                and slot_end <= window[1]
            )

            # Priority rule: High -> earliest start, others -> best fit.
            if is_high:
                priority_key = slot_start
                priority_rule = "earliest_start"
            else:
                priority_key = piece_length - duration  # leftover space
                priority_rule = "best_fit"

            candidates.append({
                "start": slot_start,
                "end": slot_end,
                # --- ranking data (the Explainer reads these) ---
                "gap_start": piece_start,
                "gap_end": piece_end,
                "gap_length": piece_length,
                "leftover": piece_length - duration,
                "before_cutoff": is_before_cutoff,
                "matches_preferred": matches_preferred,
                "priority_rule": priority_rule,
                "priority_key": priority_key,
            })

    # One sort applying the four rules in order. False sorts before True, so
    # "not X" puts the slots that satisfy X first. Python's sort is stable and
    # the key is fully decided by the tuple, so the same input always gives
    # the same order.
    candidates.sort(key=lambda c: (
        not c["before_cutoff"],       # rule 1
        not c["matches_preferred"],   # rule 2
        c["priority_key"],            # rule 3
        c["start"],                   # rule 4
    ))

    return candidates[:max_slots]


# ----------------------------------------------------------------------
# Helpers (small, single-purpose)
# ----------------------------------------------------------------------

def _split_at_cutoff(gap_start, gap_end, cutoff, cutoff_mode, duration):
    """
    Cut a gap at the cutoff and return a list of
    (start, end, is_before_cutoff) pieces.
      Strict:   only the part before the cutoff is kept.
      Flexible: the part before is kept, and a late piece is kept too. The late
                piece normally starts at the cutoff. But if the task does not
                fit before the cutoff, the late piece is the whole gap, so the
                task may start before the cutoff and run past it (a last
                resort, ranked below every slot that ends by the cutoff).
    """
    pieces = []

    before = (gap_start, min(gap_end, cutoff))
    before_length = max(0, before[1] - before[0])
    if before_length > 0:
        pieces.append((before[0], before[1], True))

    if cutoff_mode == "Flexible":
        late_start = max(gap_start, cutoff)
        if gap_start < cutoff < gap_end and before_length < duration:
            late_start = gap_start          # the task has to straddle the cutoff
        if late_start < gap_end:
            pieces.append((late_start, gap_end, False))

    return pieces


def _preferred_window(piece_start, piece_end, preferred_time):
    """
    Return the preferred time-of-day window as (start, end) in absolute
    minutes, if it overlaps this piece. Otherwise return None.
    (A piece is at most a day or so long, so we check each day it touches.)
    """
    if preferred_time not in TIME_OF_DAY:
        return None

    window_start_of_day, window_end_of_day = TIME_OF_DAY[preferred_time]
    first_day = piece_start // MINUTES_PER_DAY
    last_day = (piece_end - 1) // MINUTES_PER_DAY

    for day in range(first_day, last_day + 1):
        window_start = day * MINUTES_PER_DAY + window_start_of_day
        window_end = day * MINUTES_PER_DAY + window_end_of_day
        if window_start < piece_end and piece_start < window_end:  # overlap
            return (window_start, window_end)
    return None


def _choose_start(piece_start, piece_end, duration, window):
    """
    Start at the beginning of the preferred window if the piece covers it and
    the task still fits. Otherwise start at the beginning of the piece.
    """
    if window is None:
        return piece_start
    start = max(piece_start, window[0])
    if start + duration > piece_end:
        return piece_start
    return start