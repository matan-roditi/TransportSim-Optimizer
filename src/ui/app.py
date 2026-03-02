import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import psycopg2
import os
import json
from dotenv import load_dotenv

load_dotenv()


def get_bus_stops():
    conn = psycopg2.connect(
        host=os.getenv("PG_HOST"),
        port=os.getenv("PG_PORT"),
        database=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PASSWORD")
    )
    # Fetching the 20 selected stops from the database
    query = "SELECT name, lat, lon FROM stops LIMIT 20;"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

def load_saved_lines():
    if os.path.exists("bus_lines_save.json"):
        with open("bus_lines_save.json", "r", encoding="utf-8") as f:
            return json.load(f)
    return [
        {"name": "Line 1", "stops": []},
        {"name": "Line 2", "stops": []},
        {"name": "Line 3", "stops": []},
        {"name": "Line 4", "stops": []}
    ]


def save_lines(lines_data):
    with open("bus_lines_save.json", "w", encoding="utf-8") as f:
        json.dump(lines_data, f, ensure_ascii=False, indent=4)


def get_edge_travel_time(stop_name_a, stop_name_b):
    """Fetches travel time (seconds) between two station names from the DB."""
    try:
        conn = psycopg2.connect(
            host=os.getenv("PG_HOST"),
            port=os.getenv("PG_PORT"),
            database=os.getenv("PG_DB"),
            user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD")
        )
        # We join edges and travel_times to find the specific 'cost' for this segment
        query = """
            SELECT tt.seconds 
            FROM edges e
            JOIN stops s1 ON e.from_stop_id = s1.stop_id
            JOIN stops s2 ON e.to_stop_id = s2.stop_id
            JOIN travel_times tt ON e.id = tt.edge_id
            WHERE s1.name = %s AND s2.name = %s
            LIMIT 1;
        """
        with conn.cursor() as cur:
            cur.execute(query, (stop_name_a, stop_name_b))
            result = cur.fetchone()
        conn.close()
        return result[0] if result else None
    except Exception as e:
        st.error(f"Error fetching travel time: {e}")
        return None
    

def main():
    st.set_page_config(page_title="Herzliya Map", layout="wide")

    # Initialize the list of bus lines in session state if not already there
    if 'bus_lines' not in st.session_state:
        st.session_state.bus_lines = load_saved_lines()
    
    # Track which line is currently "active" for adding stations
    if 'active_line_index' not in st.session_state:
        st.session_state.active_line_index = None

    st.title("Herzliya Road Network")

    # Split layout into a map and a control panel
    col_map, col_ctrl = st.columns([3, 1])

    with col_ctrl:
        st.header("Bus Lines")
        
        # Display each line and its buttons
        for i, line in enumerate(st.session_state.bus_lines):
            # Button to toggle the view of this line
            if st.button(f"🚌 {line['name']}", key=f"btn_{i}"):
                if st.session_state.active_line_index == i:
                    st.session_state.active_line_index = None
                else:
                    st.session_state.active_line_index = i
                st.rerun()

            # Only show stations and editing mode if this line is active
            if st.session_state.active_line_index == i:
                st.info(f"Click a yellow pinpoint on the map to add it to {line['name']}")
                st.write("**Current Stations:**")
                for stop in line["stops"]:
                    st.write(f"📍 {stop}")
                
                if st.button("Save", key=f"save_{i}", type="primary"):
                    save_lines(st.session_state.bus_lines)
                    st.success("Bus lines saved successfully!")
                
            st.divider()

    with col_map:
        m = folium.Map(location=[32.1663, 34.825], zoom_start=14)
        df = get_bus_stops()

        for _, stop in df.iterrows():
            folium.CircleMarker(
                location=[stop['lat'], stop['lon']],
                radius=7,
                popup=stop['name'],
                tooltip=stop['name'], 
                color="black",
                fill=True,
                fill_color="yellow",
                fill_opacity=0.9
            ).add_to(m)

        # Capture map interaction data
        map_data = st_folium(m, width=900, height=600, key="herzliya_map")

        if 'last_processed_click' not in st.session_state:
            st.session_state.last_processed_click = None

        # Logic: If a pinpoint was clicked AND we are in 'Adding Mode'
        clicked_stop = map_data.get("last_object_clicked_tooltip")
        
        # Check if we have already processed this exact click event
        if clicked_stop and clicked_stop != st.session_state.last_processed_click:
            st.session_state.last_processed_click = clicked_stop

            if st.session_state.active_line_index is not None:
                line_idx = st.session_state.active_line_index
                
                # Add the stop if it's not already in the line
                if clicked_stop not in st.session_state.bus_lines[line_idx]["stops"]:
                    st.session_state.bus_lines[line_idx]["stops"].append(clicked_stop)
                    st.rerun()   #Refresh UI to show the new stop name immediately


if __name__ == "__main__":
    main()