import re
import pandas as pd


def parse_simulation_logs(log_lines, stops_dict):
    """
    Parses raw simulation logs into a structured Pandas DataFrame.
    Extracts time, entity type, ID, coordinates, and assigns map icons.
    Entities are marked 'done' when they complete their journey so they
    can be removed from the map by get_simulation_state.
    """
    parsed_data = []

    # Regex patterns to extract specific data from the log strings
    time_pattern = re.compile(r'\[(\d{2}:\d{2})\]')
    passenger_pattern = re.compile(r'(passenger #\d+) deployed with origin:\(([\d.]+),\s*([\d.]+)\)')
    # Matches the bus ID and the stop name right before the "|" character
    bus_pattern = re.compile(r'(Bus_Line[a-zA-Z0-9_]+) at ([^|]+)\s*\|')

    # --- Completion patterns ---
    # "[06:12] Bus_Line1_0600 completed forward route"
    bus_done_bracket = re.compile(r'\[(\d{2}:\d{2})\] (Bus_Line[a-zA-Z0-9_]+) completed forward route')
    # "Bus Bus_Line4_0600 has completed its route at ..."
    bus_done_nobracket = re.compile(r'Bus (Bus_Line[a-zA-Z0-9_]+) has completed its route')
    # "passenger #3 arrived to dest"
    passenger_done = re.compile(r'(passenger #\d+) arrived to dest')

    # Track the most-recent sim time so no-bracket lines get the right tick
    current_time = "00:00"

    for line in log_lines:
        # Always update current_time when a bracket time appears
        time_match = time_pattern.search(line)
        if time_match:
            current_time = time_match.group(1)

        # --- Completion checks (run before the position checks) ---

        # Bus completed (with bracket) — time is explicit in the line
        m = bus_done_bracket.search(line)
        if m:
            parsed_data.append({
                'time': m.group(1),
                'type': 'done',
                'entity_id': m.group(2),
                'lat': None, 'lon': None, 'icon': ''
            })
            continue

        # Bus completed (no bracket) — use last seen sim time
        m = bus_done_nobracket.search(line)
        if m:
            parsed_data.append({
                'time': current_time,
                'type': 'done',
                'entity_id': m.group(1),
                'lat': None, 'lon': None, 'icon': ''
            })
            continue

        # Passenger arrived at destination — use last seen sim time
        m = passenger_done.search(line)
        if m:
            parsed_data.append({
                'time': current_time,
                'type': 'done',
                'entity_id': m.group(1),
                'lat': None, 'lon': None, 'icon': ''
            })
            continue

        # --- Position events (require a bracket time) ---
        if not time_match:
            continue

        time_str = time_match.group(1)

        # Check if the line is a passenger deployment
        passenger_match = passenger_pattern.search(line)
        if passenger_match:
            entity_id = passenger_match.group(1)
            lat = float(passenger_match.group(2))
            lon = float(passenger_match.group(3))

            parsed_data.append({
                'time': time_str,
                'type': 'passenger',
                'entity_id': entity_id,
                'lat': lat,
                'lon': lon,
                'icon': '🚶'
            })
            continue

        # Check if the line is a bus arriving at a stop
        bus_match = bus_pattern.search(line)
        if bus_match:
            entity_id = bus_match.group(1)
            stop_name = bus_match.group(2).strip()

            # Cross-reference the stop name with our GPS dictionary
            if stop_name in stops_dict:
                lat, lon = stops_dict[stop_name]
                parsed_data.append({
                    'time': time_str,
                    'type': 'bus',
                    'entity_id': entity_id,
                    'lat': lat,
                    'lon': lon,
                    'icon': '🚌'
                })

    return pd.DataFrame(parsed_data)


def get_simulation_state(df: pd.DataFrame, current_time: str) -> pd.DataFrame:
    """
    Filters the parsed simulation logs to return the exact location of
    every active entity at a specific minute in time.
    Entities whose latest event is 'done' are excluded (they've finished).
    """
    if df.empty:
        return df

    # Filter out any events that haven't happened yet
    past_events = df[df['time'] <= current_time]

    # Since logs are chronological, keeping the 'last' duplicate gives us the latest location
    latest_state = past_events.drop_duplicates(subset=['entity_id'], keep='last')

    # Remove entities whose most-recent event is a completion marker
    latest_state = latest_state[latest_state['type'] != 'done']

    return latest_state
