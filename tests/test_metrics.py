import pytest
from crew.metrics import MetricsCollector
from simulation.config import HERZLIYA_NEIGHBORHOODS


@pytest.fixture
def sample_log_file(tmp_path):
    # Setup a temporary log file mimicking the exact output of the orchestrator
    log_path = tmp_path / "simulation_output.log"
    log_path.write_text(
        "2026-04-02 18:06:19 - passenger #1 arrived | walk to dest: 5| waited 10.0 mins at Green_Herzliya\n"
        "2026-04-02 18:06:20 - passenger #2 arrived | walk to dest: 2| waited 20.0 mins at Green_Herzliya\n"
        "2026-04-02 18:06:21 - passenger #3 arrived | walk to dest: 8| waited 5.0 mins at City_Center\n"
        "2026-04-02 18:06:22 - Bus_Line1_0800 departed empty from Stop A\n"
    )
    return log_path


def test_collector_averages_wait_times_green_herzliya(sample_log_file):
    collector = MetricsCollector(log_file=sample_log_file)
    times = collector.get_average_wait_times()

    assert times["Green_Herzliya"] == 15.0


def test_collector_averages_wait_times_city_center(sample_log_file):
    collector = MetricsCollector(log_file=sample_log_file)
    times = collector.get_average_wait_times()

    assert times["City_Center"] == 5.0


def test_collector_includes_unvisited_neighborhood_in_result(sample_log_file):
    unvisited = [n for n in HERZLIYA_NEIGHBORHOODS if n not in ["Green_Herzliya", "City_Center"]][0]
    collector = MetricsCollector(log_file=sample_log_file)
    times = collector.get_average_wait_times()

    assert unvisited in times


def test_collector_unvisited_neighborhood_has_zero_wait_time(sample_log_file):
    unvisited = [n for n in HERZLIYA_NEIGHBORHOODS if n not in ["Green_Herzliya", "City_Center"]][0]
    collector = MetricsCollector(log_file=sample_log_file)
    times = collector.get_average_wait_times()

    assert times[unvisited] == 0.0
