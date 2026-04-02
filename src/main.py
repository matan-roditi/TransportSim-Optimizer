import logging
import os
import sys
import subprocess
from dotenv import load_dotenv
from simulation.orchestrator import SimulationOrchestrator
from simulation.config import HERZLIYA_NEIGHBORHOODS
# Import the AI integration modules
from crew.metrics import MetricsCollector
from crew.board import run_board_meeting

load_dotenv()

# Configure logging to write to both a file and the console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("simulation_output.log", mode="w", encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
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
    logger.info("=" * 55)
    logger.info("  SIMULATION COMPLETE — END OF SERVICE DAY SUMMARY")
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

    try:
        # Initialize the collector and extract the simulated day data
        collector = MetricsCollector("simulation_output.log")
        wait_time_metrics = collector.get_average_wait_times()

        logger.info("Metrics extracted. Handing data to the AI agents...")

        # Execute the crew and retrieve the consensus
        board_decision = run_board_meeting(wait_time_metrics)

        logger.info("=" * 55)
        logger.info("  AI BOARD FINAL CONSENSUS")
        logger.info("=" * 55)
        logger.info(f"\n{board_decision}")
        logger.info("=" * 55)

    except Exception as e:
        # Catch network timeouts or API authentication errors gracefully
        logger.error(f"The AI Board failed to convene. Error: {e}")
        logger.info("Simulation completed without AI consensus.")


if __name__ == "__main__":
    run_simulation()
