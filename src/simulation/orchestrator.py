import logging
import json
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
        self.clock = SimulationClock("06:00", "22:00")
        # Initialize the frequency manager
        self.dispatcher = Dispatcher()
        # Initialize the person factory for Herzliya
        self.passenger_generator = PassengerGenerator(neighborhoods)
        # Load all bus routes into memory once when the simulation starts
        self.routes_cache = self._load_routes("bus_lines_save.json")

        # Lists to track active entities in the world
        self.active_buses: List[BusAgent] = []
        self.active_passengers: List[PassengerAgent] = []

        logger.info("Simulation Orchestrator initialized for Herzliya")

    def _load_routes(self, file_path: str) -> Dict[str, List[str]]:
        """
        Reads the JSON file and parses the routes into a dictionary.
        Maps the line name to its corresponding list of stops.
        """
        loaded_routes = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for line in data:
                    loaded_routes[line["name"]] = line.get("stops", [])
            logger.info(f"Successfully loaded {len(loaded_routes)} routes from {file_path}")
        except FileNotFoundError:
            logger.error(f"Route file not found at {file_path}")
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format in {file_path}: {e}")

        return loaded_routes

    def run_tick(self) -> None:
        """
        Advances the simulation by one tick (1 minute).
        Handles bus dispatching and passenger generation based on the current time.
        """
        current_time = self.clock.current_time

        # Check with the dispatcher if a new bus should start its route
        if self.dispatcher.should_dispatch(current_time):
            bus_id = f"Bus_{current_time.strftime('%H%M')}"
            
            # Fetch the specific stops for Line 1 from the memory cache
            target_line = "Line 1"
            line_stops = self.routes_cache.get(target_line, [])

            # Format the data exactly as BusAgent expects it
            route_data = {
                "line_id": target_line,
                "stops": line_stops
            }

            new_bus = BusAgent(bus_id=bus_id, route_data=route_data)
            self.active_buses.append(new_bus)
            logger.info(f"Deployed new bus: {bus_id} on {target_line}")

        # Generate new passengers
        new_passenger = self.passenger_generator.generate_passenger()
        self.active_passengers.append(new_passenger)
        logger.info(f"Generated new passenger at ({new_passenger.lat}, {new_passenger.lon}) with destination {new_passenger.destination}")

        # Advance the simulation clock by 1 minute
        self.clock.tick()

    def is_running(self) -> bool:
        """
        Checks if the simulation is still within its operational hours (06:00-22:00).
        """
        # The simulation day ends exactly at 22:00
        return bool(self.clock.current_time < time(22, 0))