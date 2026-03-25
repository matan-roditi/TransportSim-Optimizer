import logging
import os
import sys
import subprocess
from dotenv import load_dotenv
from simulation.orchestrator import SimulationOrchestrator
from simulation.config import HERZLIYA_NEIGHBORHOODS

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
    logger.info("=" * 55)


if __name__ == "__main__":
    run_simulation()
