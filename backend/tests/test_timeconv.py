#unit tests for the time representation 
import pytest
from app.models.timeconv import clock_to_minutes, from_minutes, to_minutes


def test_reference_date_is_minute_zero():
    assert to_minutes("2000-01-01T00:00") == 0

def test_crossing_midnight_is_plain_subtraction():
    late = to_minutes("2026-09-21T23:00")
    early_next_day = to_minutes("2026-09-22T01:00")
    assert early_next_day - late == 120


def test_round_trip():
    text = "2026-10-13T10:45"
    assert from_minutes(to_minutes(text)) == text


@pytest.mark.parametrize("bad", ["2026-10-13T25:70", "hello", "2026-13-01T10:00", ""])
def test_unreadable_time_raises(bad):
    with pytest.raises(ValueError):
        to_minutes(bad)


def test_clock_time():
    assert clock_to_minutes("21:00") == 1260
    with pytest.raises(ValueError):
        clock_to_minutes("25:70")       