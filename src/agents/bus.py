from __future__ import annotations
import logging
from typing import List, TYPE_CHECKING

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

    def __init__(self, bus_id: str, capacity: int = 50) -> None:
        # Unique identifier for the bus
        self.bus_id = bus_id
        # Maximum passenger capacity
        self.capacity = capacity
        # We now specify that this list will only hold PassengerAgent objects
        self.passengers: List[PassengerAgent] = []
        logger.info(f"Bus {bus_id} created with capacity {capacity}")

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
