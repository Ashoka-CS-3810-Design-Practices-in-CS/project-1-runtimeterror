
#Binary-Search Incremental Conflict Checker + full-calendar scan


MAX_EVENT_DURATION = 24 * 60  


def overlap_range(start_a, end_a, start_b, end_b):
    overlap_start = max(start_a, start_b)
    overlap_end = min(end_a, end_b)
    if overlap_start < overlap_end:
        return (overlap_start, overlap_end)
    return None


def find_conflicts_for_event(sorted_events, start, end,
                             max_duration=MAX_EVENT_DURATION, exclude_id=None):
   
    earliest_possible_start = start - max_duration
    index = _first_index_starting_at_or_after(sorted_events, earliest_possible_start)

    conflicts = []
    while index < len(sorted_events) and sorted_events[index].start < end:
        candidate = sorted_events[index]
        is_itself = exclude_id is not None and candidate.id == exclude_id
        if not is_itself and overlap_range(start, end, candidate.start, candidate.end):
            conflicts.append(candidate)
        index += 1

    return conflicts


def _first_index_starting_at_or_after(sorted_events, target_time):

    low, high = 0, len(sorted_events)
    while low < high:
        middle = (low + high) // 2
        if sorted_events[middle].start < target_time:
            low = middle + 1     
        else:
            high = middle        
    return low

#full calendar scan

def find_all_conflicts(sorted_events):
    conflicts = []

    for i, current in enumerate(sorted_events):

        j = i + 1
  
        while j < len(sorted_events) and sorted_events[j].start < current.end:
            later = sorted_events[j]
            overlap_start = later.start                  
            overlap_end = min(current.end, later.end)    # whichever ends first
            conflicts.append((current, later, overlap_start, overlap_end))
            j += 1

    return conflicts