import logging
import sys
import altair as alt
import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import psycopg2
import os
import json
from urllib.parse import quote
from dotenv import load_dotenv

# Ensure src/ is on the path so sibling packages (simulation, crew) are importable
# regardless of the working directory Streamlit is launched from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from log_parser import parse_simulation_logs, get_simulation_state
from folium.plugins import TimestampedGeoJson
from simulation.orchestrator import SimulationOrchestrator
from simulation.config import HERZLIYA_NEIGHBORHOODS
from crew.metrics import MetricsCollector
from crew.board import run_topological_board_meeting

load_dotenv()

# Project root (two levels up from src/ui/app.py) — used for all data file paths
# so the app works regardless of the working directory Streamlit is launched from.
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

LOG_FILE    = os.path.join(ROOT_DIR, "simulation_output.log")
ROUTES_FILE = os.path.join(ROOT_DIR, "bus_lines_save.json")
CREW_FILE   = os.path.join(ROOT_DIR, "bus_lines_crew.json")

# Force Streamlit to write simulation logs to the file so the map can read them
file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
file_handler.setLevel(logging.INFO)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.WARNING)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[file_handler, console_handler],
    force=True  # Crucial override for Streamlit internal logger
)


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


@st.cache_data
def build_simulation_geojson(df_logs: pd.DataFrame) -> dict:
    """Build client-side animated GeoJSON frames for the simulation map."""
    if df_logs.empty:
        return {"type": "FeatureCollection", "features": []}

    import re as _re

    def _line_label(entity_id: str) -> str:
        """Derive a short Hebrew line label from a bus entity_id.
        e.g. Bus_Line1_0600 → קו1   |   Bus_Line2Reverse_0800 → קו2ר
        """
        m = _re.search(r'Bus_Line(\w+?)(?:Reverse)?_\d{4}$', entity_id)
        if not m:
            return ""
        num = _re.search(r'\d+', m.group(0).replace("Bus_Line", ""))
        line_num = num.group(0) if num else "?"
        is_reverse = "Reverse" in entity_id
        return f"קו{line_num}{'ר' if is_reverse else ''}"

    def _emoji_icon_url(emoji: str, size: int = 26, top_label: str = "", bottom_label: str = "") -> str:
        """Encode an emoji with optional labels above and below into an SVG data URI."""
        top_h    = 13 if top_label    else 0
        bottom_h = 13 if bottom_label else 0
        total_h  = top_h + size + bottom_h
        emoji_y  = top_h + size - 2          # baseline of the emoji text

        parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{total_h}">']
        if top_label:
            parts.append(
                f'<text x="{size // 2}" y="11" font-size="11" '
                f'text-anchor="middle" fill="#0055cc" font-weight="bold">{top_label}</text>'
            )
        parts.append(f'<text y="{emoji_y}" font-size="{size - 2}">{emoji}</text>')
        if bottom_label:
            parts.append(
                f'<text x="{size // 2}" y="{total_h - 1}" font-size="10" '
                f'text-anchor="middle" fill="#1a1a1a" font-weight="bold">{bottom_label}</text>'
            )
        parts.append("</svg>")
        return "data:image/svg+xml," + quote("".join(parts))

    PASSENGER_ICON_URL = _emoji_icon_url("\U0001F9CD")  # 🧍 — static, no label needed

    features = []
    timeline = sorted(df_logs['time'].unique())

    for current_time in timeline:
        state_df = get_simulation_state(df_logs, current_time)
        timestamp = f"2026-03-29T{current_time}:00"

        for _, row in state_df.iterrows():
            is_bus = row['type'] == 'bus'
            if is_bus:
                count      = int(row['passenger_count']) if 'passenger_count' in row.index else 0
                line_label = _line_label(row['entity_id'])
                icon_url   = _emoji_icon_url("\U0001F68C", top_label=line_label, bottom_label=f"{count}/50")  # 🚌
                icon_size  = [28, 52]
            else:
                icon_url  = PASSENGER_ICON_URL
                icon_size = [22, 22]

            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row['lon'], row['lat']],
                },
                "properties": {
                    "times": [timestamp],
                    "icon": "marker",
                    "iconstyle": {
                        "iconUrl": icon_url,
                        "iconSize": icon_size,
                        "iconAnchor": [icon_size[0] // 2, icon_size[1] // 2],
                    },
                    "popup": row['entity_id'],
                    "tooltip": row['entity_id'],
                },
            })

    return {"type": "FeatureCollection", "features": features}


def load_saved_lines():
    if os.path.exists(ROUTES_FILE):
        with open(ROUTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return [
        {"name": "Line 1", "stops": []},
        {"name": "Line 2", "stops": []},
        {"name": "Line 3", "stops": []},
        {"name": "Line 4", "stops": []}
    ]


def save_lines(lines_data):
    with open(ROUTES_FILE, "w", encoding="utf-8") as f:
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
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()

    # Stops are cached separately (see @st.cache_data on get_bus_stops)
    stops_df = get_bus_stops()
    stops_dict = {row['name']: (row['lat'], row['lon']) for _, row in stops_df.iterrows()}

    with open(LOG_FILE, "r", encoding="utf-8") as f:
        log_lines = f.readlines()

    return parse_simulation_logs(log_lines, stops_dict)


def render_live_simulation_tab():
    hdr_col, run_col, refresh_col = st.columns([4, 2, 1])
    
    # Define a path for our physical stats file
    STATS_FILE = os.path.join(ROOT_DIR, "last_run_stats.json")
    
    with hdr_col:
        st.subheader("Live Simulation Viewer")
        
    with run_col:
        if st.button("Run Simulation (bus_lines_save.json)", type="primary", use_container_width=True):
            with st.spinner("Running simulation engine..."):
                
                # Safely clear the log file stream before a fresh run
                for handler in logging.root.handlers:
                    if isinstance(handler, logging.FileHandler):
                        handler.stream.seek(0)
                        handler.stream.truncate(0)
                
                orch = SimulationOrchestrator(
                    neighborhoods=HERZLIYA_NEIGHBORHOODS, 
                    routes_file=ROUTES_FILE
                )
                
                while not orch.clock.is_finished():
                    orch.run_tick()
                
                stats = orch.get_stats()
                st.session_state.human_stats = stats
                st.session_state.human_orch_passengers = orch.active_passengers
                
                # Save the stats permanently to a physical file
                with open(STATS_FILE, "w", encoding="utf-8") as f:
                    json.dump(stats, f)
                
                load_and_parse_logs.clear()
                build_simulation_geojson.clear()
                
                st.rerun()

    with refresh_col:
        if st.button("Refresh Log", use_container_width=True):
            load_and_parse_logs.clear()
            build_simulation_geojson.clear()
            st.rerun()

    df_logs = load_and_parse_logs()

    if df_logs.empty:
        st.warning("No simulation output found. Click the red 'Run Simulation' button above!")
        return

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

    info_col, map_col = st.columns([1.2, 4.8])

    with info_col:
        st.markdown("#### End of Day Stats")
        
        # Load stats from file if they are missing from memory
        if "human_stats" not in st.session_state and os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                st.session_state.human_stats = json.load(f)
        
        if "human_stats" in st.session_state:
            stats = st.session_state.human_stats
            
            # Display primary high-level metrics including the new Service Rate
            st.metric("Service Rate", f"{stats.get('service_rate_pct', 0)}%")
            st.metric("Buses Dispatched", stats.get("buses_dispatched", 0))
            st.metric("Passengers Deployed", stats.get("passengers_deployed", 0))
            st.metric("Avg Commute Time", f"{stats.get('avg_commute_time_mins', 0):.1f} min")

            # Draw a clean line to separate the specific breakdown
            st.divider()
            st.markdown("**Boardings Per Line:**")

            boarding_keys = [k for k in stats.keys() if k.startswith("avg_boardings_")]
            # Loop through the dictionary and extract the individual line names and values
            for key in boarding_keys:
                line_name = key.replace("avg_boardings_", "")
                line_value = stats[key]
                st.caption(f"🚌 {line_name}: {line_value:.1f} avg")

        else:
            st.info("Run the simulation to calculate final statistics.")

        st.divider()
        st.caption("Use the map's built-in play button and time slider for smooth client-side playback.")

    with map_col:
        st_folium(
            sim_map,
            height=560,
            width="stretch",
            key="simulation_timestamped_map",
        )
        st.markdown(
            """
            <div style="font-size:12px; color:#555; margin-top:6px; line-height:1.8;">
            קו&nbsp;1 = Line&nbsp;1 &nbsp;|&nbsp;
            קו&nbsp;2 = Line&nbsp;2 &nbsp;|&nbsp;
            קו&nbsp;3 = Line&nbsp;3 &nbsp;|&nbsp;
            קו&nbsp;4 = Line&nbsp;4 &nbsp;|&nbsp;
            קו&nbsp;1ר = Line&nbsp;1&nbsp;Reverse &nbsp;|&nbsp;
            קו&nbsp;2ר = Line&nbsp;2&nbsp;Reverse &nbsp;|&nbsp;
            קו&nbsp;3ר = Line&nbsp;3&nbsp;Reverse &nbsp;|&nbsp;
            קו&nbsp;4ר = Line&nbsp;4&nbsp;Reverse
            </div>
            """,
            unsafe_allow_html=True,
        )


def render_ai_optimizer_tab():
    st.header("Human vs. AI: Network A/B Testing")
    st.write("Run the baseline simulation, then let the AI Board attempt to optimize the routes.")

    col1, col2 = st.columns(2)

    # --- LEFT COLUMN: HUMAN BASELINE ---
    with col1:
        st.subheader("Baseline (Human Routes)")
        if st.button("1. Run Baseline Simulation", use_container_width=True):
            with st.spinner("Simulating human routes (bus_lines_save.json)..."):
                # Clear out the log file before a fresh run
                open(LOG_FILE, "w").close()
                
                orch = SimulationOrchestrator(neighborhoods=HERZLIYA_NEIGHBORHOODS, routes_file=ROUTES_FILE)
                while not orch.clock.is_finished():
                    orch.run_tick()
                
                # Save results to session state so they persist
                st.session_state.human_stats = orch.get_stats()
                st.session_state.human_orch_passengers = orch.active_passengers
                st.success("Baseline simulation complete!")

        # Display baseline stats if they exist
        if "human_stats" in st.session_state:
            h_stats = st.session_state.human_stats
            st.metric("Service Rate", f"{h_stats['service_rate_pct']}%")
            st.metric("Unserved Passengers", h_stats['passengers_unserved'])
            st.metric("Avg Commute Time", f"{h_stats['avg_commute_time_mins']:.1f} min")
            st.metric("Avg Walking Time", f"{h_stats['avg_walking_time_mins']:.1f} min")
            st.metric("Avg Waiting Time", f"{h_stats['avg_waiting_time_mins']:.1f} min")

    # --- RIGHT COLUMN: AI OPTIMIZATION ---
    with col2:
        st.subheader("Optimized (AI Routes)")
        
        # Button is disabled until the human baseline is run
        is_disabled = "human_stats" not in st.session_state
        if st.button("2. Convene AI Board & Simulate", use_container_width=True, disabled=is_disabled):
            
            with st.spinner("AI Board is redesigning the network..."):
                collector = MetricsCollector(LOG_FILE)
                wait_time_metrics = collector.get_average_wait_times()
                
                with open(ROUTES_FILE, encoding="utf-8") as f:
                    current_lines = json.load(f)
                    
                # Build OD failures from the baseline run
                unserved_od_metrics = {}
                for p in st.session_state.human_orch_passengers:
                    key = f"{p.origin_stop} to {p.target_stop}"
                    unserved_od_metrics[key] = unserved_od_metrics.get(key, 0) + 1
                    
                valid_stops_list = get_bus_stops()['name'].tolist()

                # Trigger CrewAI
                board_decision = run_topological_board_meeting(
                    current_lines=current_lines,
                    wait_time_metrics=wait_time_metrics,
                    unserved_od_metrics=unserved_od_metrics,
                    valid_stops_list=valid_stops_list
                )
                
                # Save AI routes
                with open(CREW_FILE, "w", encoding="utf-8") as f:
                    json.dump(json.loads(board_decision), f, ensure_ascii=False, indent=4)
                    
            with st.spinner("Simulating AI routes (bus_lines_crew.json)..."):
                open(LOG_FILE, "w").close()
                
                orch_ai = SimulationOrchestrator(neighborhoods=HERZLIYA_NEIGHBORHOODS, routes_file=CREW_FILE)
                while not orch_ai.clock.is_finished():
                    orch_ai.run_tick()
                
                st.session_state.ai_stats = orch_ai.get_stats()
                st.success("AI optimization and simulation complete!")

        # Display AI stats with delta indicators
        if "ai_stats" in st.session_state:
            h_stats = st.session_state.human_stats
            a_stats = st.session_state.ai_stats

            srv_delta      = a_stats['service_rate_pct']    - h_stats['service_rate_pct']
            unserved_delta = a_stats['passengers_unserved'] - h_stats['passengers_unserved']
            commute_delta  = a_stats['avg_commute_time_mins'] - h_stats['avg_commute_time_mins']
            walking_delta  = a_stats['avg_walking_time_mins'] - h_stats['avg_walking_time_mins']
            wait_delta     = a_stats['avg_waiting_time_mins'] - h_stats['avg_waiting_time_mins']

            st.metric("Service Rate", f"{a_stats['service_rate_pct']}%", delta=f"{srv_delta:.1f}%")
            st.metric("Unserved Passengers", a_stats['passengers_unserved'], delta=unserved_delta, delta_color="inverse")
            st.metric("Avg Commute Time", f"{a_stats['avg_commute_time_mins']:.1f} min", delta=f"{commute_delta:.1f} min", delta_color="inverse")
            st.metric("Avg Walking Time", f"{a_stats['avg_walking_time_mins']:.1f} min", delta=f"{walking_delta:.1f} min", delta_color="inverse")
            st.metric("Avg Waiting Time", f"{a_stats['avg_waiting_time_mins']:.1f} min", delta=f"{wait_delta:.1f} min",   delta_color="inverse")

    # --- COMPARISON CHART (shown once both runs are done) ---
    if "human_stats" in st.session_state and "ai_stats" in st.session_state:
        h_stats = st.session_state.human_stats
        a_stats = st.session_state.ai_stats

        st.divider()
        st.subheader("Head-to-Head Comparison")

        comparison_metrics = [
            ("Service Rate (%)",       float(h_stats["service_rate_pct"]),     float(a_stats["service_rate_pct"])),
            ("Unserved Passengers",    float(h_stats["passengers_unserved"]),  float(a_stats["passengers_unserved"])),
            ("Avg Commute (min)",      h_stats["avg_commute_time_mins"],       a_stats["avg_commute_time_mins"]),
            ("Avg Walking (min)",      h_stats["avg_walking_time_mins"],       a_stats["avg_walking_time_mins"]),
            ("Avg Waiting (min)",      h_stats["avg_waiting_time_mins"],       a_stats["avg_waiting_time_mins"]),
        ]

        rows = []
        for label, h_val, a_val in comparison_metrics:
            rows.append({"Metric": label, "Route": "Human", "Value": h_val})
            rows.append({"Metric": label, "Route": "AI",    "Value": a_val})
        df_cmp = pd.DataFrame(rows)

        chart = (
            alt.Chart(df_cmp)
            .mark_bar()
            .encode(
                x=alt.X("Route:N", axis=alt.Axis(title=None, labelAngle=0), sort=["Human", "AI"]),
                y=alt.Y("Value:Q", axis=alt.Axis(title=None)),
                color=alt.Color(
                    "Route:N",
                    scale=alt.Scale(domain=["Human", "AI"], range=["#4C78A8", "#F58518"]),
                    legend=alt.Legend(orient="bottom"),
                ),
                tooltip=[
                    alt.Tooltip("Metric:N"),
                    alt.Tooltip("Route:N"),
                    alt.Tooltip("Value:Q", format=".2f"),
                ],
            )
            .properties(width=140, height=180)
            .facet(facet=alt.Facet("Metric:N", title=None), columns=5)
            .resolve_scale(y="independent")
        )
        st.altair_chart(chart, use_container_width=True)


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

    tab1, tab2, tab3 = st.tabs(["Route Builder", "Live Simulation", "AI Optimizer"])

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

    # ==========================================
    # TAB 3: AI OPTIMIZER & A/B TESTING     
    # ==========================================
    with tab3:
        render_ai_optimizer_tab()


if __name__ == "__main__":
    main()
