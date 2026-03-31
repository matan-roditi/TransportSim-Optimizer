import pytest
from database.metrics import MetricsCollector
from simulation.config import HERZLIYA_NEIGHBORHOODS


@pytest.fixture
def sample_log_file(tmp_path):
    # Setup a temporary log file for testing purposes
    log_path = tmp_path / "simulation_output.log"
    log_path.write_text(
        "INFO: Passenger A waited 10.0 mins at Green_Herzliya\n"
        "INFO: Passenger B waited 20.0 mins at Green_Herzliya\n"
        "INFO: Passenger C waited 5.0 mins at City_Center\n"
    )
    return log_path


def test_collector_includes_unvisited_neighborhood(sample_log_file):
    # Pick a neighborhood that is in config but not in our mock log
    unvisited = [n for n in HERZLIYA_NEIGHBORHOODS if n not in ["Green_Herzliya", "City_Center"]][0]
    collector = MetricsCollector(log_file=sample_log_file)
    times = collector.get_average_wait_times()

    assert unvisited in times
