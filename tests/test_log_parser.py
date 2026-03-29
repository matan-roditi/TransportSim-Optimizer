import pytest
import pandas as pd
from ui.log_parser import parse_simulation_logs, get_simulation_state

@pytest.fixture
def parsed_logs():
    # Provide a mock dictionary of stops to resolve bus coordinates
    mock_stops = {
        "כנפי נשרים/מגן דוד": (32.1600, 34.8400)
    }

    # Provide raw log lines exactly as they appear in simulation_output.log
    mock_logs = [
        "2026-03-29 13:57:08,239 - INFO - [06:00] passenger #1 deployed with origin:(32.1511, 34.8495), dest:(32.1806, 34.8042)",
        "2026-03-29 13:57:08,239 - INFO - [06:00] Bus_Line1_0600 at כנפי נשרים/מגן דוד | Left: 0 | Boarded: 0 | On-board: 0 | continued without stopping"
    ]

    return parse_simulation_logs(mock_logs, mock_stops)


def test_log_parser_returns_dataframe(parsed_logs):
    assert isinstance(parsed_logs, pd.DataFrame)


def test_log_parser_returns_correct_number_of_rows(parsed_logs):
    assert len(parsed_logs) == 2


def test_log_parser_extracts_passenger_type(parsed_logs):
    assert parsed_logs[parsed_logs['entity_id'] == 'passenger #1'].iloc[0]['type'] == "passenger"


def test_log_parser_extracts_passenger_icon(parsed_logs):
    assert parsed_logs[parsed_logs['entity_id'] == 'passenger #1'].iloc[0]['icon'] == "🚶"


def test_log_parser_extracts_bus_type(parsed_logs):
    assert parsed_logs[parsed_logs['entity_id'] == 'Bus_Line1_0600'].iloc[0]['type'] == "bus"


def test_log_parser_extracts_bus_icon(parsed_logs):
    assert parsed_logs[parsed_logs['entity_id'] == 'Bus_Line1_0600'].iloc[0]['icon'] == "🚌"


def test_log_parser_extracts_bus_latitude(parsed_logs):
    assert parsed_logs[parsed_logs['entity_id'] == 'Bus_Line1_0600'].iloc[0]['lat'] == 32.1600


@pytest.fixture
def mock_simulation_dataframe():
    # Create a mock dataframe of parsed events where a bus has moved
    data = [
        {'time': '06:00', 'type': 'bus', 'entity_id': 'Bus_1', 'lat': 32.1, 'lon': 34.1, 'icon': '🚌'},
        {'time': '06:15', 'type': 'bus', 'entity_id': 'Bus_1', 'lat': 32.2, 'lon': 34.2, 'icon': '🚌'}
    ]
    return pd.DataFrame(data)


def test_get_state_excludes_future_events_count(mock_simulation_dataframe):
    # Verify the event count at a time before the second movement
    state_df = get_simulation_state(mock_simulation_dataframe, '06:10')
    assert len(state_df) == 1


def test_get_state_retains_past_event_time(mock_simulation_dataframe):
    # Verify the specific event time matches the past location
    state_df = get_simulation_state(mock_simulation_dataframe, '06:10')
    assert state_df.iloc[0]['time'] == '06:00'


def test_get_state_maintains_entity_count(mock_simulation_dataframe):
    # Verify only one row exists per entity even after multiple movements
    state_df = get_simulation_state(mock_simulation_dataframe, '06:20')
    assert len(state_df) == 1


def test_get_state_updates_to_latest_location(mock_simulation_dataframe):
    # Verify the entity location reflects the most recent movement
    state_df = get_simulation_state(mock_simulation_dataframe, '06:20')
    assert state_df.iloc[0]['lat'] == 32.2
