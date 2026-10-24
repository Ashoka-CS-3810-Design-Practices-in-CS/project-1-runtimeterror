# Performance results

Median of repeated runs, seeded random calendars, run by `python -m samples.benchmark`.

| Operation | Target | 1000 events | 5000 events |
|---|---|---|---|
| Conflict check after one change (Algorithm 3) | under 500 ms | 0.001 ms | 0.003 ms |
| Create an event end to end (validate, store, save, check) | under 500 ms | 1.345 ms | 1.176 ms |
| Best-time finder, 2-week window | under 2000 ms | 0.060 ms | 0.078 ms |
| Load the saved calendar at startup | under 3000 ms | 3.579 ms | 15.469 ms |
| Full-calendar conflict scan (Algorithm 4) | none set | 0.086 ms | 1.748 ms |
| Insert plus delete one event (sorted array) | none set | 0.005 ms | 0.007 ms |
