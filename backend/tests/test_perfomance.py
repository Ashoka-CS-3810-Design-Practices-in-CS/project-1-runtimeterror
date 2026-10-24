"""Assignment 3, section 3.7: the targets from Assignment 1.

Timings come from samples/benchmark.py (run `python -m samples.benchmark` for
the full table). Seeded random calendars of 1,000 and 5,000 events.
"""
import pytest

from samples.benchmark import TARGETS_MS, measure


@pytest.mark.parametrize("n", [1000, 5000])
def test_main_operations_meet_the_assignment_1_targets(n, tmp_path):
    results = measure(n, str(tmp_path / f"perf{n}.db"))

    assert results["events"] == n
    assert results["conflict_check_ms"] < TARGETS_MS["conflict_check"]
    assert results["create_event_ms"] < TARGETS_MS["conflict_check"]
    assert results["finder_2_weeks_ms"] < TARGETS_MS["finder_2_weeks"]
    assert results["load_calendar_ms"] < TARGETS_MS["load_calendar"]