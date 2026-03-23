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

    # Create a fake navigator that always returns a guaranteed perfect route
    mock_navigator = MagicMock()
    mock_navigator.find_optimal_route.return_value = ("Calculated Start", "Calculated End", 15.0)

    return PassengerGenerator(
        neighborhoods=dummy_neighborhoods,
        navigator=mock_navigator,
        routes_cache={},
        get_bus_time=lambda o, d: 5,
        get_walk_time=lambda o, d: 5
    )

def test_passenger_spawn_lat_within_bounds(mock_brain_generator):
    # Verify the generated passenger latitude is within the defined boundaries
    passenger = mock_brain_generator.generate_passenger()
    assert 32.1 <= passenger.lat <= 32.2

def test_passenger_spawn_lon_within_bounds(mock_brain_generator):
    # Verify the generated passenger longitude is within the defined boundaries
    passenger = mock_brain_generator.generate_passenger()
    assert 34.8 <= passenger.lon <= 34.9

def test_generator_assigns_calculated_origin_stop(mock_brain_generator):
    # Testing that the passenger origin is no longer hardcoded but comes from the navigator
    passenger = mock_brain_generator.generate_passenger()
    assert passenger.origin_stop == "Calculated Start"

def test_generator_assigns_calculated_target_stop(mock_brain_generator):
    # Testing that the passenger destination comes from the navigator routing logic
    passenger = mock_brain_generator.generate_passenger()
    assert passenger.target_stop == "Calculated End"

def test_generator_syncs_passenger_destination_with_navigator_call(mock_brain_generator):
    # Testing that the destination coordinates assigned to the agent exactly match the route search
    passenger = mock_brain_generator.generate_passenger()
    call_kwargs = mock_brain_generator.navigator.find_optimal_route.call_args.kwargs
    assert call_kwargs.get("dest_coords") == passenger.destination

def test_generator_syncs_passenger_origin_with_navigator_call(mock_brain_generator):
    # Testing that the origin coordinates assigned to the agent exactly match the route search
    passenger = mock_brain_generator.generate_passenger()
    call_kwargs = mock_brain_generator.navigator.find_optimal_route.call_args.kwargs
    assert call_kwargs.get("origin_coords") == (passenger.lat, passenger.lon)

def test_generator_raises_value_error_if_no_route_found(mock_brain_generator):
    # Testing that the generator aborts if the passenger cannot physically reach the destination
    mock_brain_generator.navigator.find_optimal_route.return_value = (None, None, float('inf'))
    with pytest.raises(ValueError):
        mock_brain_generator.generate_passenger()

def test_generator_calls_navigator_exactly_once_per_passenger(mock_brain_generator):
    # Testing that the routing algorithm is triggered exactly once per spawn
    mock_brain_generator.generate_passenger()
    assert mock_brain_generator.navigator.find_optimal_route.call_count == 1
