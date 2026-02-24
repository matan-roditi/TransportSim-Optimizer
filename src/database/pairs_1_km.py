from pathlib import Path
import pandas as pd
from math import radians, sin, cos, asin, sqrt

BASE_DIR = Path(__file__).resolve().parent
INPUT_CSV = BASE_DIR / "herzliya_stops_clean.csv"
OUTPUT_CSV = BASE_DIR / "herzliya_pairs_within_1km.csv"

MAX_KM = 1

def haversine_km(lat1, lon1, lat2, lon2):
    """Great-circle distance in km."""
    R = 6371.0088
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * R * asin(sqrt(a))

def main():
    stops = pd.read_csv(INPUT_CSV, encoding="utf-8")

    # Ensure numeric lat/lon
    stops["stop_lat"] = pd.to_numeric(stops["stop_lat"], errors="coerce")
    stops["stop_lon"] = pd.to_numeric(stops["stop_lon"], errors="coerce")
    stops = stops.dropna(subset=["stop_lat", "stop_lon"])

    rows = stops[["stop_id", "stop_lat", "stop_lon"]].itertuples(index=False, name=None)

    rows = list(rows)  # small enough (~292), simplifies loops
    pairs = []

    for i in range(len(rows)):
        id1, lat1, lon1 = rows[i]
        for j in range(i + 1, len(rows)):
            id2, lat2, lon2 = rows[j]
            d = haversine_km(lat1, lon1, lat2, lon2)
            if d <= MAX_KM:
                pairs.append((int(id1), int(id2), float(d)))

    pairs_df = pd.DataFrame(pairs, columns=["stop_id_a", "stop_id_b", "air_distance_km"])
    pairs_df.to_csv(OUTPUT_CSV, index=False, encoding="utf-8-sig")

    print("Done")
    print("Stops:", len(stops))
    print("Pairs within 1 km:", len(pairs_df))
    print("Saved:", OUTPUT_CSV.name)

if __name__ == "__main__":
    main()