from __future__ import annotations
from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional, List, Callable
import random
import requests
import logging
import math


# Setup logging for external API communication and generation events
logger = logging.getLogger(__name__)

@dataclass
class PassengerAgent:
    """
    Represents a single commuter in the simulation.
    Stores current GPS coordinates and the target destination.
    """
    lat: float
    lon: float
    destination: Tuple[float, float]
    origin_stop: str
    target_stop: str
    walking_time_to_stop: int = 0


class PassengerGenerator:
    """
    Generates PassengerAgents based on neighborhood population density.
    Uses a routing brain to assign logical origins and destinations.
    """

    def __init__(
        self, 
        neighborhoods: Dict[str, Any],
        navigator: PassengerNavigator,
        routes_cache: Dict[str, List[str]],
        get_bus_time: Callable[[str, str], int],
        get_walk_time: Callable[[Tuple[float, float], Tuple[float, float]], int],
        llm_schedule: Optional[List[Dict[str, Any]]] = None
    ):
        self.neighborhoods = neighborhoods
        self.neighborhood_names = list(neighborhoods.keys())
        self.weights = [n["weight"] for n in neighborhoods.values()]
        
        self.navigator = navigator
        self.routes_cache = routes_cache
        self.get_bus_time = get_bus_time
        self.get_walk_time = get_walk_time
        self.llm_schedule: List[Dict[str, Any]] = llm_schedule or []

    def generate_passengers_for_time(self, current_time_str: str) -> List[PassengerAgent]:
        """
        Generates passengers whose departure time matches the current simulation time.
        Driven by the LLM demand schedule loaded at startup.
        """
        if not self.llm_schedule:
            return []

        # Look for the exact key we specified in the LLM prompt
        matching = [entry for entry in self.llm_schedule if entry.get("departing_time") == current_time_str]
        
        passengers = []
        for entry in matching:
            origin = entry.get("origin_neighborhood")
            dest = entry.get("destination_neighborhood")
            
            # Ensure the LLM didn't hallucinate missing data before attempting to route
            if origin and dest:
                try:
                    # Pass the AI's requested neighborhoods into the spawner
                    passengers.append(self.generate_passenger(origin, dest))
                except ValueError:
                    logger.warning(f"Could not route scheduled passenger from {origin} to {dest} at {current_time_str}")
                except KeyError:
                    logger.warning(f"LLM hallucinated an unknown neighborhood: {origin} or {dest}")
                    
        return passengers

    def generate_passenger(self, origin_name: str, dest_name: str) -> PassengerAgent:
        """
        Creates a passenger by selecting random coordinates within the specifically requested bounds.
        Calculates the optimal multimodal route using the passenger brain.
        """
        # Look up the GPS bounding boxes for the requested neighborhoods
        origin_bounds = self.neighborhoods[origin_name]["bounds"]
        lat = random.uniform(origin_bounds["lat"][0], origin_bounds["lat"][1])
        lon = random.uniform(origin_bounds["lon"][0], origin_bounds["lon"][1])
        
        dest_bounds = self.neighborhoods[dest_name]["bounds"]
        dest_lat = random.uniform(dest_bounds["lat"][0], dest_bounds["lat"][1])
        dest_lon = random.uniform(dest_bounds["lon"][0], dest_bounds["lon"][1])
        destination = (dest_lat, dest_lon)

        # Query the brain for the best route using injected callbacks
        origin_stop, target_stop, total_time = self.navigator.find_optimal_route(
            origin_coords=(lat, lon),
            dest_coords=destination,
            routes_cache=self.routes_cache,
            get_bus_time=self.get_bus_time,
            get_walk_time=self.get_walk_time
        )

        # Prevent broken agents from spawning
        if origin_stop is None or target_stop is None:
            raise ValueError("No viable route found for passenger.")

        return PassengerAgent(
            lat=lat, 
            lon=lon, 
            destination=destination,
            origin_stop=origin_stop,
            target_stop=target_stop,
            walking_time_to_stop=0 
        )


class PassengerNavigator:
    """
    Acts as the routing brain for passengers.
    Finds the most optimal stops based on geographic distance.
    """

    def __init__(self, stops: Dict[str, Tuple[float, float]]):
        self.stops = stops

    def get_closest_stops(self, lat: float, lon: float, count: int = 5) -> List[str]:
        """
        Calculates the straight-line distance to all known stops.
        Returns the names of the closest stops sorted by distance.
        """
        distances = []

        for stop_name, coords in self.stops.items():
            stop_lat, stop_lon = coords

            # Calculate the straight-line distance between the passenger and the stop
            dist = math.hypot(lat - stop_lat, lon - stop_lon)
            distances.append((dist, stop_name))

        # Sort the list by the calculated distance (the first element in the tuple)
        distances.sort(key=lambda x: x[0])

        # Extract just the names of the closest stops up to the requested count
        closest_stops = [stop_name for dist, stop_name in distances[:count]]

        return closest_stops

    def find_optimal_route(
        self,
        origin_coords: Tuple[float, float],
        dest_coords: Tuple[float, float],
        routes_cache: Dict[str, List[str]],
        get_bus_time: Callable[[str, str], int],
        get_walk_time: Callable[[Tuple[float, float], Tuple[float, float]], int]
    ) -> Tuple[Optional[str], Optional[str], float]:
        """
        Finds the fastest multimodal route connecting a passenger origin to their destination.
        Prunes combinations by verifying bus line connectivity before calculating time.
        """
        closest_origins = self.get_closest_stops(origin_coords[0], origin_coords[1], count=5)
        closest_destinations = self.get_closest_stops(dest_coords[0], dest_coords[1], count=5)

        best_time = float('inf')
        best_origin = None
        best_dest = None

        for o_stop in closest_origins:
            for d_stop in closest_destinations:
                
                # Verify if any route connects these two stops in the correct direction
                is_connected = False
                for stops_list in routes_cache.values():
                    if o_stop in stops_list and d_stop in stops_list:
                        if stops_list.index(o_stop) < stops_list.index(d_stop):
                            is_connected = True
                            break

                if is_connected:
                    # Calculate the three legs of the journey
                    walk_to_stop = get_walk_time(origin_coords, self.stops[o_stop])
                    bus_ride = get_bus_time(o_stop, d_stop)
                    walk_to_dest = get_walk_time(self.stops[d_stop], dest_coords)

                    total_time = walk_to_stop + bus_ride + walk_to_dest

                    # Update the winning route if this combination is faster
                    if total_time < best_time:
                        best_time = total_time
                        best_origin = o_stop
                        best_dest = d_stop

        return best_origin, best_dest, best_time
