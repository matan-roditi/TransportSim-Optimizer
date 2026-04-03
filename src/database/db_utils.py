import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()


def fetch_travel_times_summary():
    # Connect to the database using the environment variables from your travel_times.py
    conn = psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=int(os.environ["PG_PORT"]),
        dbname=os.environ["PG_DB"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"]
    )

    try:
        with conn.cursor() as cur:
            # Join travel_times with edges and stops to get actual names
            # We filter by time_bucket=0 to get the baseline driving speeds
            cur.execute("""
                SELECT 
                    s1.name AS from_stop, 
                    s2.name AS to_stop, 
                    t.seconds 
                FROM travel_times t
                JOIN edges e ON t.edge_id = e.edge_id
                JOIN stops s1 ON e.from_stop_id = s1.stop_id
                JOIN stops s2 ON e.to_stop_id = s2.stop_id
                WHERE t.time_bucket = 0;
            """)
            rows = cur.fetchall()

            # Convert the raw seconds into minutes and format for the LLM prompt
            summary_lines = []
            for from_stop, to_stop, seconds in rows:
                minutes = round(seconds / 60.0, 1)
                summary_lines.append(f"[{from_stop}] to [{to_stop}]: {minutes}m")

            # Combine into a single string to be injected into the Architect task
            return "\n".join(summary_lines)

    except Exception as e:
        print(f"Error fetching travel times: {e}")
        return "Travel time data unavailable."
    finally:
        conn.close()
