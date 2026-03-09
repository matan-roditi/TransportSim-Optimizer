import pytest
from agents.bus import BusAgent

def test_bus_starts_empty():
    # Verify a new bus starts empty 
    bus = BusAgent(bus_id="Line_1", capacity=50)
    assert len(bus.passengers) == 0

def test_bus_capacity_assignment():
    # Verify a new bus has the correct maximum capacity of 50
    bus = BusAgent(bus_id="Line_1", capacity=50)
    assert bus.capacity == 50

def test_bus_boarding_limit_return_value():
    # Verify the board_passengers method correctly returns the number of boarded passengers
    bus = BusAgent(bus_id="Line_1", capacity=50)
    potential_passengers = list(range(55))
    boarded_count = bus.board_passengers(potential_passengers)
    assert boarded_count == 50

def test_bus_boarding_limit_passenger_list():
    # Verify the bus strictly enforces the 50-passenger limit in its internal list
    bus = BusAgent(bus_id="Line_1", capacity=50)
    potential_passengers = list(range(55))
    bus.board_passengers(potential_passengers)
    assert len(bus.passengers) == 50

def test_base_dwell_time():
    # Verify the bus stops for exactly 30 seconds even with 1 passenger
    bus = BusAgent(bus_id="Line_1")
    duration = bus.calculate_stop_duration(boarding_count=1)
    assert duration == 30

def test_extra_passenger_penalty():
    # Verify that 10 passengers cause a 60-second delay
    # 30s base + (6 extra passengers * 5s) = 60s
    bus = BusAgent(bus_id="Line_1")
    duration = bus.calculate_stop_duration(boarding_count=10)
    assert duration == 60