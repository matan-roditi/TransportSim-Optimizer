import pytest
from unittest.mock import MagicMock
from agents.passenger import PassengerAgent, PassengerGenerator


@pytest.fixture
def mock_brain_generator():
    """Provides a generator equipped with a mocked navigator for testing."""
    dummy_neighborhoods = {
        "Center": {
            "weight": 1.0,
            "bounds": {"lat": [32.1, 32.2], "lon": [34.8, 34.9]}
        }
    }

    # Create a fake navigator that returns a guaranteed perfect route including the chosen line
    mock_navigator = MagicMock()
    mock_navigator.find_optimal_route.return_value = ("Calculated Start", "Calculated End", "Fast Line", 15.0)

    return PassengerGenerator(
        neighborhoods=dummy_neighborhoods,
        navigator=mock_navigator,
        routes_cache={},
        get_bus_time=lambda o, d: 5,
        get_walk_time=lambda o, d: 5
    )


def test_generator_assigns_chosen_line_to_passenger(mock_brain_generator):
    # Testing that the passenger knows exactly which bus line to wait for
    passenger = mock_brain_generator.generate_passenger("Center", "Center")
    assert passenger.chosen_line == "Fast Line"


def test_passenger_spawn_lat_within_bounds(mock_brain_generator):
    # Verify the generated passenger latitude is within the defined boundaries
    passenger = mock_brain_generator.generate_passenger("Center", "Center")
    assert 32.1 <= passenger.lat <= 32.2

def test_passenger_spawn_lon_within_bounds(mock_brain_generator):
    # Verify the generated passenger longitude is within the defined boundaries
    passenger = mock_brain_generator.generate_passenger("Center", "Center")
    assert 34.8 <= passenger.lon <= 34.9

def test_generator_assigns_calculated_origin_stop(mock_brain_generator):
    # Testing that the passenger origin is no longer hardcoded but comes from the navigator
    passenger = mock_brain_generator.generate_passenger("Center", "Center")
    assert passenger.origin_stop == "Calculated Start"

def test_generator_assigns_calculated_target_stop(mock_brain_generator):
    # Testing that the passenger destination comes from the navigator routing logic
    passenger = mock_brain_generator.generate_passenger("Center", "Center")
    assert passenger.target_stop == "Calculated End"

def test_generator_syncs_passenger_destination_with_navigator_call(mock_brain_generator):
    # Testing that the destination coordinates assigned to the agent exactly match the route search
    passenger = mock_brain_generator.generate_passenger("Center", "Center")
    call_kwargs = mock_brain_generator.navigator.find_optimal_route.call_args.kwargs
    assert call_kwargs.get("dest_coords") == passenger.destination

def test_generator_syncs_passenger_origin_with_navigator_call(mock_brain_generator):
    # Testing that the origin coordinates assigned to the agent exactly match the route search
    passenger = mock_brain_generator.generate_passenger("Center", "Center")
    call_kwargs = mock_brain_generator.navigator.find_optimal_route.call_args.kwargs
    assert call_kwargs.get("origin_coords") == (passenger.lat, passenger.lon)

def test_generator_raises_value_error_if_no_route_found(mock_brain_generator):
    # Testing that the generator aborts if the passenger cannot physically reach the destination
    mock_brain_generator.navigator.find_optimal_route.return_value = (None, None, None, float('inf'))
    with pytest.raises(ValueError):
        mock_brain_generator.generate_passenger("Center", "Center")

def test_generator_calls_navigator_exactly_once_per_passenger(mock_brain_generator):
    # Testing that the routing algorithm is triggered exactly once per spawn
    mock_brain_generator.generate_passenger("Center", "Center")
    assert mock_brain_generator.navigator.find_optimal_route.call_count == 1

def test_generator_spawns_scheduled_passengers(mock_brain_generator):
    # Setup a dummy schedule for the mock generator
    mock_brain_generator.llm_schedule = [
        {"departing_time": "08:00", "origin_neighborhood": "Center", "destination_neighborhood": "Center"},
        {"departing_time": "08:00", "origin_neighborhood": "Center", "destination_neighborhood": "Center"},
        {"departing_time": "09:00", "origin_neighborhood": "Center", "destination_neighborhood": "Center"}
    ]
    
    passengers = mock_brain_generator.generate_passengers_for_time("08:00")
    
    # Verify exactly two passengers were spawned for the matching time
    assert len(passengers) == 2

def test_generator_ignores_empty_or_mismatched_schedule(mock_brain_generator):
    # Verify the generator returns an empty list if no times match the clock
    mock_brain_generator.llm_schedule = [
        {"departing_time": "08:00", "origin_neighborhood": "Center", "destination_neighborhood": "Center"}
    ]
    
    passengers = mock_brain_generator.generate_passengers_for_time("09:00")
    
    # Verify no passengers were spawned for the wrong time
    assert len(passengers) == 0