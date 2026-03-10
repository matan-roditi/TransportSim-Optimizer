import logging
from datetime import time

# Setup logging for the dispatcher
logger = logging.getLogger(__name__)


class Dispatcher:
    """
    Manages bus dispatch scheduling based on time period.
    Dispatch frequencies:
    - Peak 1 (06:00-10:00): Every 15 minutes
    - Off-peak (10:00-16:00): Every 30 minutes
    - Peak 2 (16:00-20:00): Every 15 minutes
    - Night (20:00-22:00): Every 30 minutes
    """

    def __init__(self):
        """Initialize the dispatcher with no internal state."""
        logger.info("Dispatcher initialized")

    def should_dispatch(self, current_time: time) -> bool:
        """
        Determine if a bus should be dispatched at the given time.
        """
        hour = current_time.hour
        minute = current_time.minute
        
        # Peak hours 1: 06:00-10:00 (every 15 minutes)
        if 6 <= hour < 10:
            return minute % 15 == 0
        
        # Off-peak hours: 10:00-16:00 (every 30 minutes)
        if 10 <= hour < 16:
            return minute % 30 == 0
        
        # Peak hours 2: 16:00-20:00 (every 15 minutes)
        if 16 <= hour < 20:
            return minute % 15 == 0
        
        # Night hours: 20:00-22:00 (every 30 minutes)
        if 20 <= hour < 22:
            return minute % 30 == 0
        
        # Outside service hours
        return False
