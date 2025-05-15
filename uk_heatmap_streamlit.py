import streamlit as st
import pandas as pd
import folium
from folium.plugins import HeatMap
from streamlit_folium import st_folium
import os

st.set_page_config(layout="wide")
st.title("UK Dentist Clinics & Customer Appointments Heatmaps")

# 1) Dentist clinics
dentist_file = "dentist_data_map.csv"
if os.path.exists(dentist_file):
    df_dent = pd.read_csv(dentist_file)
    df_dent = df_dent[["latitude", "longitude", "weekly_availability_hours"]].dropna()
else:
    df_dent = pd.DataFrame({
        "latitude": [51.5, 53.4, 52.5],
        "longitude": [-0.1, -2.3, -1.5],
        "weekly_availability_hours": [100, 150, 80],
    })

map_dent = folium.Map(location=[55.3781, -3.4360], zoom_start=6)
heat_dent = [
    [r.latitude, r.longitude, r.weekly_availability_hours]
    for r in df_dent.itertuples()
]
HeatMap(heat_dent, radius=15, max_zoom=13).add_to(map_dent)

# Customer appointments 
cust_file = "customers_with_latlon_cleaned.csv"
if os.path.exists(cust_file):
    df_cust = pd.read_csv(cust_file, low_memory=False)
else:
    st.error(f"Could not find `{cust_file}` in the project folder.")
    st.stop()

date_col = "assigned_date"

# parse it into datetime
df_cust[date_col] = pd.to_datetime(df_cust[date_col], errors="coerce")
df_cust = df_cust.dropna(subset=[date_col])

# for possible weekly grouping later
df_cust["week_start"] = df_cust[date_col].dt.to_period("W").apply(lambda r: r.start_time)

# Sidebar date selectors
st.sidebar.header("Customer Heatmap Date Range")
min_date = df_cust[date_col].dt.date.min()
max_date = df_cust[date_col].dt.date.max()
start_date = st.sidebar.date_input("Start date", value=min_date, min_value=min_date, max_value=max_date)
end_date   = st.sidebar.date_input("End date",   value=max_date, min_value=min_date, max_value=max_date)
if start_date > end_date:
    st.sidebar.error("Start date must be on or before end date")

# filter & group by lat/lon
mask = (
    (df_cust[date_col].dt.date >= start_date) &
    (df_cust[date_col].dt.date <= end_date)
)
df_filt = df_cust.loc[mask]
df_grp = (
    df_filt
    .groupby(["latitude", "longitude"], as_index=False)
    .size()
    .rename(columns={"size": "count"})
)

map_cust = folium.Map(location=[55.3781, -3.4360], zoom_start=6)
heat_cust = [
    [r.latitude, r.longitude, r.count]
    for r in df_grp.itertuples()
]
HeatMap(heat_cust, radius=15, max_zoom=13).add_to(map_cust)

tab1, tab2 = st.tabs(["Clinics Availability", "Customer Appointments"])

with tab1:
    st.header("Weekly Availability of Dentist Clinics")
    st_folium(map_dent, width="100%", height=600)

with tab2:
    st.header(f"Customer Appointments from {start_date} to {end_date}")
    st.markdown(f"**Total appointments:** {len(df_filt)}")
    st_folium(map_cust, width="100%", height=600)
