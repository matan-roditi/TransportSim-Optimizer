import logging
from datetime import time
from typing import List, Dict, Any

from simulation.clock import SimulationClock
from simulation.dispatcher import Dispatcher
from agents.bus import BusAgent
from agents.passenger import PassengerAgent, PassengerGenerator

# Setup logging for the central simulation brain
logger = logging.getLogger(__name__)


class SimulationOrchestrator:
    """
    The central brain of the simulation.
    Coordinates time advancement, bus dispatching, and passenger spawning.
    """

    def __init__(self, neighborhoods: Dict[str, Any]) -> None:
        # Initialize the simulation clock (starts at 06:00)
        self.clock = SimulationClock()
        # Initialize the frequency manager
        self.dispatcher = Dispatcher()
        # Initialize the person factory for Herzliya
        self.passenger_generator = PassengerGenerator(neighborhoods)
        
        # Lists to track active entities in the world
        self.active_buses: List[BusAgent] = []
        self.active_passengers: List[PassengerAgent] = []
        
        logger.info("Simulation Orchestrator initialized for Herzliya")