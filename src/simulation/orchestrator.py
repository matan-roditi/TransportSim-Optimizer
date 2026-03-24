import logging
import json
import math
import os
import psycopg2
from datetime import time
from typing import List, Dict, Any, Tuple


from simulation.clock import SimulationClock
from simulation.dispatcher import Dispatcher
from agents.bus import BusAgent
from agents.passenger import PassengerAgent, PassengerGenerator, PassengerNavigator

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

        # Load all bus routes into memory once when the simulation starts
        self.routes_cache = self._load_routes("bus_lines_save.json")
        # Load travel times between stops from the database
        self.travel_times_cache: Dict[Tuple[str, str], int] = self._load_travel_times()

        # Initialize the passenger routing brain using the real stops from the JSON
        # We generate coordinates for the real stop names found in your routes
        stop_coords = self._generate_stop_coordinates()
        
        self.navigator = PassengerNavigator(stops=stop_coords)

        # Load the LLM Demand Matrix from the JSON file
        self.llm_schedule = self._load_llm_schedule()

        # Initialize the person factory for Herzliya with fully wired dependencies
        self.passenger_generator = PassengerGenerator(
            neighborhoods=neighborhoods,
            navigator=self.navigator,
            routes_cache=self.routes_cache,
            get_bus_time=self.get_travel_time_minutes,
            get_walk_time=self._calculate_walk_time,
            llm_schedule=self.llm_schedule # Pass the loaded schedule here
        )

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

    def _load_travel_times(self) -> Dict[Tuple[str, str], int]:
        """
        Loads travel times between stops from PostgreSQL.
        Returns a dict mapping (stop_a, stop_b) -> minutes.
        Falls back to an empty dict if credentials are missing or DB is unavailable.
        """
        required = ["PG_HOST", "PG_PORT", "PG_DB", "PG_USER", "PG_PASSWORD"]
        if not all(os.environ.get(var) for var in required):
            logger.warning("PostgreSQL credentials not set — travel times cache will be empty")
            return {}

        if psycopg2 is None:
            logger.error("psycopg2 is not installed — cannot load travel times")
            return {}

        travel_times: Dict[Tuple[str, str], int] = {}
        try:
            with psycopg2.connect(
                host=os.environ["PG_HOST"],
                port=os.environ["PG_PORT"],
                dbname=os.environ["PG_DB"],
                user=os.environ["PG_USER"],
                password=os.environ["PG_PASSWORD"]
            ) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT s1.stop_name, s2.stop_name, tt.seconds
                        FROM travel_times tt
                        JOIN edges e  ON e.edge_id    = tt.edge_id
                        JOIN stops s1 ON s1.stop_id   = e.from_stop_id
                        JOIN stops s2 ON s2.stop_id   = e.to_stop_id
                        WHERE tt.time_bucket = 0
                    """)
                    for stop_a, stop_b, duration_seconds in cur.fetchall():
                        travel_times[(stop_a, stop_b)] = max(1, round(duration_seconds / 60.0))
            logger.info(f"Loaded {len(travel_times)} travel time entries from database")
        except Exception as e:
            logger.error(f"Failed to load travel times from database: {e}")

        return travel_times

    def get_travel_time_minutes(self, stop_a: str, stop_b: str, fallback: int = 2) -> int:
        """
        Returns the travel time in minutes between two stops.
        Falls back to the provided default if the route is not in the cache.
        """
        return self.travel_times_cache.get((stop_a, stop_b), fallback)

    def run_tick(self) -> None:
        """
        Advances the simulation by one tick.
        Handles bus dispatching and passenger generation based on the current time.
        """
        current_time = self.clock.current_time
        current_time_str = current_time.strftime("%H:%M")

        if self.dispatcher.should_dispatch(current_time):
            for target_line, line_stops in self.routes_cache.items():
                if not line_stops:
                    continue
                bus_id = f"Bus_{target_line.replace(' ', '')}_{current_time.strftime('%H%M')}"
                route_data = {"line_id": target_line, "stops": line_stops}
                new_bus = BusAgent(bus_id=bus_id, route_data=route_data)
                self.active_buses.append(new_bus)
                logger.info(f"[{current_time_str}] 🚌 {bus_id} departing empty from {line_stops[0]} on {target_line}")

        new_passengers = self.passenger_generator.generate_passengers_for_time(current_time_str)
        if new_passengers:
            self.active_passengers.extend(new_passengers)
            logger.info(f"[{current_time_str}] 🧍 Deployed {len(new_passengers)} scheduled passengers.")

        for bus in self.active_buses:
            current_stop = bus.navigator.get_current_stop()
            next_stop = bus.navigator.get_next_stop()

            if bus.ticks_until_arrival == 0:
                passengers_before_alight = len(getattr(bus, 'passengers', []))
                bus.alight_passengers()
                passengers_after_alight = len(getattr(bus, 'passengers', []))
                alighted_count = passengers_before_alight - passengers_after_alight

                waiting_passengers_before = len(self.active_passengers)
                self.active_passengers = bus.process_boarding(self.active_passengers)
                boarded_count = waiting_passengers_before - len(self.active_passengers)
                current_load = len(getattr(bus, 'passengers', []))

                if alighted_count > 0 or boarded_count > 0:
                    logger.info(f"[{current_time_str}] 🚏 {bus.bus_id} at {current_stop} | Left: {alighted_count} | Boarded: {boarded_count} | Total Inside: {current_load}")

            travel_time = 0
            if bus.ticks_until_arrival == 0 and next_stop:
                travel_time = self.get_travel_time_minutes(current_stop, next_stop)
            bus.tick(travel_time_to_next=travel_time)

        self.clock.tick()

    def _calculate_walk_time(self, coord_a: Tuple[float, float], coord_b: Tuple[float, float]) -> int:
        """
        Calculates walking time in minutes using the Haversine formula.
        Applies an urban circuity multiplier and a crosswalk penalty.
        """
        lat1, lon1 = coord_a
        lat2, lon2 = coord_b

        earth_radius_meters = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        straight_line_distance = earth_radius_meters * c

        # Apply standard urban detour index for a highly walkable grid
        urban_circuity_multiplier = 1.3
        actual_walking_distance = straight_line_distance * urban_circuity_multiplier

        average_speed_meters_per_minute = 84.0
        base_minutes = actual_walking_distance / average_speed_meters_per_minute

        crosswalk_penalty = base_minutes // 4

        total_time = int(base_minutes + crosswalk_penalty)

        return max(1, total_time)

    def _load_llm_schedule(self) -> List[Dict[str, Any]]:
        """Loads the schedule generated by scripts/generate_llm_demand.py."""
        path = "herzliya_demand.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

                # Explicitly type the variable to satisfy mypy strict checks
                passengers: List[Dict[str, Any]] = data.get("passengers", [])
                return passengers

        return []

    def _generate_stop_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """Maps real stop names to generic coordinates so the navigator can function."""
        stops = {}
        for route in self.routes_cache.values():
            for stop in route:
                if stop not in stops:
                    # Default center of Herzliya coordinate for real stop names
                    stops[stop] = (32.1650, 34.8400)
        return stops
