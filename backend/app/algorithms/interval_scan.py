
#sort and scan to find busy blocks and free gaps.

def find_busy_blocks_and_free_gaps(events_in_window, window_start, window_end):
    # merge overlapping ortouching events into busy blocks
    busy_blocks = []  

    for event in events_in_window:  
        block_start = max(event.start, window_start)
        block_end = min(event.end, window_end)

        # Safety check if nothing of this event is inside the window skip it
        if block_start >= block_end:
            continue
        if busy_blocks and block_start <= busy_blocks[-1][1]:
            busy_blocks[-1][1] = max(busy_blocks[-1][1], block_end) #max to get the bigger block event
        else:
            busy_blocks.append([block_start, block_end])

   
    # free gaps are the empty time between busy blocks

    free_gaps = []
    free_from = window_start  # the user is free from here until the next block

    for block_start, block_end in busy_blocks:
        if block_start > free_from:  
            free_gaps.append((free_from, block_start))
        free_from = block_end 

    if free_from < window_end:  
        free_gaps.append((free_from, window_end))


    return [tuple(block) for block in busy_blocks], free_gaps

