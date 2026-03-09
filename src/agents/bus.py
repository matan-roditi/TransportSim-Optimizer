import logging
from typing import List, Any

# Setup logging for the bus agent
logger = logging.getLogger(__name__)


class BusAgent:
    """
    Represents a bus in the transportation simulation.
    Manages passenger boarding up to a fixed capacity.
    """

    def __init__(self, bus_id: str, capacity: int = 50) -> None:
        """
        Initialize a bus with a given ID and passenger capacity.
        
        Args:
            bus_id: Unique identifier for the bus (e.g., "Line_1")
            capacity: Maximum number of passengers the bus can hold (default: 50)
        """
        self.bus_id = bus_id
        self.capacity = capacity
        self.passengers: List[Any] = []
        logger.info(f"Bus {bus_id} created with capacity {capacity}")

    def board_passengers(self, potential_passengers: List[Any]) -> int:
        """
        Board passengers up to the bus's capacity limit.
        
        Args:
            potential_passengers: List of passengers attempting to board
            
        Returns:
            The number of passengers that were successfully boarded
        """
        # Calculate how many available seats remain
        available_seats = self.capacity - len(self.passengers)
        
        # Board only as many as can fit
        passengers_to_board = potential_passengers[:available_seats]
        self.passengers.extend(passengers_to_board)
        
        boarded_count = len(passengers_to_board)
        logger.debug(f"Bus {self.bus_id}: {boarded_count} passengers boarded")
        
        return boarded_count

    def calculate_stop_duration(self, boarding_count: int) -> int:
        """
        Calculate the duration of a bus stop based on the number of boarding passengers.
        
        Base duration: 30 seconds
        Additional penalty: 5 seconds for each passenger above 4
        
        Args:
            boarding_count: Number of passengers boarding at this stop
            
        Returns:
            Duration in seconds
        """
        base_duration = 30
        extra_passengers = max(0, boarding_count - 4)
        penalty = extra_passengers * 5
        
        total_duration = base_duration + penalty
        logger.debug(f"Bus {self.bus_id}: stop duration {total_duration}s for {boarding_count} boarding")
        
        return total_duration
