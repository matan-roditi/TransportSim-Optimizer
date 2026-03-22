import pytest
from agents.bus import BusAgent, RouteNavigator
from agents.passenger import PassengerAgent

# Test route data fixture
TEST_ROUTE_DATA = {
    "line_id": "Line_1",
    "stops": ["Stop_A", "Stop_B", "Stop_C", "Stop_D"]
}

def test_bus_starts_empty():
    # Verify a new bus starts empty 
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA, capacity=50)
    assert len(bus.passengers) == 0

def test_bus_capacity_assignment():
    # Verify a new bus has the correct maximum capacity of 50
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA, capacity=50)
    assert bus.capacity == 50

def test_bus_boarding_limit_return_value():
    # Verify the board_passengers method correctly returns the number of boarded passengers
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA, capacity=50)
    potential_passengers = list(range(55))
    boarded_count = bus.board_passengers(potential_passengers)
    assert boarded_count == 50

def test_bus_boarding_limit_passenger_list():
    # Verify the bus strictly enforces the 50-passenger limit in its internal list
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA, capacity=50)
    potential_passengers = list(range(55))
    bus.board_passengers(potential_passengers)
    assert len(bus.passengers) == 50

def test_base_dwell_time():
    # Verify the bus stops for exactly 30 seconds even with 1 passenger
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA)
    duration = bus.calculate_stop_duration(boarding_count=1, exiting_count=0)
    assert duration == 30

def test_extra_passenger_penalty():
    # Verify that 10 passengers cause a 60-second delay
    # 30s base + (6 extra passengers * 5s) = 60s
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA)
    duration = bus.calculate_stop_duration(boarding_count=10, exiting_count=0)
    assert duration == 60

def test_stop_for_exiting_passengers_only():
    # Verify the bus stops for 30s if someone is getting off, 
    # even if 0 people are boarding.
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA)
    
    # boarding_count=0, exiting_count=1
    duration = bus.calculate_stop_duration(boarding_count=0, exiting_count=1)
    assert duration == 30

def test_no_stop_if_empty_and_no_boarders():
    # If no one is on the bus to exit and no one is at the stop to board,
    # the bus should ideally spend 0 seconds at the stop.
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA)
    
    duration = bus.calculate_stop_duration(boarding_count=0, exiting_count=0)
    assert duration == 0

def test_extra_passenger_penalty_with_exiting():
    # Verify that 7 boarding passengers and 5 exiting passengers still results in a 45-second stop
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA)
    duration = bus.calculate_stop_duration(boarding_count=7, exiting_count=5)
    assert duration == 45

def test_max_time_boarding_vs_exiting():
    # Scenario: 10 passengers boarding (60s) and 5 passengers exiting (35s)
    # The bus should take the maximum of the two: 60s
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA)
    duration = bus.calculate_stop_duration(boarding_count=10, exiting_count=5)
    assert duration == 60


def test_max_time_exiting_heavy():
    # Scenario: 4 passengers boarding (30s) and 10 passengers exiting (60s)
    # The bus should take the maximum: 60s
    bus = BusAgent(bus_id="Line_1", route_data=TEST_ROUTE_DATA)
    duration = bus.calculate_stop_duration(boarding_count=4, exiting_count=10)
    assert duration == 60


@pytest.fixture
def mock_navigator():
    """Provides a fresh navigator with a linear route."""
    return RouteNavigator(line_id="Line A", stops=["Alpha", "Beta", "Gamma", "Delta"])


def test_navigator_reaches_future_stop(mock_navigator):
    assert mock_navigator.reaches_stop("Gamma") is True


def test_navigator_does_not_reach_passed_stop(mock_navigator):
    mock_navigator.advance()
    mock_navigator.advance()

    assert mock_navigator.reaches_stop("Alpha") is False


def test_navigator_does_not_reach_off_route_stop(mock_navigator):
    assert mock_navigator.reaches_stop("Omega") is False


@pytest.fixture
def bus_with_two_seats():
    """Provides a bus with a strict capacity limit of two for boarding tests."""
    route_data = {
        "line_id": "Line A",
        "stops": ["Start", "Middle", "End"]
    }
    return BusAgent(bus_id="TestBus", route_data=route_data, capacity=2)


@pytest.fixture
def waiting_crowd():
    """Provides a group of three passengers waiting at the starting stop."""
    p_one = PassengerAgent(lat=0, lon=0, destination=(0,0), origin_stop="Start", target_stop="End")
    p_two = PassengerAgent(lat=0, lon=0, destination=(0,0), origin_stop="Start", target_stop="End")
    p_three = PassengerAgent(lat=0, lon=0, destination=(0,0), origin_stop="Start", target_stop="End")
    return [p_one, p_two, p_three]


def test_bus_boards_passengers_up_to_capacity(bus_with_two_seats, waiting_crowd):
    # Testing that exactly two passengers make it onto the bus when capacity is two
    bus_with_two_seats.process_boarding(waiting_crowd)
    
    assert len(bus_with_two_seats.passengers) == 2


def test_bus_leaves_unboarded_passengers_in_queue(bus_with_two_seats, waiting_crowd):
    # Testing that the single passenger who could not fit is returned to the waiting pool
    remaining_passengers = bus_with_two_seats.process_boarding(waiting_crowd)
    
    assert len(remaining_passengers) == 1


def test_bus_ignores_passengers_at_wrong_stop(bus_with_two_seats):
    # Testing that a passenger waiting at a different station is skipped
    wrong_stop_passenger = PassengerAgent(
        lat=0, lon=0, destination=(0,0), origin_stop="Middle", target_stop="End"
    )
    bus_with_two_seats.process_boarding([wrong_stop_passenger])
    
    assert len(bus_with_two_seats.passengers) == 0


def test_bus_ignores_passengers_with_wrong_destination(bus_with_two_seats):
    # Testing that a passenger wanting to go to an off-route stop is rejected
    wrong_dest_passenger = PassengerAgent(
        lat=0, lon=0, destination=(0,0), origin_stop="Start", target_stop="OffRoute"
    )
    bus_with_two_seats.process_boarding([wrong_dest_passenger])
    
    assert len(bus_with_two_seats.passengers) == 0
