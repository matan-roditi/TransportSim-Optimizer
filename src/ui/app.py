import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import psycopg2
import os
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


def main():
    st.set_page_config(page_title="Herzliya Map", layout="wide")
    st.title("Herzliya Road Network")

    # Initialize the map centered on Herzliya center
    # Coordinates for Herzliya (approx 32.166, 34.825)
    m = folium.Map(location=[32.1663, 34.825], zoom_start=14)

    # Fetch data
    df = get_bus_stops()

    # Add yellow pinpoints (CircleMarkers) for each stop
    for _, stop in df.iterrows():
        folium.CircleMarker(
            location=[stop['lat'], stop['lon']],
            radius=7,
            popup=stop['name'],
            tooltip=stop['name'],
            color="black",        # Outline
            weight=1,
            fill=True,
            fill_color="yellow",  # yellow pinpoint
            fill_opacity=0.9
        ).add_to(m)

    # Display the map in the Streamlit app
    st_folium(m, width=1000, height=600)

if __name__ == "__main__":
    main()