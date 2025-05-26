import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from folium.plugins import HeatMap
from branca.colormap import LinearColormap
import json
from datetime import datetime, timedelta
import numpy as np
from process_customers import calculate_region_capacity
from streamlit_folium import folium_static
from shapely.geometry import Point, Polygon, box
from math import radians, cos, sin, asin, sqrt
import os
import sys

def km_to_deg(km):
    """
    Convert kilometers to approximate degrees.
    This is a rough approximation and varies with latitude.
    At UK latitudes (around 54°N), 1 degree is approximately:
    - Latitude: 111 km
    - Longitude: 111 * cos(54°) ≈ 65 km
    """
    return {
        'lat': km / 111.0,  # degrees latitude per km
        'lon': km / (111.0 * np.cos(np.radians(54)))  # degrees longitude per km at UK latitude
    }

def load_data():
    """Load and prepare all necessary data."""
    try:
        # Load base regions (without metrics)
        regions_gdf = gpd.read_file('regions.geojson')
        regions_df = pd.read_csv('regions.csv')
        
        # Ensure clinic_ids are properly loaded from CSV
        regions_gdf['clinic_ids'] = regions_df['clinic_ids']
        
        # Add clinic count
        regions_gdf['clinic_count'] = regions_gdf['clinic_ids'].apply(
            lambda x: len(json.loads(x)) if isinstance(x, str) else 1
        )
        
        return regions_gdf
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def load_customers():
    """Load customer data separately for better performance."""
    try:
        customers_df = pd.read_csv('customers_with_latlon_cleaned.csv', low_memory=False)
        customers_df['assigned_date'] = pd.to_datetime(customers_df['assigned_date'])
        return customers_df
    except Exception as e:
        st.error(f"Error loading customer data: {str(e)}")
        return None

def create_color_scale():
    """Create a color scale for capacity ratios."""
    return LinearColormap(
        colors=['green', 'yellow', 'red'],
        vmin=0,
        vmax=2,
        caption='Capacity Ratio (Customers/Hour)'
    )

def create_popup_content(region_data):
    """Create HTML content for region popups."""
    return f"""
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
            <h4 style="margin: 0 0 10px 0;">Region {region_data['region_id']}</h4>
            <p style="margin: 5px 0;"><b>Status:</b> {region_data['status']}</p>
            <p style="margin: 5px 0;"><b>Weekly Hours:</b> {region_data['total_availability_hours']:.1f}</p>
            <p style="margin: 5px 0;"><b>Current Customers:</b> {region_data['customer_count']}</p>
            <p style="margin: 5px 0;"><b>Capacity Ratio:</b> {region_data['capacity_ratio']:.2f}</p>
            <p style="margin: 5px 0;"><b>Number of Clinics:</b> {region_data['clinic_count']}</p>
        </div>
    """

def find_service_gaps(customers_df, regions_gdf, start_date, end_date):
    """Find customers not served by any region."""
    # Filter customers for the selected date range
    mask = (customers_df['assigned_date'].dt.date >= start_date) & (customers_df['assigned_date'].dt.date <= end_date)
    period_customers = customers_df[mask].copy()
    
    # Create points for each customer
    customer_points = [Point(row['longitude'], row['latitude']) for _, row in period_customers.iterrows()]
    
    # Check each customer against all regions
    gaps = []
    for i, (point, row) in enumerate(zip(customer_points, period_customers.iterrows())):
        is_in_region = False
        for _, region in regions_gdf.iterrows():
            if region.geometry.contains(point):
                is_in_region = True
                break
        if not is_in_region:
            gaps.append(row[1])  # row[1] contains the actual data
    
    if gaps:
        return pd.DataFrame(gaps)
    return pd.DataFrame()

def calculate_metrics(regions_gdf, customers_df, start_date, end_date):
    """Calculate metrics for regions including customer counts and capacity ratios."""
    # Filter customers for the selected date range and group by customer ID
    mask = (customers_df['assigned_date'].dt.date >= start_date) & (customers_df['assigned_date'].dt.date <= end_date)
    period_customers = customers_df[mask].copy()
    
    # Group by customer ID to avoid counting the same customer multiple times
    period_customers = period_customers.drop_duplicates(subset=['customer_id'])
    
    # Create a copy of regions_gdf for metrics
    metrics_gdf = regions_gdf.copy()
    
    # Initialize customer counts
    metrics_gdf['customer_count'] = 0
    
    # Count unique customers per region
    for idx, region in metrics_gdf.iterrows():
        region_poly = region.geometry
        region_customers = period_customers[period_customers.apply(
            lambda row: region_poly.contains(Point(row['longitude'], row['latitude'])), axis=1
        )]
        metrics_gdf.at[idx, 'customer_count'] = len(region_customers)
    
    # Calculate capacity ratio (customers per hour)
    metrics_gdf['capacity_ratio'] = metrics_gdf['customer_count'] / metrics_gdf['total_availability_hours']
    metrics_gdf['capacity_ratio'] = metrics_gdf['capacity_ratio'].fillna(0)
    
    # Determine status based on capacity ratio with new thresholds
    def get_status(ratio):
        if ratio == 0:
            return "Empty"
        elif ratio < 0.25:
            return "Partially Empty"
        elif ratio <= 0.5:
            return "moderately Full"
        elif ratio <= 0.75:
            return "Partially Full"
        elif ratio <= 0.85:
            return "Nearly Full"
        elif ratio <= 1:
            return "At Capacity"
        else:
            return "Overcrowded"
    
    metrics_gdf['status'] = metrics_gdf['capacity_ratio'].apply(get_status)
    
    # Find service gaps
    gaps_df = find_service_gaps(customers_df, regions_gdf, start_date, end_date)
    
    return metrics_gdf, gaps_df

def haversine_distance(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance between two points in kilometers."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def load_dynamic_areas():
    """Load dynamic areas from JSON file."""
    try:
        with open('dynamic_areas.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading dynamic areas: {str(e)}")
        return {"dynamic_areas": []}

def point_in_dynamic_area(point_lon, point_lat, area):
    """Check if a point falls within a dynamic area's square."""
    # Convert radius to degrees for the square
    deg = km_to_deg(area['radius_km'])
    
    # Calculate square boundaries
    min_lon = area['center'][0] - deg['lon']
    max_lon = area['center'][0] + deg['lon']
    min_lat = area['center'][1] - deg['lat']
    max_lat = area['center'][1] + deg['lat']
    
    # Check if point is within square
    return (min_lon <= point_lon <= max_lon) and (min_lat <= point_lat <= max_lat)

def main():
    st.set_page_config(layout="wide", page_title="UK Dental Capacity Map")
    st.title("UK Dental Capacity Map")
    
    # Parse command line arguments for dates
    start_date = None
    end_date = None
    
    for i in range(len(sys.argv)):
        if sys.argv[i] == '--start_date':
            start_date = datetime.strptime(sys.argv[i+1], '%Y-%m-%d').date()
        elif sys.argv[i] == '--end_date':
            end_date = datetime.strptime(sys.argv[i+1], '%Y-%m-%d').date()
    
    if start_date is None or end_date is None:
        st.error("Please provide start and end dates via command line arguments.")
        return
    
    # Show loading message
    with st.spinner("Generating visualization..."):
        # Load data
        regions_gdf = load_data()
        if regions_gdf is None:
            return
        
        # Load customer data
        customers_df = load_customers()
        if customers_df is None:
            return
        
        # Calculate metrics
        metrics_gdf, gaps_df = calculate_metrics(
            regions_gdf,
            customers_df,
            start_date,
            end_date
        )
        
        # Create map
        m = folium.Map(location=[54.5, -2], zoom_start=6)
        
        # Add color scale
        color_scale = create_color_scale()
        color_scale.add_to(m)
        
        # Load and add dynamic areas (squares)
        dynamic_areas_data = load_dynamic_areas()
        for area in dynamic_areas_data['dynamic_areas']:
            deg = km_to_deg(area['radius_km'])
            bounds = [
                [area['center'][1] - deg['lat'], area['center'][0] - deg['lon']],
                [area['center'][1] - deg['lat'], area['center'][0] + deg['lon']],
                [area['center'][1] + deg['lat'], area['center'][0] + deg['lon']],
                [area['center'][1] + deg['lat'], area['center'][0] - deg['lon']]
            ]
            
            folium.Polygon(
                locations=bounds,
                color='purple',
                weight=2,
                fill=True,
                fillColor='purple',
                fillOpacity=0.1,
                popup=None
            ).add_to(m)
        
        # Add regions
        for idx, row in metrics_gdf.iterrows():
            popup_content = create_popup_content(row)
            fill_color = color_scale(row['capacity_ratio']) if row['capacity_ratio'] != float('inf') else 'gray'
            
            folium.GeoJson(
                row.geometry,
                style_function=lambda x, color=fill_color: {
                    'fillColor': color,
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.7
                },
                popup=folium.Popup(popup_content, max_width=300),
                tooltip=f"Region {row['region_id']} - {row['status']}"
            ).add_to(m)
        
        # Add gaps heatmap
        if not gaps_df.empty:
            gap_points = gaps_df[['latitude', 'longitude']].values.tolist()
            HeatMap(
                gap_points,
                radius=15,
                blur=10,
                max_zoom=1,
                gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}
            ).add_to(m)
        
        # Display map and legend
        col1, col2 = st.columns([3, 1])
        with col1:
            folium_static(m, width=800)
        
        with col2:
            st.write("### Map Legend")
            st.write("Capacity Ratio Colors:")
            st.markdown("Green: Low utilization")
            st.markdown("Yellow: Moderate utilization")
            st.markdown("Red: High utilization")
            st.markdown("Gray: No availability")
            st.write("---")
            st.write("Purple Squares:")
            st.markdown("Dynamic grid size areas")
            st.write("---")
            st.write("Heatmap (Blue-Green-Red):")
            st.markdown("Shows concentration of service gaps")
        
        # Display statistics and tables
        st.write("### Summary Statistics")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Regions", len(metrics_gdf))
        with col2:
            st.metric("Total Hours", f"{metrics_gdf['total_availability_hours'].sum():.1f}")
        with col3:
            st.metric("Total Customers", metrics_gdf['customer_count'].sum())
        with col4:
            st.metric("Service Gaps", len(gaps_df))
        
        # Display region data table
        st.write("### Region Capacity Details")
        columns_to_display = ['region_id', 'total_availability_hours', 'customer_count', 
                            'capacity_ratio', 'status', 'clinic_count']
        display_df = metrics_gdf[columns_to_display].copy()
        display_df = display_df.sort_values('capacity_ratio', ascending=False)
        display_df['total_availability_hours'] = display_df['total_availability_hours'].round(1)
        display_df['capacity_ratio'] = display_df['capacity_ratio'].round(2)
        st.dataframe(display_df)
        
        # Display gaps and overcrowded regions
        if not gaps_df.empty:
            st.write("### Service Gaps")
            st.write("Areas not serviced by any clinic:")
            st.dataframe(gaps_df[['latitude', 'longitude', 'assigned_date']])
        
        overcrowded = metrics_gdf[metrics_gdf['capacity_ratio'] > 1]
        if not overcrowded.empty:
            st.write("### Overcrowded Regions")
            st.write("Regions with more customers than available hours:")
            overcrowded_display = overcrowded[columns_to_display].copy()
            overcrowded_display['total_availability_hours'] = overcrowded_display['total_availability_hours'].round(1)
            overcrowded_display['capacity_ratio'] = overcrowded_display['capacity_ratio'].round(2)
            st.dataframe(overcrowded_display)

if __name__ == "__main__":
    main() 