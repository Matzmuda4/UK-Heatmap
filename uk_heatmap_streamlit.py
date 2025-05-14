import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import os

# Load and aggregate data from the new dataset
dentist_file_path = 'dentist_data_map.csv'
if os.path.exists(dentist_file_path):
    df = pd.read_csv(dentist_file_path)
    # Use the correct column names: latitude, longitude, weekly_availability_hours
    aggregated_data = df[['latitude', 'longitude', 'weekly_availability_hours']].copy()
    # Drop rows with NaN values in any of the columns
    aggregated_data = aggregated_data.dropna()
else:
    # Dummy data with matching column names
    aggregated_data = pd.DataFrame({
        'latitude': [51.5, 53.4, 52.5],
        'longitude': [-0.1, -2.3, -1.5],
        'weekly_availability_hours': [100, 150, 80]
    })

# Streamlit app title
st.title("UK Dentist Clinics Heatmap")

# Create Folium map with heatmap based on weekly_availability_hours
m = folium.Map(location=[55.3781, -3.4360], zoom_start=6)
heat_data = [[row['latitude'], row['longitude'], row['weekly_availability_hours']] for _, row in aggregated_data.iterrows()]
HeatMap(heat_data, radius=15, max_zoom=13).add_to(m)

# Display the map using st_folium
st_folium(m, width='100%', height=600)