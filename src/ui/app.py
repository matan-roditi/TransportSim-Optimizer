import streamlit as st
import folium
from streamlit_folium import st_folium

def main():
    st.set_page_config(page_title="Herzliya Map", layout="wide")
    st.title("Herzliya Road Network")

    # Initialize the map centered on Herzliya center
    # Coordinates for Herzliya (approx 32.166, 34.843)
    m = folium.Map(location=[32.1663, 34.8433], zoom_start=14)

    # Display the map in the Streamlit app
    st_folium(m, width=1000, height=600)

if __name__ == "__main__":
    main()