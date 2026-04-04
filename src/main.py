import csv
import json
import logging
import os
import sys
import subprocess
from dotenv import load_dotenv
from simulation.orchestrator import SimulationOrchestrator
from simulation.config import HERZLIYA_NEIGHBORHOODS
# Import the AI integration modules
from crew.metrics import MetricsCollector
from crew.board import run_topological_board_meeting

load_dotenv()

# Configure logging to write to both a file and the console
# File handler captures everything (INFO+); console only shows warnings and above
_file_handler = logging.FileHandler("simulation_output.log", mode="w", encoding="utf-8")
_file_handler.setLevel(logging.INFO)

_console_handler = logging.StreamHandler(sys.stdout)
_console_handler.setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[_file_handler, _console_handler]
)
logger = logging.getLogger(__name__)


def run_simulation():
    """
    The entry point for the Herzliya Transit Simulation.
    Initializes the environment and runs the clock until the end of the service day.
    """
    logger.info("Starting Herzliya Transit Simulation Engine...")

    if not os.path.exists("herzliya_demand.json"):
        logger.warning("Demand file 'herzliya_demand.json' not found! Booting up the LLM generator...")
        try:
            subprocess.run([sys.executable, "scripts/generate_llm_demand.py"], check=True)
            logger.info("Demand generation complete. Resuming simulation startup.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Fatal error during LLM generation: {e}")
            return

    orchestrator = SimulationOrchestrator(neighborhoods=HERZLIYA_NEIGHBORHOODS)

    logger.info(f"Simulation initialized. Service window: {orchestrator.clock.current_dt.strftime('%H:%M')} - {orchestrator.clock.end_dt.strftime('%H:%M')}")

    while not orchestrator.clock.is_finished():
        orchestrator.run_tick()

    stats = orchestrator.get_stats()

    boardings_lines = []
    for key, value in stats.items():
        if key.startswith("avg_boardings_"):
            line_name = key[len("avg_boardings_"):]
            boardings_lines.append(f"    {line_name:<20}: {value:.1f}")

    summary = "\n".join([
        "=" * 55,
        "  SIMULATION COMPLETE — END OF SERVICE DAY SUMMARY",
        "=" * 55,
        f"  Buses dispatched    : {stats['buses_dispatched']}",
        f"  Passengers deployed : {stats['passengers_deployed']}",
        f"  Passengers served   : {stats['passengers_served']}",
        f"  Passengers unserved : {stats['passengers_unserved']}",
        f"  Service rate        : {stats['service_rate_pct']}%",
        "-" * 55,
        f"  Avg commute time for passengers : {stats['avg_commute_time_mins']:.1f} min",
        f"  Avg walking time for passengers : {stats['avg_walking_time_mins']:.1f} min",
        f"  Avg waiting time for passengers : {stats['avg_waiting_time_mins']:.1f} min",
        "-" * 55,
        "  Avg boardings per bus dispatch (by line):",
        *boardings_lines,
        "=" * 55,
    ])
    logger.info(summary)
    print(summary)

    try:
        # Initialize the collector and extract the simulated day data
        collector = MetricsCollector("simulation_output.log")
        wait_time_metrics = collector.get_average_wait_times()

        # Load the baseline routes that ran during this simulation
        with open("bus_lines_save.json", encoding="utf-8") as f:
            current_lines = json.load(f)

        # Build an OD failure map from passengers still stranded at end of service
        unserved_od_metrics = {}
        for p in orchestrator.active_passengers:
            key = f"{p.origin_stop} to {p.target_stop}"
            unserved_od_metrics[key] = unserved_od_metrics.get(key, 0) + 1

        # Load the full candidate stop universe from the curated top-20 CSV so the
        # AI can route buses to stops that are not yet served by any current line.
        valid_stops_list = []
        csv_path = os.path.join(os.path.dirname(__file__), "database", "herzliya_top20_selected.csv")
        with open(csv_path, encoding="utf-8") as csv_file:
            for row in csv.DictReader(csv_file):
                name = row["stop_name"].strip()
                if name and name not in valid_stops_list:
                    valid_stops_list.append(name)

        logger.info("Metrics extracted. Handing data to the AI agents...")

        # Execute the crew and retrieve the redesigned routes as JSON
        board_decision = run_topological_board_meeting(
            current_lines=current_lines,
            wait_time_metrics=wait_time_metrics,
            unserved_od_metrics=unserved_od_metrics,
            valid_stops_list=valid_stops_list,
        )

        # Write the AI-redesigned routes to a separate file, keeping the original
        # human-authored routes in bus_lines_save.json untouched for comparison.
        with open("bus_lines_crew.json", "w", encoding="utf-8") as f:
            json.dump(json.loads(board_decision), f, ensure_ascii=False, indent=4)
        logger.info("Redesigned routes saved to bus_lines_crew.json.")
        print("AI board complete. Redesigned routes saved to bus_lines_crew.json.")

    except Exception as e:
        # Catch network timeouts or API authentication errors gracefully
        logger.error(f"The AI Board failed to convene. Error: {e}")
        logger.info("Simulation completed without AI consensus.")


if __name__ == "__main__":
    run_simulation()
