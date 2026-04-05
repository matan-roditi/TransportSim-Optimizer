import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()


def create_cloud_tables():
    # Establish connection to the Neon database
    conn = psycopg2.connect(
        host=os.environ["PG_HOST"],
        port=int(os.environ["PG_PORT"]),
        dbname=os.environ["PG_DB"],
        user=os.environ["PG_USER"],
        password=os.environ["PG_PASSWORD"]
    )
    
    # Auto-commit ensures the tables are saved immediately without needing a manual commit
    conn.autocommit = True
    
    try:
        with conn.cursor() as cur:
            # Construct the stops table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS stops (
                stop_id INT PRIMARY KEY,
                name VARCHAR(255),
                lat FLOAT,
                lon FLOAT
            );
            """)
            
            # Construct the edges table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS edges (
                edge_id SERIAL PRIMARY KEY,
                from_stop_id INT REFERENCES stops(stop_id),
                to_stop_id INT REFERENCES stops(stop_id),
                distance FLOAT
            );
            """)
            
            # Construct the travel times table
            cur.execute("""
            CREATE TABLE IF NOT EXISTS travel_times (
                id SERIAL PRIMARY KEY,
                edge_id INT REFERENCES edges(edge_id),
                time_bucket INT,
                seconds FLOAT
            );
            """)
            
            print("Successfully created the schema in the Neon cloud database!")
            
    except Exception as e:
        print(f"Failed to create tables: {e}")
        
    finally:
        conn.close()


if __name__ == "__main__":
    create_cloud_tables()
