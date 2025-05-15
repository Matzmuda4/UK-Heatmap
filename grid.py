import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import os

def main():
    # Page config & title
    st.set_page_config(layout="wide")
    st.title("UK Dentist Clinics & Customer Appointments Heatmaps")

    # Sidebar Settings
    st.sidebar.header("Settings")

    # Quadrant slider for dentist map
    quadrant_range_km = st.sidebar.slider(
        "Quadrant range around clinics (km)",
        10, 50, 30, 5
    )

    # Date range picker for customer map
    st.sidebar.markdown("---")
    st.sidebar.header("Customer Heatmap Date Range")
    cust_file = "customers_with_latlon_cleaned.csv"
    if os.path.exists(cust_file):
        df_cust = pd.read_csv(cust_file, low_memory=False)
        df_cust["assigned_date"] = pd.to_datetime(df_cust["assigned_date"], errors="coerce")

        min_date = df_cust["assigned_date"].dt.date.min()
        max_date = df_cust["assigned_date"].dt.date.max()
        start_date = st.sidebar.date_input("Start date", min_value=min_date, max_value=max_date, value=min_date)
        end_date   = st.sidebar.date_input("End date",   min_value=min_date, max_value=max_date, value=max_date)
        
        if start_date > end_date:
            st.sidebar.error("Start must be before end")
    else:
        st.sidebar.error(f"Missing {cust_file}")
        start_date = end_date = None

    # Build Dentist Map
    dentist_file = "dentist_data_map.csv"
    if os.path.exists(dentist_file):
        df_dent = pd.read_csv(dentist_file).dropna(subset=["latitude", "longitude", "weekly_availability_hours"])
    else:
        df_dent = pd.DataFrame({
            "latitude": [51.5, 53.4, 52.5],
            "longitude": [-0.1, -2.3, -1.5],
            "weekly_availability_hours": [100, 150, 80],
        })

    map_dent = folium.Map(location=[55.3781, -3.4360], zoom_start=6)
    # heat layer
    heat_dent = [[r.latitude, r.longitude, r.weekly_availability_hours]
                for r in df_dent.itertuples()]
    HeatMap(heat_dent, radius=15, max_zoom=13).add_to(map_dent)
    # quadrant rectangles
    lat_km = quadrant_range_km / 111.0
    lon_km = quadrant_range_km / 69.0
    for r in df_dent.itertuples():
        bounds = [
            [r.latitude - lat_km, r.longitude - lon_km],
            [r.latitude + lat_km, r.longitude + lon_km],
        ]
        folium.Rectangle(bounds=bounds,
                        color="blue", weight=1,
                        fill=False,
                        popup=f"Clinic: {r.latitude:.2f},{r.longitude:.2f}"
                        ).add_to(map_dent)

    # Build Customer Map
    map_cust = None
    total_appts = 0

    if os.path.exists(cust_file) and start_date and end_date:
        # filter by date
        mask = (
            (df_cust["assigned_date"].dt.date >= start_date) &
            (df_cust["assigned_date"].dt.date <= end_date)
        )
        df_filt = df_cust.loc[mask]
        total_appts = len(df_filt)
        
        # group by lat/lon
        df_grp = (df_filt
                .groupby(["latitude", "longitude"], as_index=False)
                .size()
                .rename(columns={"size": "count"}))
        
        map_cust = folium.Map(location=[55.3781, -3.4360], zoom_start=6)
        heat_cust = [[r.latitude, r.longitude, r.count] for r in df_grp.itertuples()]
        HeatMap(heat_cust, radius=15, max_zoom=13).add_to(map_cust)

    # Render Tabs
    tab1, tab2 = st.tabs(["Clinics Availability", "Customer Appointments"])

    with tab1:
        st.header("Weekly Availability of Dentist Clinics")
        st_folium(map_dent, width="100%", height=600)

    with tab2:
        st.header("Customer Appointments")
        if map_cust is None:
            st.error("No customer map—check your CSV & date range")
        else:
            st.subheader(f"{start_date} → {end_date}  |  Total: {total_appts}")
            st_folium(map_cust, width="100%", height=600)

if __name__ == '__main__':
    main()