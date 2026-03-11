import pytest
from agents.passenger import PassengerGenerator

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