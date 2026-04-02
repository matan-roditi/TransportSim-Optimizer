import re
from collections import defaultdict
from simulation.config import HERZLIYA_NEIGHBORHOODS


class MetricsCollector:
    def __init__(self, log_file="simulation_output.log"):
        self.log_file = log_file

    def get_average_wait_times(self):
        wait_times = defaultdict(list)

        # Pre-populate all valid neighborhoods to guarantee they exist in the output
        for neighborhood in HERZLIYA_NEIGHBORHOODS:
            wait_times[neighborhood] = []

        pattern = re.compile(r"time waited: ([\d\.]+)\| .*neighborhood: ([^|]+)\|")

        try:
            with open(self.log_file, 'r', encoding='utf-8') as file:
                for line in file:
                    match = pattern.search(line.strip())
                    if match:
                        time = float(match.group(1))
                        neighborhood = match.group(2)

                        # Only track times for valid neighborhoods defined in config
                        if neighborhood in wait_times:
                            wait_times[neighborhood].append(time)
        except FileNotFoundError:
            pass

        averages = {}
        for neighborhood, times in wait_times.items():
            if times:
                averages[neighborhood] = sum(times) / len(times)
            else:
                # Default to zero for unvisited areas to prevent KeyErrors downstream
                averages[neighborhood] = 0.0

        return averages