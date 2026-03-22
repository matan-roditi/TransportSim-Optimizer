import pytest
from datetime import time, datetime
from simulation.orchestrator import SimulationOrchestrator
from unittest.mock import patch, MagicMock

TEST_NEIGHBORHOODS = {
    "Green_Herzliya": {
        "weight": 1.0,
        "bounds": {"lat": (32.17, 32.18), "lon": (34.84, 34.85)}
    }
}

def test_orchestrator_starts_with_empty_buses():
    # Verify the simulation begins with no active buses on the road
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    assert orchestrator.active_buses == []

def test_orchestrator_starts_with_empty_passengers():
    # Verify the simulation begins with no passengers in the system
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    assert orchestrator.active_passengers == []

def test_orchestrator_clock_initialization():
    # Verify the orchestrator has a clock instance ready to go
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    assert orchestrator.clock is not None

def test_run_tick_advances_clock_time():
    # Verify that calling run_tick actually moves the simulation time forward
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    initial_time = orchestrator.clock.current_time
    orchestrator.run_tick()
    assert orchestrator.clock.current_time != initial_time

def test_run_tick_advances_exactly_one_minute():
    # Verify that the simulation clock moves by exactly 1 minute per tick
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    orchestrator.run_tick()
    # If it starts at 06:00, it must be 06:01
    assert orchestrator.clock.current_time == time(6, 1)

def test_bus_dispatched_during_peak_hour():
    # At 08:00 (Peak), a new bus should be added to the active list
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    # We force the clock to a known dispatch time
    orchestrator.clock.current_dt = datetime.strptime("08:00", "%H:%M")
    orchestrator.run_tick()
    assert len(orchestrator.active_buses) == 1

def test_no_bus_dispatched_on_off_interval():
    # At 08:05 (Peak, but not a 15-min mark), no bus should be created
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    orchestrator.clock.current_dt = datetime.strptime("08:05", "%H:%M")
    orchestrator.run_tick()
    assert len(orchestrator.active_buses) == 0

def test_passenger_generation_increases_active_count():
    # Verify that passengers are added to the system during a tick
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    # We'll assume the generator is called every tick or based on a probability
    orchestrator.run_tick()
    assert len(orchestrator.active_passengers) > 0

def test_frequency_transition_at_ten_am():
    # At 10:15, a bus should NOT be dispatched (off-peak is every 30m)
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    orchestrator.clock.current_dt = datetime.strptime("10:15", "%H:%M")
    orchestrator.run_tick()
    assert len(orchestrator.active_buses) == 0

def test_simulation_ends_at_twenty_two():
    # Verify the orchestrator stops or reflects 'finished' status after 22:00
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    orchestrator.clock.current_dt = datetime.strptime("22:00", "%H:%M")
    # This test depends on how you implement is_running
    assert orchestrator.is_running() is False

@pytest.fixture
def orchestrator():
    # Mock the initialization loaders to keep the test environment isolated and fast
    with patch("simulation.orchestrator.PassengerGenerator"), \
         patch.object(SimulationOrchestrator, "_load_routes", return_value={}), \
         patch.object(SimulationOrchestrator, "_load_travel_times", return_value={}):
        return SimulationOrchestrator(neighborhoods={})


def test_get_travel_time_returns_cached_value(orchestrator):
    # Setup the cache with a known route duration
    orchestrator.travel_times_cache = {("Stop A", "Stop B"): 5}

    result = orchestrator.get_travel_time_minutes("Stop A", "Stop B")

    assert result == 5


def test_get_travel_time_returns_fallback_value(orchestrator):
    # Clear the cache to simulate an unknown edge route
    orchestrator.travel_times_cache = {}

    result = orchestrator.get_travel_time_minutes("Unknown A", "Unknown B")

    assert result == 2


@patch.dict("os.environ", {}, clear=True)
def test_load_travel_times_missing_credentials(orchestrator):
    # Simulate an environment missing PostgreSQL variables
    result = orchestrator._load_travel_times()
    
    assert result == {}


@patch.dict("os.environ", {"PG_HOST": "h", "PG_PORT": "p", "PG_DB": "d", "PG_USER": "u", "PG_PASSWORD": "pw"})
@patch("simulation.orchestrator.psycopg2.connect")
def test_load_travel_times_calculates_minutes_correctly(mock_connect, orchestrator):
    # Setup a mock database response returning exactly sixty seconds
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [("Stop A", "Stop B", 60)]

    mock_conn = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
    mock_connect.return_value.__enter__.return_value = mock_conn

    result = orchestrator._load_travel_times()

    assert result == {("Stop A", "Stop B"): 1}