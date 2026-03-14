from dataclasses import dataclass
from typing import Tuple, Dict, Any
import random


@dataclass
class PassengerAgent:
    """
    Represents a single commuter in the simulation.
    Stores current GPS coordinates and the target destination.
    """
    lat: float
    lon: float
    destination: Tuple[float, float]


class PassengerGenerator:
    """
    Generates PassengerAgents based on neighborhood population density.
    Uses geographical bounds and weights to distribute demand.
    """

    def __init__(self, neighborhoods: Dict[str, Any]):
        # Store neighborhood configuration and prepare weighting lists
        self.neighborhoods = neighborhoods
        self.neighborhood_names = list(neighborhoods.keys())
        self.weights = [n["weight"] for n in neighborhoods.values()]

    def generate_passenger(self) -> PassengerAgent:
        """
        Creates a passenger by selecting a neighborhood based on weight.
        Randomizes coordinates within that neighborhood's bounds.
        """
        # Select a neighborhood based on population probability
        selected_name = random.choices(
            self.neighborhood_names, 
            weights=self.weights, 
            k=1
        )[0]
        
        neighborhood = self.neighborhoods[selected_name]
        bounds = neighborhood["bounds"]
        
        # Generate random coordinates within the bounding box
        lat = random.uniform(bounds["lat"][0], bounds["lat"][1])
        lon = random.uniform(bounds["lon"][0], bounds["lon"][1])
        
        # Assign a mock destination (e.g., Herzliya Train Station)
        # This will be replaced by OSRM/POI logic in future steps
        destination = (32.1624, 34.8447)
        
        return PassengerAgent(lat, lon, destination)