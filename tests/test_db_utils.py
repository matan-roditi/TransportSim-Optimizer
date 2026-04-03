import pytest
from database.db_utils import fetch_travel_times_summary


def test_fetch_travel_times_is_string():
    # Verify the database utility returns a string object.
    result = fetch_travel_times_summary()
    assert isinstance(result, str)


def test_fetch_travel_times_not_empty():
    # Ensure the database actually returns data and not an empty string.
    result = fetch_travel_times_summary()
    assert len(result) > 0


def test_fetch_travel_times_contains_hebrew_brackets():
    # Confirm the output format uses the expected bracket notation for stops.
    result = fetch_travel_times_summary()
    assert "[" in result and "]" in result


def test_fetch_travel_times_contains_time_marker():
    # Verify that the duration 'm' suffix is present in the output lines.
    result = fetch_travel_times_summary()
    assert "m" in result
