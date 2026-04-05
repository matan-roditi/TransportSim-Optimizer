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

    def __init__(self, neighborhoods: Dict[str, Any], routes_file: str = "bus_lines_save.json") -> None:
        # Initialize the simulation clock (starts at 06:00)
        self.clock = SimulationClock("06:00", "22:00")
        # Initialize the frequency manager
        self.dispatcher = Dispatcher()

        self.routes_cache = self._load_routes(routes_file)
        # Load travel times between stops from the database
        self.travel_times_cache: Dict[Tuple[str, str], int] = self._load_travel_times()

        # Initialize the passenger routing brain using the real stops from the JSON
        # We generate coordinates for the real stop names found in your routes
        stop_coords = self._load_stop_coordinates_from_db()
        
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

        # Ridership counters for the end-of-simulation summary
        self._total_passengers_served: int = 0
        self._total_passengers_deployed: int = 0
        self._total_buses_dispatched: int = 0

        # Detailed tracking lists/dicts for per-passenger and per-line stats
        self.served_passengers: List[PassengerAgent] = []
        self.line_boarding_counts: Dict[str, int] = {}
        self.line_dispatch_counts: Dict[str, int] = {}

        logger.info("Simulation Orchestrator initialized for Herzliya")

    def _load_routes(self, file_path: str) -> Dict[str, List[str]]:
        """
        Reads the JSON file and parses the routes into a dictionary.
        Automatically generates a reverse route for each line loaded.
        """
        loaded_routes = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for line in data:
                    line_name = line["name"]
                    stops = line.get("stops", [])
                    
                    loaded_routes[line_name] = stops
                    
                    if len(stops) > 1:
                        reverse_name = f"{line_name} Reverse"
                        loaded_routes[reverse_name] = list(reversed(stops))
                        
            logger.info(f"Successfully loaded {len(loaded_routes)} routes (including reverse directions) from {file_path}")
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
                        SELECT s1.name, s2.name, tt.seconds
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
            dispatched_this_tick = 0
            for target_line, line_stops in self.routes_cache.items():

                # Skip auto-dispatching for reverse lines so they only spawn when a forward bus finishes
                if target_line.endswith(" Reverse"):
                    continue

                if not line_stops:
                    continue

                bus_id = f"Bus_{target_line.replace(' ', '')}_{current_time.strftime('%H%M')}"
                route_data = {"line_id": target_line, "stops": line_stops}
                new_bus = BusAgent(bus_id=bus_id, route_data=route_data)
                self.active_buses.append(new_bus)
                self._total_buses_dispatched += 1
                dispatched_this_tick += 1
                self.line_dispatch_counts[target_line] = self.line_dispatch_counts.get(target_line, 0) + 1
                logger.info(f"[{current_time_str}] {bus_id} departing empty from {line_stops[0]} on {target_line}")

        new_passengers = self.passenger_generator.generate_passengers_for_time(current_time_str)
        if new_passengers:
            self.active_passengers.extend(new_passengers)
            self._total_passengers_deployed += len(new_passengers)

            # Log the specific deployment of each individual passenger
            for p in new_passengers:
                origin_coords = f"({p.lat:.4f}, {p.lon:.4f})"
                dest_coords = f"({p.destination[0]:.4f}, {p.destination[1]:.4f})"
                logger.info(
                    f"[{current_time_str}] passenger #{p.passenger_id} deployed "
                    f"with origin:{origin_coords}, dest:{dest_coords}"
                )

        # Temporary list to hold newly spawned reverse buses
        # This prevents modifying self.active_buses while we are iterating over it
        new_reverse_buses = []

        for bus in self.active_buses:
            current_stop = bus.navigator.get_current_stop()
            next_stop = bus.navigator.get_next_stop()

            if bus.ticks_until_arrival == 0:
                passengers_before_alight = len(getattr(bus, 'passengers', []))

                # Capture the exact passengers getting off this tick
                getting_off = bus.alight_passengers(current_time_str)

                passengers_after_alight = len(getattr(bus, 'passengers', []))
                alighted_count = passengers_before_alight - passengers_after_alight

                # Emit the final Stage 2 arrival log for each passenger
                for p in getting_off:
                    self.served_passengers.append(p)
                    logger.info(
                        f"passenger #{p.passenger_id} arrived to dest| "
                        f"total commute time: {p.total_commute_time}| "
                        f"walk to bus stop: {p.walking_time_to_bus_stop}| "
                        f"time waited: {p.time_waited}| "
                        f"time in the bus: {p.time_in_bus}| "
                        f"walk to dest: {p.walking_time_to_dest}| "
                        f"neighborhood: {p.origin_neighborhood}|"
                    )

                waiting_passengers_before = len(self.active_passengers)
                self.active_passengers = bus.process_boarding(self.active_passengers, current_time_str)
                boarded_count = waiting_passengers_before - len(self.active_passengers)

                # Track per-line boarding counts
                if boarded_count > 0:
                    line_key = bus.navigator.line_id
                    self.line_boarding_counts[line_key] = (
                        self.line_boarding_counts.get(line_key, 0) + boarded_count
                    )
                current_load = len(getattr(bus, 'passengers', []))

                self._total_passengers_served += alighted_count

                # Evaluate boarding activity and log the exact bus behavior
                if alighted_count > 0 or boarded_count > 0:
                    logger.info(
                        f"[{current_time_str}] {bus.bus_id} at {current_stop} "
                        f"| Left: {alighted_count} | Boarded: {boarded_count} "
                        f"| On-board: {current_load}"
                    )
                elif next_stop:
                    # The bus arrived but no one got on or off and it is not the final destination
                    logger.info(
                        f"[{current_time_str}] {bus.bus_id} at {current_stop} "
                        f"| Left: 0 | Boarded: 0 "
                        f"| On-board: {current_load} | continued without stopping"
                    )

            # Check if the bus has reached the end of its route
            if not next_stop and not bus.reverse_dispatched:
                # Apply the safety flag to prevent infinite dispatching loops
                bus.reverse_dispatched = True
                current_line_id = bus.route_data.get("line_id", "")

                # Only dispatch a reverse bus if the finishing bus was on a forward line
                if not current_line_id.endswith(" Reverse"):
                    reverse_line = f"{current_line_id} Reverse"

                    if reverse_line in self.routes_cache:
                        reverse_stops = self.routes_cache[reverse_line]
                        new_bus_id = f"Bus_{reverse_line.replace(' ', '')}_{current_time.strftime('%H%M')}"

                        new_reverse_bus = BusAgent(
                            bus_id=new_bus_id, 
                            route_data={"line_id": reverse_line, "stops": reverse_stops}
                        )
                        new_reverse_buses.append(new_reverse_bus)
                        self._total_buses_dispatched += 1
                        self.line_dispatch_counts[reverse_line] = self.line_dispatch_counts.get(reverse_line, 0) + 1
                        logger.info(f"[{current_time_str}] {bus.bus_id} completed forward route. Dispatching {new_bus_id} on {reverse_line}")

            travel_time = 0
            if bus.ticks_until_arrival == 0 and next_stop:
                travel_time = self.get_travel_time_minutes(current_stop, next_stop)
            bus.tick(travel_time_to_next=travel_time)

        # Append all newly spawned reverse buses to the fleet so they begin moving on the next tick
        if new_reverse_buses:
            self.active_buses.extend(new_reverse_buses)

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

    def _load_stop_coordinates_from_db(self) -> Dict[str, Tuple[float, float]]:
        """
        Loads real stop coordinates from the PostgreSQL database.
        Falls back to synthetic coordinates if the connection fails or data is missing.
        """
        required_env_vars = ["PG_HOST", "PG_PORT", "PG_DB", "PG_USER", "PG_PASSWORD"]
        if not all(os.environ.get(var) for var in required_env_vars):
            logger.warning("PostgreSQL credentials not set. Falling back to synthetic coordinates.")
            return self._generate_synthetic_coordinates()

        db_stops: Dict[str, Tuple[float, float]] = {}
        try:
            with psycopg2.connect(
                host=os.environ["PG_HOST"],
                port=os.environ["PG_PORT"],
                dbname=os.environ["PG_DB"],
                user=os.environ["PG_USER"],
                password=os.environ["PG_PASSWORD"]
            ) as conn:
                with conn.cursor() as cur:
                    # Column names match the schema defined in top20_build_edges.py: name, lat, lon
                    cur.execute("SELECT name, lat, lon FROM stops")
                    for stop_name, lat, lon in cur.fetchall():
                        db_stops[stop_name] = (float(lat), float(lon))
            
            logger.info(f"Loaded {len(db_stops)} stop coordinates from database.")
        except Exception as e:
            logger.error(f"Failed to load coordinates from DB: {e}. Falling back to synthetic.")
            return self._generate_synthetic_coordinates()

        # Verify that all stops needed by the routes exist in the database results
        # Use synthetic coordinates for any missing stops to prevent routing crashes
        final_stops = {}
        missing_stops_count = 0
        base_lat = 32.1650
        base_lon = 34.8400
        offset_step = 0.002
        current_offset = 0.0

        for route in self.routes_cache.values():
            for stop in route:
                if stop not in final_stops:
                    if stop in db_stops:
                        final_stops[stop] = db_stops[stop]
                    else:
                        missing_stops_count += 1
                        final_stops[stop] = (base_lat + current_offset, base_lon + current_offset)
                        current_offset += offset_step

        if missing_stops_count > 0:
            logger.warning(f"Missing {missing_stops_count} stops in DB. Used synthetic coordinates for them.")

        return final_stops

    def _generate_synthetic_coordinates(self) -> Dict[str, Tuple[float, float]]:
        """
        Generates fallback coordinates by applying a small offset to each stop.
        """
        stops = {}
        base_lat = 32.1650
        base_lon = 34.8400
        offset_step = 0.002
        current_offset = 0.0

        for route in self.routes_cache.values():
            for stop in route:
                if stop not in stops:
                    stops[stop] = (base_lat + current_offset, base_lon + current_offset)
                    current_offset += offset_step
        
        return stops

    def is_running(self) -> bool:
        """Returns True if the simulation clock has not yet reached the end time."""
        return not self.clock.is_finished()

    def get_stats(self) -> Dict[str, Any]:
        """Returns a summary of key simulation statistics."""
        still_on_buses = sum(len(getattr(bus, 'passengers', [])) for bus in self.active_buses)
        unserved = len(self.active_passengers) + still_on_buses

        # Initialize base stats
        stats = {
            "buses_dispatched": self._total_buses_dispatched,
            "passengers_deployed": self._total_passengers_deployed,
            "passengers_served": self._total_passengers_served,
            "passengers_unserved": unserved,
            "service_rate_pct": (
                round(self._total_passengers_served / self._total_passengers_deployed * 100, 1)
                if self._total_passengers_deployed > 0 else 0.0
            ),
        }

        # Add passenger averages safely using the served passengers list
        served_list = getattr(self, 'served_passengers', [])
        total_served = len(served_list)

        if total_served > 0:
            stats["avg_commute_time_mins"] = sum(p.total_commute_time for p in served_list) / total_served

            total_walking = sum((p.walking_time_to_bus_stop + p.walking_time_to_dest) for p in served_list)
            stats["avg_walking_time_mins"] = total_walking / total_served

            stats["avg_waiting_time_mins"] = sum(p.time_waited for p in served_list) / total_served
        else:
            stats["avg_commute_time_mins"] = 0.0
            stats["avg_walking_time_mins"] = 0.0
            stats["avg_waiting_time_mins"] = 0.0

        # Add line boarding averages safely
        for line, boardings in getattr(self, 'line_boarding_counts', {}).items():
            dispatches = getattr(self, 'line_dispatch_counts', {}).get(line, 0)

            if dispatches > 0:
                stats[f"avg_boardings_{line}"] = boardings / dispatches
            else:
                stats[f"avg_boardings_{line}"] = 0.0

        return stats
