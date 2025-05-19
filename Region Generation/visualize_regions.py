import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from streamlit_folium import st_folium
import json
import branca.colormap as cm
import numpy as np

# Set page config
st.set_page_config(layout="wide", page_title="UK Dental Regions Map")

def load_data():
    """Load and prepare regions data."""
    try:
        # Load regions from both GeoJSON and CSV to ensure we have all fields
        regions_gdf = gpd.read_file('regions.geojson')
        regions_csv = pd.read_csv('regions.csv')
        
        # Merge the clinic_ids from CSV into the GeoDataFrame
        regions_gdf['clinic_ids'] = regions_csv['clinic_ids']
        
        return regions_gdf
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        st.stop()

def create_color_scale(max_hours):
    """Create a color scale for availability hours."""
    return cm.LinearColormap(
        colors=['#ff0000', '#ffff00', '#00ff00'],  # Red to Yellow to Green
        vmin=0,
        vmax=max_hours,
        caption='Weekly Availability Hours'
    )

def create_popup_content(region_data):
    """Create HTML content for region popup."""
    try:
        clinic_ids = json.loads(str(region_data['clinic_ids']))
        if not isinstance(clinic_ids, list):
            clinic_ids = [clinic_ids]
    except (json.JSONDecodeError, TypeError):
        clinic_ids = []
    
    return f"""
    <div style='min-width: 200px'>
        <h4>Region {region_data['region_id']}</h4>
        <b>Number of clinics:</b> {len(clinic_ids)}
        <br>
        <b>Clinic IDs:</b> {', '.join(map(str, clinic_ids))}
        <br>
        <b>Total availability:</b> {region_data['total_availability_hours']:.1f} h/week
        <br>
        <b>Hours per clinic:</b> {region_data['total_availability_hours']/len(clinic_ids):.1f} h/week
    </div>
    """

def main():
    st.title("UK Dental Regions Availability Map")
    
    # Load data
    regions_gdf = load_data()
    
    # Add number of clinics column
    regions_gdf['n_clinics'] = regions_gdf['clinic_ids'].apply(
        lambda x: len(json.loads(str(x))) if pd.notnull(x) else 0
    )
    
    # Calculate max hours for color scale
    max_hours = regions_gdf['total_availability_hours'].max()
    
    # Create map
    m = folium.Map(
        location=[54.5, -2],  # Center of UK
        zoom_start=6,
        width='100%',
        height='100%'
    )
    
    # Create color scale
    colormap = create_color_scale(max_hours)
    colormap.add_to(m)
    
    # Add regions to map
    for idx, row in regions_gdf.iterrows():
        # Calculate color based on total availability hours
        color = colormap(row['total_availability_hours'])
        
        # Create tooltip with basic info
        tooltip = f"Region {row['region_id']}: {row['n_clinics']} clinics, {row['total_availability_hours']:.1f} h/week"
        
        # Add region to map
        folium.GeoJson(
            row.geometry.__geo_interface__,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': 'black',
                'weight': 1,
                'fillOpacity': 0.7
            },
            tooltip=tooltip,
            popup=folium.Popup(create_popup_content(row), max_width=300)
        ).add_to(m)
    
    # Display map
    st_data = st_folium(m, width=1200, height=800)
    
    # Display summary statistics
    st.subheader("Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Regions", len(regions_gdf))
    with col2:
        st.metric("Total Weekly Hours", f"{regions_gdf['total_availability_hours'].sum():.1f}")
    with col3:
        st.metric("Total Clinics", regions_gdf['n_clinics'].sum())
    with col4:
        st.metric("Max Clinics per Region", regions_gdf['n_clinics'].max())
    
    # Display distribution of clinics per region
    st.subheader("Distribution of Clinics per Region")
    clinic_dist = regions_gdf['n_clinics'].value_counts().sort_index()
    st.bar_chart(clinic_dist)
    
    # Display detailed region data
    st.subheader("Region Details")
    display_df = regions_gdf[['region_id', 'clinic_ids', 'total_availability_hours', 'n_clinics']].copy()
    display_df = display_df.sort_values('region_id')
    st.dataframe(display_df)
    
    # Display distribution of availability hours
    st.subheader("Distribution of Weekly Availability Hours")
    hist_data = np.histogram(
        regions_gdf['total_availability_hours'],
        bins=20,
        range=(0, max_hours)
    )
    st.bar_chart(pd.DataFrame({
        'Hours': hist_data[0]
    }))

if __name__ == "__main__":
    main() 