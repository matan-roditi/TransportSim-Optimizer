import pytest
from typing import Callable, Tuple, Dict, List
from agents.passenger import PassengerNavigator

@pytest.fixture
def mock_stops():
    # Provides a small set of mock stops with simple grid coordinates for easy distance math
    return {
        "Center Station": (0.0, 0.0),
        "North Station": (1.0, 0.0),
        "East Station": (0.0, 1.0),
        "Far Away Station": (10.0, 10.0)
    }

@pytest.fixture
def navigator(mock_stops):
    # Initializes the navigator with our mock stops
    return PassengerNavigator(stops=mock_stops)


def test_navigator_finds_exact_stop_when_coordinates_match(navigator):
    # Testing that standing exactly on the Center Station coordinates makes it the absolute closest
    closest = navigator.get_closest_stops(lat=0.0, lon=0.0, count=1)

    assert closest[0] == "Center Station"


def test_navigator_returns_requested_number_of_stops(navigator):
    # Testing that the method limits the returned list to the specified count parameter
    closest = navigator.get_closest_stops(lat=0.0, lon=0.0, count=2)

    assert len(closest) == 2


def test_navigator_sorts_stops_by_distance(navigator):
    # Testing that standing near the North Station makes it first, followed by the Center Station
    closest = navigator.get_closest_stops(lat=0.8, lon=0.0, count=2)

    assert closest == ["North Station", "Center Station"]

@pytest.fixture
def mock_routes_cache() -> Dict[str, List[str]]:
    # Provides a route that specifically connects North Station to Center Station
    return {
        "Line 1": ["North Station", "Center Station", "South Station"],
        "Line 2": ["East Station", "West Station"]
    }


@pytest.fixture
def mock_bus_time_callback() -> Callable[[str, str], int]:
    # Simulates a database query for bus travel times
    def get_time(origin_stop: str, dest_stop: str) -> int:
        routes = {
            ("North Station", "Center Station"): 5,
        }
        return routes.get((origin_stop, dest_stop), 999)
    return get_time


@pytest.fixture
def mock_walk_time_callback() -> Callable[[Tuple[float, float], Tuple[float, float]], int]:
    # Simulates OSRM walking time API returning a flat two minutes
    def get_time(coord_a: Tuple[float, float], coord_b: Tuple[float, float]) -> int:
        return 2
    return get_time


def test_optimizer_selects_valid_connected_origin(
    navigator, mock_routes_cache, mock_bus_time_callback, mock_walk_time_callback
):
    # Testing that the optimizer picks North Station because Line 1 connects it to Center Station
    origin_stop, target_stop, chosen_line, total_time = navigator.find_optimal_route(
        origin_coords=(0.9, 0.0),
        dest_coords=(0.0, 0.1),
        routes_cache=mock_routes_cache,
        get_bus_time=mock_bus_time_callback,
        get_walk_time=mock_walk_time_callback
    )
    
    assert origin_stop == "North Station"


def test_optimizer_selects_valid_connected_target(
    navigator, mock_routes_cache, mock_bus_time_callback, mock_walk_time_callback
):
    # Testing the destination side of the connected route
    origin_stop, target_stop, chosen_line, total_time = navigator.find_optimal_route(
        origin_coords=(0.9, 0.0),
        dest_coords=(0.0, 0.1),
        routes_cache=mock_routes_cache,
        get_bus_time=mock_bus_time_callback,
        get_walk_time=mock_walk_time_callback
    )
    
    assert target_stop == "Center Station"


def test_optimizer_ignores_unconnected_stops(
    navigator, mock_routes_cache, mock_bus_time_callback, mock_walk_time_callback
):
    # Testing that East Station is ignored because no bus goes from East to Center
    origin_stop, target_stop, chosen_line, total_time = navigator.find_optimal_route(
        origin_coords=(0.1, 0.9),
        dest_coords=(0.0, 0.1),
        routes_cache=mock_routes_cache,
        get_bus_time=mock_bus_time_callback,
        get_walk_time=mock_walk_time_callback
    )
    
    assert origin_stop != "East Station"