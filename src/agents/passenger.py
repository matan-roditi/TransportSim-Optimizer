from dataclasses import dataclass
from typing import Tuple, Dict, Any, Optional
import random
import requests
import logging

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
    Uses geographical bounds and weights to distribute demand.
    """

    def __init__(self, neighborhoods: Dict[str, Any], osrm_url: str = "http://router.project-osrm.org"):
        # Store neighborhood configuration and prepare weighting lists
        self.neighborhoods = neighborhoods
        self.neighborhood_names = list(neighborhoods.keys())
        self.weights = [n["weight"] for n in neighborhoods.values()]
        self.osrm_url = osrm_url

    def _get_walking_duration(self, origin: Tuple[float, float], dest: Tuple[float, float]) -> int:
        """
        Queries OSRM for the walking duration between two points.
        Returns the duration in seconds.
        """
        # OSRM requires coordinates in lon,lat order
        coords = f"{origin[1]},{origin[0]};{dest[1]},{dest[0]}"
        url = f"{self.osrm_url}/route/v1/foot/{coords}?overview=false"
        
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if "routes" in data and data["routes"]:
                return int(data["routes"][0]["duration"])
        except Exception as e:
            logger.error(f"OSRM Request failed: {e}. Falling back to default estimate.")
            
        # Fallback if API is down or coordinates are invalid
        return 600

    def generate_passenger(self, nearest_stop_coords: Optional[Tuple[float, float]] = None) -> PassengerAgent:
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
        
        # Assign mock destination coordinates
        destination = (32.1624, 34.8447)

        # Assign mock stops for the simulation handshake
        # These will be replaced by actual database logic in future steps
        mock_origin = "קניון ארנה"
        mock_target = "ת. רכבת הרצליה"

        walk_time = 0
        if nearest_stop_coords:
            walk_time = self._get_walking_duration((lat, lon), nearest_stop_coords)
        
        return PassengerAgent(
            lat=lat, 
            lon=lon, 
            destination=destination,
            origin_stop=mock_origin,
            target_stop=mock_target,
            walking_time_to_stop=walk_time
        )