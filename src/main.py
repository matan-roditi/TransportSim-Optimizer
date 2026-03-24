import logging
import os
import sys
import subprocess
from simulation.orchestrator import SimulationOrchestrator
from simulation.config import HERZLIYA_NEIGHBORHOODS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
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

    logger.info("--- Simulation Complete ---")
    logger.info(f"Total Buses Dispatched: {len(orchestrator.active_buses)}")
    logger.info(f"Total Passengers Deployed: {len(orchestrator.active_passengers)}")


if __name__ == "__main__":
    run_simulation()
