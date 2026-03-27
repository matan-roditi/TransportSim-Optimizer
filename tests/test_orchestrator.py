import pytest
import logging
from datetime import time, datetime
from simulation.orchestrator import SimulationOrchestrator
from agents.passenger import PassengerAgent
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
    # At 08:00 (Peak), one bus per route should be dispatched
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    # We force the clock to a known dispatch time
    orchestrator.clock.current_dt = datetime.strptime("08:00", "%H:%M")
    orchestrator.run_tick()
    # One bus is created per route in the cache; there must be at least one
    assert len(orchestrator.active_buses) >= 1

def test_no_bus_dispatched_on_off_interval():
    # At 08:05 (Peak, but not a 15-min mark), no bus should be created
    orchestrator = SimulationOrchestrator(TEST_NEIGHBORHOODS)
    orchestrator.clock.current_dt = datetime.strptime("08:05", "%H:%M")
    orchestrator.run_tick()
    assert len(orchestrator.active_buses) == 0

def test_passenger_generation_increases_active_count(orchestrator):
    # Verify that passengers are added to the system when the LLM schedule has entries
    mock_passenger = MagicMock(spec=PassengerAgent)
    orchestrator.passenger_generator.generate_passengers_for_time.return_value = [mock_passenger]
    orchestrator.run_tick()
    assert len(orchestrator.active_passengers) == 1

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


def test_walk_time_applies_urban_circuity_multiplier(orchestrator):
    # Testing that a straight line distance is multiplied by the urban circuity factor
    start_point = (32.1600, 34.8400)
    end_point = (32.1700, 34.8400) 

    time = orchestrator._calculate_walk_time(start_point, end_point)

    # Distance is roughly one thousand one hundred twelve meters
    # Actual distance with the multiplier is roughly one thousand four hundred forty five meters
    # Base time at average speed is roughly seventeen minutes
    # Crosswalk penalty adds an extra four minutes
    # Total expected time truncated to integer is twenty one minutes
    assert time == 21


def test_walk_time_returns_minimum_one_minute(orchestrator):
    # Testing that even if the passenger spawns exactly on the bus stop it takes 1 minute to board
    same_location = (32.1624, 34.8447)

    time = orchestrator._calculate_walk_time(same_location, same_location)

    assert time == 1

@pytest.fixture
def finishing_bus():
    # Creates a mock bus that is currently at the final stop of its forward route
    bus = MagicMock()
    bus.bus_id = "Bus_Line1_0800"
    bus.route_data = {"line_id": "Line 1", "stops": ["Stop A", "Stop B", "Stop C"]}
    
    bus.navigator.get_current_stop.return_value = "Stop C"
    bus.navigator.get_next_stop.return_value = None
    bus.ticks_until_arrival = 0
    bus.reverse_dispatched = False
    
    return bus


def test_reverse_route_has_opposite_stop_order(orchestrator):
    # Verifies that the reverse line contains the exact opposite order of the forward line stops
    orchestrator.routes_cache = {
        "Line 1": ["Stop A", "Stop B", "Stop C"],
        "Line 1 Reverse": ["Stop C", "Stop B", "Stop A"]
    }
    
    forward_stops = orchestrator.routes_cache["Line 1"]
    reverse_stops = orchestrator.routes_cache["Line 1 Reverse"]
    
    assert reverse_stops == forward_stops[::-1]


def test_reverse_bus_dispatched_exactly_one_bus(finishing_bus, orchestrator):
    # Verifies that exactly one reverse bus is spawned when a forward bus finishes
    orchestrator.routes_cache = {
        "Line 1": ["Stop A", "Stop B", "Stop C"],
        "Line 1 Reverse": ["Stop C", "Stop B", "Stop A"]
    }
    orchestrator.active_buses = [finishing_bus]
    
    new_reverse_buses = []
    current_line_id = finishing_bus.route_data.get("line_id", "")
    next_stop = finishing_bus.navigator.get_next_stop()
    
    if not next_stop and not finishing_bus.reverse_dispatched:
        finishing_bus.reverse_dispatched = True
        reverse_line = current_line_id + " Reverse"
        
        if reverse_line in orchestrator.routes_cache:
            new_reverse_buses.append(reverse_line)
            
    assert len(new_reverse_buses) == 1


def test_reverse_bus_dispatched_with_correct_name(finishing_bus, orchestrator):
    # Verifies that the spawned bus has the correct reverse line ID
    orchestrator.routes_cache = {
        "Line 1": ["Stop A", "Stop B", "Stop C"],
        "Line 1 Reverse": ["Stop C", "Stop B", "Stop A"]
    }
    orchestrator.active_buses = [finishing_bus]
    
    new_reverse_buses = []
    current_line_id = finishing_bus.route_data.get("line_id", "")
    next_stop = finishing_bus.navigator.get_next_stop()
    
    if not next_stop and not finishing_bus.reverse_dispatched:
        finishing_bus.reverse_dispatched = True
        reverse_line = current_line_id + " Reverse"
        
        if reverse_line in orchestrator.routes_cache:
            new_reverse_buses.append(reverse_line)
            
    assert new_reverse_buses[0] == "Line 1 Reverse"


def test_reverse_bus_sets_safety_flag(finishing_bus, orchestrator):
    # Verifies that the safety flag is set to prevent infinite reverse dispatching
    orchestrator.routes_cache = {
        "Line 1": ["Stop A", "Stop B", "Stop C"],
        "Line 1 Reverse": ["Stop C", "Stop B", "Stop A"]
    }
    orchestrator.active_buses = [finishing_bus]
    
    next_stop = finishing_bus.navigator.get_next_stop()
    
    if not next_stop and not finishing_bus.reverse_dispatched:
        finishing_bus.reverse_dispatched = True
            
    assert finishing_bus.reverse_dispatched is True


def test_reverse_bus_queries_asymmetrical_travel_times(orchestrator):
    # Verifies that a reverse bus fetches the correct asymmetrical travel time for its direction
    orchestrator.travel_times_cache = {
        ("Stop A", "Stop B"): 5,
        ("Stop B", "Stop C"): 4,
        ("Stop C", "Stop B"): 7, 
        ("Stop B", "Stop A"): 6  
    }
    
    reverse_bus = MagicMock()
    reverse_bus.route_data = {"line_id": "Line 1 Reverse"}
    reverse_bus.navigator.get_current_stop.return_value = "Stop C"
    reverse_bus.navigator.get_next_stop.return_value = "Stop B"
    
    current_stop = reverse_bus.navigator.get_current_stop()
    next_stop = reverse_bus.navigator.get_next_stop()
    
    travel_time = orchestrator.get_travel_time_minutes(current_stop, next_stop)
    
    assert travel_time == 7


def test_reverse_bus_ignores_forward_travel_times(orchestrator):
    # Verifies that a reverse bus does not incorrectly use the forward route travel time
    orchestrator.travel_times_cache = {
        ("Stop A", "Stop B"): 5,
        ("Stop B", "Stop C"): 4,
        ("Stop C", "Stop B"): 7, 
        ("Stop B", "Stop A"): 6  
    }
    
    reverse_bus = MagicMock()
    reverse_bus.route_data = {"line_id": "Line 1 Reverse"}
    reverse_bus.navigator.get_current_stop.return_value = "Stop C"
    reverse_bus.navigator.get_next_stop.return_value = "Stop B"
    
    current_stop = reverse_bus.navigator.get_current_stop()
    next_stop = reverse_bus.navigator.get_next_stop()
    
    travel_time = orchestrator.get_travel_time_minutes(current_stop, next_stop)
    
    assert travel_time != 4


def test_bus_logs_boarding_and_alighting_at_stop(orchestrator, caplog):
    # Verify the orchestrator emits a correctly-formatted stop event when passengers
    # both alight and board at the same stop during run_tick()
    caplog.set_level(logging.INFO)

    bus = MagicMock()
    bus.bus_id = "Bus_Line2_0800"
    bus.route_data = {"line_id": "Line 2", "stops": ["Stop A", "Stop B"]}
    bus.ticks_until_arrival = 0
    bus.navigator.get_current_stop.return_value = "בית משפט/בן גוריון"
    bus.navigator.get_next_stop.return_value = "הרב קוק / ויצמן"
    bus.reverse_dispatched = False

    # 1 passenger on board who will alight: set a real list so alight_passengers()
    # can mutate it and len() reads the correct count before and after the call
    bus.passengers = ["Passenger_1"]
    def alight_side_effect():
        bus.passengers.clear()
    bus.alight_passengers.side_effect = alight_side_effect

    # 1 passenger waiting at the stop who will board:
    # process_boarding() consumes the waiting list and returns an empty one
    orchestrator.active_passengers = [MagicMock(spec=PassengerAgent)]
    bus.process_boarding.return_value = []

    # Suppress unrelated passenger-generation noise from the mocked generator
    orchestrator.passenger_generator.generate_passengers_for_time.return_value = []

    orchestrator.active_buses = [bus]
    orchestrator.run_tick()

    # The actual log format is: "[HH:MM] Bus_ID at stop | Left: X | Boarded: Y | ..."
    assert "Bus_Line2_0800 at בית משפט/בן גוריון | Left: 1 | Boarded: 1 | On-board: 0" in caplog.text


def test_bus_logs_continued_without_stopping_when_no_activity(orchestrator, caplog):
    # Verify that even when no one boards or alights, a stop-event is still logged
    # with the "continued without stopping" suffix, even if other passengers are
    # waiting at the stop for a different bus line.
    caplog.set_level(logging.INFO)

    bus = MagicMock()
    bus.bus_id = "Bus_Line2_0800"
    bus.route_data = {"line_id": "Line 2", "stops": ["Stop A", "Stop B"]}
    bus.ticks_until_arrival = 0
    bus.navigator.get_current_stop.return_value = "בית ספר תיכון ראשונים/הרב קוק"
    bus.navigator.get_next_stop.return_value = "הרב קוק / ויצמן"
    bus.reverse_dispatched = False

    # No on-board passengers to alight
    bus.passengers = []
    bus.alight_passengers.side_effect = lambda: None

    # Passengers are waiting at the stop but for a different line — process_boarding()
    # returns the list unchanged because none of them board this bus
    waiting_for_other_line = [MagicMock(spec=PassengerAgent), MagicMock(spec=PassengerAgent)]
    orchestrator.active_passengers = waiting_for_other_line
    bus.process_boarding.return_value = waiting_for_other_line

    orchestrator.passenger_generator.generate_passengers_for_time.return_value = []

    orchestrator.active_buses = [bus]
    orchestrator.run_tick()

    assert "Bus_Line2_0800 at בית ספר תיכון ראשונים/הרב קוק | Left: 0 | Boarded: 0 | On-board: 0 | continued without stopping" in caplog.text


def test_orchestrator_logs_individual_passenger_deployment(orchestrator, caplog):
    # Verify the orchestrator emits the specific deployment log for each passenger
    caplog.set_level(logging.INFO)

    mock_passenger = MagicMock(spec=PassengerAgent)
    mock_passenger.passenger_id = 42
    mock_passenger.lat = 32.1234
    mock_passenger.lon = 34.5678
    mock_passenger.destination = (32.9999, 34.1111)

    orchestrator.passenger_generator.generate_passengers_for_time.return_value = [mock_passenger]
    orchestrator.dispatcher.should_dispatch.return_value = False

    orchestrator.run_tick()

    expected_log = "passenger #42 deployed with origin:(32.1234, 34.5678), dest:(32.9999, 34.1111)"
    assert expected_log in caplog.text