import pytest
from agents.passenger import PassengerAgent, PassengerGenerator

# Mock data for testing Herzliya neighborhood distribution
TEST_NEIGHBORHOODS = {
    "Green_Herzliya": {
        "weight": 1.0,  # 100% for simple boundary testing
        "bounds": {"lat": (32.17, 32.18), "lon": (34.84, 34.85)}
    }
}


def test_passenger_spawn_lat_within_bounds():
    # Verify the generated passenger's latitude is within the defined boundaries
    generator = PassengerGenerator(TEST_NEIGHBORHOODS)
    passenger = generator.generate_passenger()
    assert 32.17 <= passenger.lat <= 32.18


def test_passenger_spawn_lon_within_bounds():
    # Verify the generated passenger's longitude is within the defined boundaries
    generator = PassengerGenerator(TEST_NEIGHBORHOODS)
    passenger = generator.generate_passenger()
    assert 34.84 <= passenger.lon <= 34.85


def test_passenger_has_destination_assigned():
    # Ensure every passenger is created with a target destination
    generator = PassengerGenerator(TEST_NEIGHBORHOODS)
    passenger = generator.generate_passenger()
    assert passenger.destination is not None


def test_passenger_destination_format_is_tuple():
    # Verify the destination is stored as a (lat, lon) tuple for OSRM queries
    generator = PassengerGenerator(TEST_NEIGHBORHOODS)
    passenger = generator.generate_passenger()
    assert isinstance(passenger.destination, tuple)


def test_distribution_weighting_accuracy():
    # Statistical test to verify that weights are respected over 1000 samples
    weighted_neighborhoods = {
        "Area_A": {"weight": 0.8, "bounds": {"lat": (0, 1), "lon": (0, 1)}},
        "Area_B": {"weight": 0.2, "bounds": {"lat": (10, 11), "lon": (10, 11)}}
    }
    generator = PassengerGenerator(weighted_neighborhoods)
    passengers = [generator.generate_passenger() for _ in range(1000)]

    # Count passengers spawned in Area A
    area_a_count = sum(1 for p in passengers if 0 <= p.lat <= 1)
    # Assert that roughly 80% of passengers were spawned in Area A
    assert 750 <= area_a_count <= 850


@pytest.fixture
def basic_passenger():
    """Provides a standard passenger instance for testing data attributes."""
    return PassengerAgent(
        lat=32.1624,
        lon=34.8447,
        destination=(32.1624, 34.8447),
        origin_stop="Central Station",
        target_stop="North Station"
    )


@pytest.fixture
def mock_generator():
    """Provides a generator initialized with dummy neighborhood bounds."""
    dummy_neighborhoods = {
        "Center": {
            "weight": 1.0,
            "bounds": {"lat": [32.1, 32.2], "lon": [34.8, 34.9]}
        }
    }
    return PassengerGenerator(dummy_neighborhoods)


def test_passenger_agent_holds_origin_stop(basic_passenger):
    # Verify that a PassengerAgent correctly stores the name of the boarding stop
    assert basic_passenger.origin_stop == "Central Station"


def test_passenger_agent_holds_target_stop(basic_passenger):
    # Verify that a PassengerAgent correctly stores the name of the alighting stop
    assert basic_passenger.target_stop == "North Station"


def test_passenger_generator_assigns_origin_stop_as_string(mock_generator):
    # Ensure the generator always assigns a string type to origin_stop (not None or int)
    passenger = mock_generator.generate_passenger()
    assert isinstance(passenger.origin_stop, str)


def test_passenger_generator_assigns_target_stop_as_string(mock_generator):
    # Ensure the generator always assigns a string type to target_stop (not None or int)
    passenger = mock_generator.generate_passenger()
    assert isinstance(passenger.target_stop, str)


def test_passenger_generator_assigns_non_empty_origin(mock_generator):
    # Verify the generator does not produce a passenger with a blank boarding stop name
    passenger = mock_generator.generate_passenger()
    assert len(passenger.origin_stop) > 0


def test_passenger_generator_assigns_non_empty_target(mock_generator):
    # Verify the generator does not produce a passenger with a blank alighting stop name
    passenger = mock_generator.generate_passenger()
    assert len(passenger.target_stop) > 0