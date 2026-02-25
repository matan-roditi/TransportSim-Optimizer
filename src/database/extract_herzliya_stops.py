from pathlib import Path
import pandas as pd

# Base folder of this script
BASE_DIR = Path(__file__).resolve().parent

# Input and output paths
STOPS_FILE = BASE_DIR / "stops.txt"
OUT_FULL = BASE_DIR / "herzliya_stops.csv"
OUT_CLEAN = BASE_DIR / "herzliya_stops_clean.csv"

CITY_PATTERN = r"עיר:\s*הרצליה\b"


def extract_herzliya_stops():

    # Load stops.txt
    stops = pd.read_csv(STOPS_FILE, encoding="utf-8")

    # Filter Herzliya stops
    herzliya = stops[
        stops["stop_desc"].astype(str).str.contains(CITY_PATTERN, na=False)
    ].copy()

    # Convert coordinates safely
    herzliya["stop_lat"] = pd.to_numeric(herzliya["stop_lat"], errors="coerce")
    herzliya["stop_lon"] = pd.to_numeric(herzliya["stop_lon"], errors="coerce")

    # Remove bad rows
    herzliya = herzliya.dropna(subset=["stop_lat", "stop_lon"])

    # Save full version
    herzliya.to_csv(OUT_FULL, index=False, encoding="utf-8-sig")

    # Save clean version (recommended for routing)
    herzliya[[
        "stop_id",
        "stop_name",
        "stop_lat",
        "stop_lon"
    ]].to_csv(
        OUT_CLEAN,
        index=False,
        encoding="utf-8-sig"
    )

    print("Done")
    print("Number of Herzliya stops:", len(herzliya))
    print("Saved:", OUT_FULL.name)
    print("Saved:", OUT_CLEAN.name)


if __name__ == "__main__":
    extract_herzliya_stops()