import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import psycopg2
import os
import json
from dotenv import load_dotenv
from log_parser import parse_simulation_logs, get_simulation_state
from folium.plugins import TimestampedGeoJson

load_dotenv()


@st.cache_data(ttl=300)
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


@st.cache_data(ttl=300)
def get_stops_display_data():
    """Build the static stop data used by the simulation map once per cache window."""
    stops_df = get_bus_stops().copy()
    # PyDeck TextLayer has no RTL support; reversing the string fixes Hebrew display
    stops_df['name_display'] = stops_df['name'].apply(lambda s: s[::-1])
    return stops_df.to_dict("records")


@st.cache_data
def build_simulation_geojson(df_logs: pd.DataFrame) -> dict:
    """Build client-side animated GeoJSON frames for the simulation map."""
    if df_logs.empty:
        return {"type": "FeatureCollection", "features": []}

    features = []
    timeline = sorted(df_logs['time'].unique())

    for current_time in timeline:
        state_df = get_simulation_state(df_logs, current_time)
        timestamp = f"2026-03-29T{current_time}:00"

        for _, row in state_df.iterrows():
            is_bus = row['type'] == 'bus'
            radius = 8 if is_bus else 5
            fill_color = '#0078FF' if is_bus else '#FF5050'

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row['lon'], row['lat']],
                },
                "properties": {
                    "times": [timestamp],
                    "icon": "circle",
                    "iconstyle": {
                        "fillColor": fill_color,
                        "fillOpacity": 0.9,
                        "stroke": True,
                        "color": "#1F1F1F",
                        "weight": 1,
                        "radius": radius,
                    },
                    "popup": row['entity_id'],
                    "tooltip": row['entity_id'],
                },
            })

    return {"type": "FeatureCollection", "features": features}


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
            JOIN travel_times tt ON e.edge_id = tt.edge_id
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

@st.cache_data
def load_and_parse_logs():
    """Read and parse the simulation log once until the user explicitly refreshes it."""
    if not os.path.exists("simulation_output.log"):
        return pd.DataFrame()

    # Stops are cached separately (see @st.cache_data on get_bus_stops)
    stops_df = get_bus_stops()
    stops_dict = {row['name']: (row['lat'], row['lon']) for _, row in stops_df.iterrows()}

    with open("simulation_output.log", "r", encoding="utf-8") as f:
        log_lines = f.readlines()

    return parse_simulation_logs(log_lines, stops_dict)


def render_live_simulation_tab():
    # Header row with refresh button
    hdr_col, refresh_col = st.columns([5, 1])
    with hdr_col:
        st.subheader("Live Simulation Viewer")
    with refresh_col:
        if st.button("Refresh Log", use_container_width=True, help="Re-read simulation_output.log from disk"):
            load_and_parse_logs.clear()
            build_simulation_geojson.clear()
            st.rerun()

    df_logs = load_and_parse_logs()

    if df_logs.empty:
        st.warning("No simulation output found. Run your simulation script first!")
        return

    timeline = sorted(df_logs['time'].unique())
    latest_state = get_simulation_state(df_logs, timeline[-1])
    active_buses = len(latest_state[latest_state['type'] == 'bus'])
    active_passengers = len(latest_state[latest_state['type'] == 'passenger'])

    sim_map = folium.Map(location=[32.1706, 34.823], zoom_start=14, tiles="cartodbpositron")

    for stop in get_bus_stops().itertuples(index=False):
        folium.CircleMarker(
            location=[stop.lat, stop.lon],
            radius=6,
            tooltip=stop.name,
            color="black",
            fill=True,
            fill_color="yellow",
            fill_opacity=0.9,
            weight=1,
        ).add_to(sim_map)

    TimestampedGeoJson(
        build_simulation_geojson(df_logs),
        period="PT1M",
        duration="PT1M",
        transition_time=400,
        auto_play=False,
        loop=False,
        max_speed=4,
        loop_button=True,
        date_options="HH:mm",
        time_slider_drag_update=True,
    ).add_to(sim_map)

    info_col, map_col = st.columns([0.9, 5.1])

    with info_col:
        st.metric("Frames", len(timeline))
        st.metric("Last Timestamp", timeline[-1])
        st.metric("Last Frame Entities", f"🚌 {active_buses}  🚶 {active_passengers}")
        st.caption("Use the map's built-in play button and time slider for smooth client-side playback.")

    with map_col:
        st_folium(
            sim_map,
            height=560,
            use_container_width=True,
            key="simulation_timestamped_map",
        )


def main():
    st.set_page_config(page_title="Herzliya Map", layout="wide")

    st.markdown(
        """
        <style>
            [data-testid="stAppViewContainer"] .main .block-container {
                max-width: 1450px;
                padding-top: 1.2rem;
                padding-left: 2rem;
                padding-right: 2rem;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Initialize the list of bus lines in session state if not already there
    if 'bus_lines' not in st.session_state:
        st.session_state.bus_lines = load_saved_lines()
    
    # Track which line is currently "active" for adding stations
    if 'active_line_index' not in st.session_state:
        st.session_state.active_line_index = None

    st.title("Herzliya Transit Command Center")
    
    # Create the dual-mode interface
    tab1, tab2 = st.tabs(["Route Builder", "Live Simulation"])

    # ==========================================
    # TAB 1: THE INTERACTIVE ROUTE BUILDER
    # ==========================================
    with tab1:
        col_map, col_ctrl = st.columns([3, 1])

    with col_ctrl:
        st.header("Bus Lines")

        # Display the line buttons in a single row
        button_cols = st.columns(len(st.session_state.bus_lines))
        for i, line in enumerate(st.session_state.bus_lines):
            with button_cols[i]:
                # Button to toggle the view of this line
                if st.button(f"{line['name']}", key=f"btn_{i}"):
                    if st.session_state.active_line_index == i:
                        st.session_state.active_line_index = None
                    else:
                        st.session_state.active_line_index = i
                    st.rerun()  # Refresh UI to show/hide stops immediately
                    
        st.divider()

        # Only show the details (stations, etc.) for the currently active line
        if st.session_state.active_line_index is not None:
            i = st.session_state.active_line_index
            line = st.session_state.bus_lines[i]
            
            st.markdown(f"### 🚌 {line['name']}")
            st.write("**Current Stations:**")
            
            num_stops = len(line["stops"])
            for idx, stop_name in enumerate(line["stops"]):
                # Split the row into two columns for the name and the delete button
                name_col, del_col = st.columns([4, 1])
                
                with name_col:
                    st.write(f"📍 {stop_name}")
                
                with del_col:
                    if st.button("X", key=f"del_{i}_{idx}"):
                        line["stops"].pop(idx)
                        st.rerun()  # Refresh UI to reflect deletion immediately
                        
                # If there is a next stop, show the travel time between current and next
                if idx < num_stops - 1:
                    next_stop = line["stops"][idx + 1]
                    travel_sec = get_edge_travel_time(stop_name, next_stop)
                    
                    if travel_sec is not None:
                        # Convert seconds to minutes for readability
                        minutes = travel_sec // 60
                        seconds = travel_sec % 60
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp; *Travel Time: {minutes}m {seconds}s*")
                    else:
                        st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp; *No direct edge found in DB*")

            st.info(f"Click a yellow pinpoint on the map to add it to {line['name']}")
            
            if st.button("Save", key=f"save_{i}", type="primary"):
                save_lines(st.session_state.bus_lines)
                st.success("Bus lines saved successfully!")

            st.divider()

    with col_map:
        m = folium.Map(location=[32.1706, 34.823], zoom_start=14)
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
                    st.rerun()

    # ==========================================
    # TAB 2: THE LIVE SIMULATION PLAYBACK
    # ==========================================
    with tab2:
        render_live_simulation_tab()


if __name__ == "__main__":
    main()
