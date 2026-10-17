"""
Algorithm 1: Sort-and-Scan to find busy blocks and free gaps.

PURE FUNCTION: plain data in, plain data out. No UI, no database.

Time convention (from our Assignment 1 and 2):
    Every time is a whole number = minutes since a fixed reference date.
    Every interval is half-open [start, end): start is included, end is not.
    So 10:00-11:00 and 11:00-12:00 only "touch" and do not overlap.

Input events:
    Any object with .start and .end attributes (your teammate's Event record
    will work as long as it has those two fields).
    The list MUST already be sorted by start time (the sorted array, DS2, gives us this).

Output:
    busy_blocks: list of (start, end) tuples, in time order
    free_gaps:   list of (start, end) tuples, in time order
"""


def find_busy_blocks_and_free_gaps(events_in_window, window_start, window_end):
    # PART 1: merge overlapping/touching events into busy blocks
 
    busy_blocks = []  # each block is a [start, end] list so we can extend it

    for event in events_in_window:  # earliest start to latest start
        # Trim the event to the window. An event that starts before the window
        # (or ends after it) only counts for the part that is inside.
        block_start = max(event.start, window_start)
        block_end = min(event.end, window_end)

        # Safety check: if nothing of this event is inside the window, skip it.
        if block_start >= block_end:
            continue

        # Because events arrive in start order, a new event can only reach
        # the LAST block. All earlier blocks end before the last one begins.
        if busy_blocks and block_start <= busy_blocks[-1][1]:
            # Overlaps or touches the last block -> extend it (merge).
            # max() matters: a nested event must not shrink the block.
            busy_blocks[-1][1] = max(busy_blocks[-1][1], block_end)
        else:
            # There is a gap before this event -> start a new block.
            busy_blocks.append([block_start, block_end])

   
    # PART 2: the free gaps are the empty time between busy blocks

    free_gaps = []
    free_from = window_start  # the user is free from here until the next block

    for block_start, block_end in busy_blocks:
        if block_start > free_from:  # empty time before this block
            free_gaps.append((free_from, block_start))
        free_from = block_end  # next free time can only start after this block

    if free_from < window_end:  # empty time after the last block
        free_gaps.append((free_from, window_end))

    # Convert [start, end] lists to (start, end) tuples so callers can't
    # accidentally change them.
    return [tuple(block) for block in busy_blocks], free_gaps



# self-check. Run:  python algorithm1_busy_and_gaps.py
# (The real pytest tests come later; this just proves it works.)

if __name__ == "__main__":
    from collections import namedtuple

    Ev = namedtuple("Ev", ["start", "end"])

    def hm(h, m=0):
        """Hours/minutes -> minutes since midnight (same day, for demo only)."""
        return h * 60 + m

    # Test T4: window 9:00-18:00, one event 8:00-10:00
    busy, gaps = find_busy_blocks_and_free_gaps(
        [Ev(hm(8), hm(10))], hm(9), hm(18)
    )
    assert busy == [(hm(9), hm(10))]
    assert gaps == [(hm(10), hm(18))]

    # Worked example from Assignment 1: A, B, C(overlaps B), D
    events = [
        Ev(hm(9), hm(9, 30)),
        Ev(hm(12), hm(13)),
        Ev(hm(12, 30), hm(13, 30)),
        Ev(hm(16), hm(17)),
    ]
    busy, gaps = find_busy_blocks_and_free_gaps(events, hm(9), hm(18))
    assert busy == [(hm(9), hm(9, 30)), (hm(12), hm(13, 30)), (hm(16), hm(17))]
    assert gaps == [(hm(9, 30), hm(12)), (hm(13, 30), hm(16)), (hm(17), hm(18))]

    # Empty calendar: whole window is one gap
    assert find_busy_blocks_and_free_gaps([], hm(9), hm(18)) == ([], [(hm(9), hm(18))])

    # One event covering the whole window: no gaps
    busy, gaps = find_busy_blocks_and_free_gaps([Ev(hm(8), hm(19))], hm(9), hm(18))
    assert busy == [(hm(9), hm(18))] and gaps == []

    # Touching events merge into one block
    busy, gaps = find_busy_blocks_and_free_gaps(
        [Ev(hm(10), hm(11)), Ev(hm(11), hm(12))], hm(9), hm(18)
    )
    assert busy == [(hm(10), hm(12))]

    # Nested event must not shrink the block
    busy, gaps = find_busy_blocks_and_free_gaps(
        [Ev(hm(10), hm(14)), Ev(hm(11), hm(12))], hm(9), hm(18)
    )
    assert busy == [(hm(10), hm(14))]

    print("Algorithm 1: all checks passed")