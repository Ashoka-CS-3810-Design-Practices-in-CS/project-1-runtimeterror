
#greedy slot ranking


'''
Ranking rules used in this fixed order 
    1. Before the cutoff beats after the cutoff
    2. Matches the preferred time of day beats not matching
    3. Priority rule: High = earliest start
                      Others = best fit (smallest leftover space in the gap)
    4. Tie-breaker: earliest start
'''

MINUTES_PER_DAY = 24 * 60


TIME_OF_DAY = {
    "morning": (6 * 60, 12 * 60),      # 6 AM  - 12 PM
    "afternoon": (12 * 60, 17 * 60),   # 12 PM - 5 PM
    "night": (17 * 60, 24 * 60),       # 5 PM  - midnight
}


def rank_slots(free_gaps, duration, priority, preferred_time,
               cutoff_minutes, cutoff_mode, max_slots=5):
    if cutoff_mode not in ("Strict", "Flexible"):
        raise ValueError("cutoff_mode must be 'Strict' or 'Flexible'")

    is_high = str(priority).lower() == "high"
    candidates = []

    for gap_start, gap_end in free_gaps:
        day_start = (gap_start // MINUTES_PER_DAY) * MINUTES_PER_DAY
        cutoff = day_start + cutoff_minutes

        for piece_start, piece_end, is_before_cutoff in _split_at_cutoff(
                gap_start, gap_end, cutoff, cutoff_mode, duration):

            piece_length = piece_end - piece_start
            if piece_length < duration:
                continue

            window = _preferred_window(piece_start, piece_end, preferred_time)
            slot_start = _choose_start(piece_start, piece_end, duration, window)
            slot_end = slot_start + duration

            matches_preferred = (
                window is not None
                and slot_start >= window[0]
                and slot_end <= window[1]
            )
            if is_high:
                priority_key = slot_start
                priority_rule = "earliest_start"
            else:
                priority_key = piece_length - duration  # leftover space
                priority_rule = "best_fit"

            candidates.append({
                "start": slot_start,
                "end": slot_end,
                "gap_start": piece_start,
                "gap_end": piece_end,
                "gap_length": piece_length,
                "leftover": piece_length - duration,
                "before_cutoff": is_before_cutoff,
                "matches_preferred": matches_preferred,
                "priority_rule": priority_rule,
                "priority_key": priority_key,
            })


    candidates.sort(key=lambda c: (
        not c["before_cutoff"],     
        not c["matches_preferred"],  
        c["priority_key"],            
        c["start"],                   
    ))

    return candidates[:max_slots]


def _split_at_cutoff(gap_start, gap_end, cutoff, cutoff_mode, duration):
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
    if window is None:
        return piece_start
    start = max(piece_start, window[0])
    if start + duration > piece_end:
        return piece_start
    return start