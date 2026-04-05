import json
import logging
import random
import os
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Define the paths based on your project structure
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(current_dir, ".."))
input_file = os.path.join(root_dir, "herzliya_demand.json")
output_file = os.path.join(root_dir, "herzliya_demand_scaled.json")

MULTIPLIER = 8

# Define strict operational boundaries
MIN_TIME = datetime.strptime("06:00", "%H:%M")
MAX_TIME = datetime.strptime("22:00", "%H:%M")


def add_time_jitter(time_str: str) -> str:
    # Parse the original time from the LLM
    base_time = datetime.strptime(time_str, "%H:%M")

    # Generate a random jitter between -10 and +10 minutes
    jitter_minutes = random.randint(-10, 10)

    # Apply the shift
    new_time = base_time + timedelta(minutes=jitter_minutes)

    # Clamp to boundaries to prevent out-of-bounds simulation errors
    if new_time < MIN_TIME:
        new_time = MIN_TIME
    elif new_time > MAX_TIME:
        new_time = MAX_TIME

    # Format back to the string structure your simulation expects
    return new_time.strftime("%H:%M")


def scale_passengers():
    random.seed(42)  # fixed seed for reproducible jitter across runs
    logger.info(f"Reading original demand from {input_file}...")

    with open(input_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    original_passengers = data.get("passengers", [])
    scaled_passengers = []

    logger.info(f"Loaded {len(original_passengers)} base passengers. Scaling by {MULTIPLIER}x...")

    # Create the clones and apply the time shift
    for _ in range(MULTIPLIER):
        for p in original_passengers:
            new_passenger = p.copy()
            new_passenger["departing_time"] = add_time_jitter(p["departing_time"])
            scaled_passengers.append(new_passenger)

    # Sort chronologically so the simulation engine reads it sequentially
    scaled_passengers.sort(key=lambda x: x["departing_time"])

    # Save to a new file so we do not overwrite the original LLM output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"passengers": scaled_passengers}, f, ensure_ascii=False, indent=4)

    logger.info(f"Success! Generated {len(scaled_passengers)} passengers.")
    logger.info(f"Saved massive dataset to: {output_file}")


if __name__ == "__main__":
    scale_passengers()
