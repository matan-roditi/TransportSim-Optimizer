from __future__ import annotations
import logging
from typing import List, TYPE_CHECKING, Optional, Dict

# We use TYPE_CHECKING to avoid circular imports during runtime
if TYPE_CHECKING:
    from agents.passenger import PassengerAgent

# Setup logging for the bus agent
logger = logging.getLogger(__name__)


class BusAgent:
    """
    Represents a bus in the transportation simulation.
    Manages passenger boarding up to a fixed capacity.
    """

    def __init__(self, bus_id: str, route_data: Dict, capacity: int = 50) -> None:
        # Unique identifier for the bus
        self.bus_id = bus_id
        # Maximum passenger capacity
        self.capacity = capacity
        # We now specify that this list will only hold PassengerAgent objects
        self.passengers: List[PassengerAgent] = []
        # Initialize the route navigator with the provided route data
        self.navigator = RouteNavigator(
            line_id=route_data["line_id"],
            stops=route_data["stops"]
        )
        # state variables to manage movement
        self.is_moving: bool = False
        self.ticks_until_arrival: int = 0

        logger.info(f"Bus {bus_id} created for Line {self.navigator.line_id}")

    def board_passengers(self, potential_passengers: List[PassengerAgent]) -> int:
        """
        Board passengers up to the bus's capacity limit.
        """
        # Calculate how many available seats remain
        available_seats = self.capacity - len(self.passengers)
        
        # Board only as many as can fit
        passengers_to_board = potential_passengers[:available_seats]
        self.passengers.extend(passengers_to_board)
        
        boarded_count = len(passengers_to_board)
        logger.debug(f"Bus {self.bus_id}: {boarded_count} passengers boarded")
        
        return boarded_count

    def calculate_stop_duration(self, boarding_count: int, exiting_count: int = 0) -> int:
        """
        Calculates the stop duration based on boarding and exiting passengers.
        Takes the maximum of boarding and exiting times using a 30s base.
        """
        def get_activity_duration(count: int) -> int:
            if count == 0:
                return 0
            base_duration = 30
            extra_people = max(0, count - 4)
            return base_duration + (extra_people * 5)
        
        boarding_time = get_activity_duration(boarding_count)
        exiting_time = get_activity_duration(exiting_count)
        
        total_duration = max(boarding_time, exiting_time)
        
        logger.debug(
            f"Bus {self.bus_id}: stop duration {total_duration}s "
            f"(boarding: {boarding_time}s, exiting: {exiting_time}s)"
        )
        
        return total_duration


class RouteNavigator:
    """
    Handles the sequence of stops for a specific bus line.
    Calculates the next destination based on the current stop.
    """
    def __init__(self, line_id: str, stops: List[str]):
        self.line_id = line_id
        self.stops = stops
        self.current_index = 0
        logger.debug(f"Navigator initialized for Line {line_id} with {len(stops)} stops")

    def get_current_stop(self) -> str:
        return self.stops[self.current_index]

    def get_next_stop(self) -> Optional[str]:
        if self.current_index + 1 < len(self.stops):
            return self.stops[self.current_index + 1]
        return None # End of the line

    def advance(self):
        """Moves the internal pointer to the next stop"""
        if self.current_index + 1 < len(self.stops):
            self.current_index += 1
            logger.info(f"Line {self.line_id}: Advancing to stop {self.get_current_stop()}")
        else:
            logger.warning(f"Line {self.line_id}: Reached the final stop")