import argparse
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

# Configure logging: full detail goes to the log file; only warnings and errors
# are echoed to the terminal to keep the console output clean.
file_handler = logging.FileHandler("simulation_output.log", mode="w", encoding="utf-8")
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[file_handler, console_handler]
)
logger = logging.getLogger(__name__)


def _reset_simulation_log():
    # Safely clear the log file stream so the metrics collector only reads the current run
    file_handler.stream.seek(0)
    file_handler.stream.truncate(0)


def _run_single_simulation(routes_file: str) -> tuple:
    """
    Run one full simulation day using the given routes file.
    Returns (orchestrator, stats) so the caller can pass data to the crew.
    """
    # Clear ghost data from previous iterations before each new run
    _reset_simulation_log()

    orchestrator = SimulationOrchestrator(neighborhoods=HERZLIYA_NEIGHBORHOODS, routes_file=routes_file)
    logger.info(f"Simulation initialised with '{routes_file}'. Service window: "
                f"{orchestrator.clock.current_dt.strftime('%H:%M')} - "
                f"{orchestrator.clock.end_dt.strftime('%H:%M')}")

    while not orchestrator.clock.is_finished():
        orchestrator.run_tick()

    stats = orchestrator.get_stats()
    return orchestrator, stats


def _print_stats(stats: dict, label: str = "") -> None:
    """Write the end-of-day summary block to logger (goes to log file and WARNING+ to console)."""
    header = f"  SIMULATION COMPLETE{' — ' + label if label else ''}"
    logger.info("=" * 55)
    logger.info(header)
    logger.info("=" * 55)
    logger.info(f"  Buses dispatched    : {stats['buses_dispatched']}")
    logger.info(f"  Passengers deployed : {stats['passengers_deployed']}")
    logger.info(f"  Passengers served   : {stats['passengers_served']}")
    logger.info(f"  Passengers unserved : {stats['passengers_unserved']}")
    logger.info(f"  Service rate        : {stats['service_rate_pct']}%")
    logger.info("-" * 55)
    logger.info(f"  Avg commute time for passengers : {stats['avg_commute_time_mins']:.1f} min")
    logger.info(f"  Avg walking time for passengers : {stats['avg_walking_time_mins']:.1f} min")
    logger.info(f"  Avg waiting time for passengers : {stats['avg_waiting_time_mins']:.1f} min")
    logger.info("-" * 55)
    logger.info("  Avg boardings per bus dispatch (by line):")
    for key, value in stats.items():
        if key.startswith("avg_boardings_"):
            line_name = key[len("avg_boardings_"):]
            logger.info(f"    {line_name:<20}: {value:.1f}")
    logger.info("=" * 55)

    # Always print a compact summary to the terminal regardless of log level
    print(f"\n{'='*55}")
    print(f"  {header}")
    print(f"  Service rate: {stats['service_rate_pct']}%  "
          f"| Served: {stats['passengers_served']}  "
          f"| Unserved: {stats['passengers_unserved']}")
    print(f"  Avg wait: {stats['avg_waiting_time_mins']:.1f} min  "
          f"| Avg commute: {stats['avg_commute_time_mins']:.1f} min")
    print(f"{'='*55}\n")


def _run_crew_step(orchestrator, routes_file: str, output_file: str) -> bool:
    """
    Run the AI board meeting and write the redesigned routes to output_file.
    Returns True on success, False if the board failed.
    """
    try:
        collector = MetricsCollector("simulation_output.log")
        wait_time_metrics = collector.get_average_wait_times()

        with open(routes_file, encoding="utf-8") as f:
            current_lines = json.load(f)

        unserved_od_metrics = {}
        for p in orchestrator.active_passengers:
            key = f"{p.origin_stop} to {p.target_stop}"
            unserved_od_metrics[key] = unserved_od_metrics.get(key, 0) + 1

        valid_stops_list = []
        csv_path = os.path.join(os.path.dirname(__file__), "database", "herzliya_top20_selected.csv")
        with open(csv_path, encoding="utf-8") as csv_file:
            for row in csv.DictReader(csv_file):
                name = row["stop_name"].strip()
                if name and name not in valid_stops_list:
                    valid_stops_list.append(name)

        logger.info("Metrics extracted. Handing data to the AI agents...")
        print("  → AI board convening...")

        board_decision = run_topological_board_meeting(
            current_lines=current_lines,
            wait_time_metrics=wait_time_metrics,
            unserved_od_metrics=unserved_od_metrics,
            valid_stops_list=valid_stops_list,
        )

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(json.loads(board_decision), f, ensure_ascii=False, indent=4)

        logger.info(f"Redesigned routes saved to {output_file}.")
        print(f"  → Redesigned routes saved to {output_file}")
        return True

    except Exception as e:
        logger.error(f"The AI Board failed to convene. Error: {e}")
        print(f"  [ERROR] AI Board failed: {e}")
        return False


def run_simulation():
    """
    Single baseline run using bus_lines_save.json.
    """
    logger.info("Starting Herzliya Transit Simulation Engine (single run)...")

    if not os.path.exists("herzliya_demand.json"):
        logger.warning("Demand file 'herzliya_demand.json' not found! Booting up the LLM generator...")
        try:
            subprocess.run([sys.executable, "scripts/generate_llm_demand.py"], check=True)
            logger.info("Demand generation complete. Resuming simulation startup.")
        except subprocess.CalledProcessError as e:
            logger.error(f"Fatal error during LLM generation: {e}")
            return

    orchestrator, stats = _run_single_simulation("bus_lines_save.json")
    _print_stats(stats)

    _run_crew_step(orchestrator, "bus_lines_save.json", "bus_lines_crew.json")


def run_crew_loop(iterations: int = 6):
    """
    Run the simulation for `iterations` cycles.
    Iteration 1 always starts from bus_lines_save.json (the human baseline).
    Each cycle the AI board redesigns the routes and writes them to
    bus_lines_crew.json, which every subsequent iteration uses.
    """
    logger.info(f"Starting Herzliya Crew Loop — {iterations} iterations")
    print(f"\n{'#'*55}")
    print(f"  CREW LOOP — {iterations} ITERATIONS")
    print(f"{'#'*55}\n")

    if not os.path.exists("herzliya_demand.json"):
        logger.warning("Demand file 'herzliya_demand.json' not found! Booting up the LLM generator...")
        try:
            subprocess.run([sys.executable, "scripts/generate_llm_demand.py"], check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Fatal error during LLM generation: {e}")
            return

    for i in range(1, iterations + 1):
        # Iteration 1 always uses the original human baseline
        routes_file = "bus_lines_save.json" if i == 1 else "bus_lines_crew.json"
        print(f"{'─'*55}")
        print(f"  ITERATION {i}/{iterations}  (routes: {routes_file})")
        print(f"{'─'*55}")
        logger.info(f"=== Crew loop iteration {i}/{iterations} — routes: {routes_file} ===")

        orchestrator, stats = _run_single_simulation(routes_file)
        _print_stats(stats, label=f"Iteration {i}/{iterations}")

        if i < iterations:
            success = _run_crew_step(orchestrator, routes_file, "bus_lines_crew.json")
            if not success:
                print(f"  Stopping loop at iteration {i} due to AI board failure.")
                break
        else:
            # Last iteration — still run the board so the final output is saved
            _run_crew_step(orchestrator, routes_file, "bus_lines_crew.json")

    print(f"\n{'#'*55}")
    print(f"  CREW LOOP COMPLETE")
    print(f"  Final AI routes saved in bus_lines_crew.json")
    print(f"{'#'*55}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Herzliya Transit Simulation")
    parser.add_argument(
        "--crew-loop",
        type=int,
        nargs="?",
        const=6,
        metavar="N",
        help="Run N crew-loop iterations (default: 6). Iteration 1 uses bus_lines_save.json; "
             "subsequent iterations use the AI-updated bus_lines_crew.json."
    )
    args = parser.parse_args()

    if args.crew_loop:
        run_crew_loop(iterations=args.crew_loop)
    else:
        run_simulation()
