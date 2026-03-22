import pytest
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