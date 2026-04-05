from __future__ import annotations

import os
from math import radians, sin, cos, asin, sqrt
from pathlib import Path

import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
IN_FILE = BASE_DIR / "herzliya_top20_selected.csv"

# PostgreSQL connection parameters (loaded from .env)
PG_HOST = os.getenv("PG_HOST", "localhost")
PG_PORT = int(os.getenv("PG_PORT", "5432"))
PG_DB = os.getenv("PG_DB", "transportsim")
PG_USER = os.getenv("PG_USER", "transportsim")
PG_PASSWORD = os.getenv("PG_PASSWORD", "")


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two lat/lon points."""
    r = 6371000.0
    lat1r, lon1r = radians(lat1), radians(lon1)
    lat2r, lon2r = radians(lat2), radians(lon2)
    dlat = lat2r - lat1r
    dlon = lon2r - lon1r
    a = sin(dlat / 2) ** 2 + cos(lat1r) * cos(lat2r) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    return r * c


def main() -> None:
    if not IN_FILE.exists():
        raise FileNotFoundError(f"Missing file: {IN_FILE}")

    df = pd.read_csv(IN_FILE, encoding="utf-8-sig")
    required = {"stop_id", "stop_name", "stop_lat", "stop_lon"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV missing columns: {missing}")

    # k-nearest neighbors per stop (directed)
    k = 8

    conn = psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
    )

    try:
        with conn:
            with conn.cursor() as cur:
                # Insert / upsert stops
                stop_rows = [
                    (str(r["stop_id"]), str(r["stop_name"]), float(r["stop_lat"]), float(r["stop_lon"]))
                    for _, r in df.iterrows()
                ]

                execute_values(
                    cur,
                    """
                    INSERT INTO stops (stop_id, name, lat, lon)
                    VALUES %s
                    ON CONFLICT (stop_id) DO UPDATE
                      SET name = EXCLUDED.name,
                          lat  = EXCLUDED.lat,
                          lon  = EXCLUDED.lon;
                    """,
                    stop_rows,
                    page_size=200,
                )

                # Build kNN edges
                edges = []
                for _, s in df.iterrows():
                    distances = []
                    for _, t in df.iterrows():
                        if s["stop_id"] == t["stop_id"]:
                            continue
                        d = haversine_m(
                            float(s["stop_lat"]), float(s["stop_lon"]),
                            float(t["stop_lat"]), float(t["stop_lon"]),
                        )
                        distances.append((d, str(t["stop_id"])))

                    distances.sort(key=lambda x: x[0])
                    for d, to_id in distances[:k]:
                        edges.append((str(s["stop_id"]), str(to_id), float(d)))

                execute_values(
                    cur,
                    """
                    INSERT INTO edges (from_stop_id, to_stop_id, distance_m)
                    VALUES %s
                    ON CONFLICT (from_stop_id, to_stop_id) DO UPDATE
                      SET distance_m = EXCLUDED.distance_m;
                    """,
                    edges,
                    page_size=500,
                )

        print(f"Done. Inserted/updated stops={len(df)} and edges≈{len(df)*k} (k={k}, directed).")

    finally:
        conn.close()


if __name__ == "__main__":
    main()