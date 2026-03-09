import logging
from datetime import datetime, timedelta, time

# Setup logging for the simulation temporal engine
logger = logging.getLogger(__name__)

class SimulationClock:
    """
    Handles the 1-minute time steps for the transportation simulator.
    Operates between 06:00 and 22:00 to model a full service day.
    """

    def __init__(self, start_time: str, end_time: str):
        # Initialize simulation boundaries using datetime objects
        self.current_dt = datetime.strptime(start_time, "%H:%M")
        self.end_dt = datetime.strptime(end_time, "%H:%M")
        self.tick_interval = timedelta(minutes=1)
        
        logger.info(f"Simulation clock started at {start_time}")

    @property
    def current_time(self) -> time:
        # Provide a clean time object for agent decision-making
        return self.current_dt.time()

    def tick(self) -> None:
        # Advance the simulation by the defined 1-minute step
        self.current_dt += self.tick_interval
        logger.debug(f"Tick: {self.current_time}")

    def is_finished(self) -> bool:
        # Check if the simulator has reached the 22:00 cutoff
        return self.current_dt >= self.end_dt