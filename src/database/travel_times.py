import psycopg2
import requests
from psycopg2.extras import execute_values
from dotenv import load_dotenv
import os

load_dotenv()

PG_HOST = os.environ["PG_HOST"]
PG_PORT = int(os.environ["PG_PORT"])
PG_DB = os.environ["PG_DB"]
PG_USER = os.environ["PG_USER"]
PG_PASSWORD = os.environ["PG_PASSWORD"]

OSRM_BASE = "http://router.project-osrm.org"

def fetch_edges(conn):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT
              e.edge_id,
              s1.lat AS from_lat,
              s1.lon AS from_lon,
              s2.lat AS to_lat,
              s2.lon AS to_lon
            FROM edges e
            JOIN stops s1 ON s1.stop_id = e.from_stop_id
            JOIN stops s2 ON s2.stop_id = e.to_stop_id;
        """)
        return cur.fetchall()

def osrm_duration_seconds(from_lat, from_lon, to_lat, to_lon) -> int | None:
    # OSRM expects lon,lat (note the order!)
    url = (
        f"{OSRM_BASE}/route/v1/driving/"
        f"{from_lon},{from_lat};{to_lon},{to_lat}"
        f"?overview=false"
    )
    r = requests.get(url, timeout=20)
    if r.status_code != 200:
        return None
    data = r.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        return None
    return int(round(data["routes"][0]["duration"]))

def upsert_travel_times(conn, rows):
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO travel_times (edge_id, time_bucket, seconds)
            VALUES %s
            ON CONFLICT (edge_id, time_bucket) DO UPDATE
              SET seconds = EXCLUDED.seconds;
            """,
            rows,
            page_size=500,
        )

def main():
    conn = psycopg2.connect(
        host=PG_HOST, port=PG_PORT, dbname=PG_DB, user=PG_USER, password=PG_PASSWORD
    )

    try:
        edges = fetch_edges(conn)

        bucket = 0
        out_rows = []
        failures = 0

        for edge_id, from_lat, from_lon, to_lat, to_lon in edges:
            secs = osrm_duration_seconds(from_lat, from_lon, to_lat, to_lon)
            if secs is None:
                failures += 1
                continue
            out_rows.append((int(edge_id), bucket, int(secs)))

        with conn:
            upsert_travel_times(conn, out_rows)

        print(f"Updated {len(out_rows)} edges in travel_times (bucket={bucket}). Failures={failures}")

    finally:
        conn.close()

if __name__ == "__main__":
    main()