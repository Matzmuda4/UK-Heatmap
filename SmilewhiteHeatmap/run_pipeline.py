import streamlit as st
import subprocess
import os
import pandas as pd
import json
from shapely.geometry import Point
import geopandas as gpd
from math import radians, cos, sin, asin, sqrt
from datetime import datetime, timedelta
import folium
from folium.plugins import HeatMap
from branca.colormap import LinearColormap
from streamlit_folium import folium_static
import visualize_regions
from process_customers import calculate_region_capacity

def haversine_distance(lon1, lat1, lon2, lat2):
    """Calculate the great circle distance between two points in kilometers."""
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def point_in_dynamic_area(point_lon, point_lat, area):
    """Check if a point falls within a dynamic area's radius."""
    distance = haversine_distance(
        point_lon, 
        point_lat, 
        area['center'][0], 
        area['center'][1]
    )
    return distance <= area['radius_km']

def get_active_clinic_count(input_file='dentist_data_map_random_hours.csv'):
    """Get the number of active clinics from the input file."""
    try:
        df = pd.read_csv(input_file)
        return len(df[df['active'] == 1])
    except Exception as e:
        st.error(f"Error reading clinic data: {e}")
        return 30  # Default fallback value

def load_dynamic_areas():
    """Load dynamic areas from JSON file."""
    try:
        with open('dynamic_areas.json', 'r') as f:
            return json.load(f)
    except Exception as e:
        st.error(f"Error loading dynamic areas: {str(e)}")
        return {"dynamic_areas": []}

def run_command(command):
    """Run a command and return its output."""
    try:
        process = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        return process.stdout, process.stderr
    except subprocess.CalledProcessError as e:
        return None, str(e)

def main():
    st.set_page_config(layout="wide", page_title="UK Dental Capacity Map")
    st.title("UK Dental Capacity Map")
    
    # Initialize session state
    if 'base_grid_size' not in st.session_state:
        st.session_state.base_grid_size = 20
    if 'dynamic_sizes' not in st.session_state:
        st.session_state.dynamic_sizes = {}
    if 'show_visualization' not in st.session_state:
        st.session_state.show_visualization = False
    
    # Get active clinic count
    total_active_clinics = get_active_clinic_count()
    
    # Load dynamic areas
    dynamic_areas_data = load_dynamic_areas()
    
    # Load customer data for date range
    try:
        customers_df = pd.read_csv('customers_with_latlon_cleaned.csv', low_memory=False)
        customers_df['assigned_date'] = pd.to_datetime(customers_df['assigned_date'])
        min_date = customers_df['assigned_date'].dt.date.min()
        max_date = customers_df['assigned_date'].dt.date.max()
    except Exception as e:
        st.error(f"Error loading customer data: {str(e)}")
        return
    
    # Sidebar for all controls
    with st.sidebar:
        # Initial Parameters (collapsible)
        with st.expander("Initial Parameters", expanded=True):
            n_clinics = st.slider(
                "Number of Clinics",
                min_value=10,
                max_value=total_active_clinics,
                value=min(50, total_active_clinics),
                step=10,
                help=f"Number of clinics to sample (max {total_active_clinics} active clinics)"
            )
            
            base_grid_size = st.slider(
                "Base Grid Size (km)",
                min_value=5,
                max_value=50,
                value=20,
                step=5,
                help="Base size of each clinic's service area grid"
            )
            
            merge_distance = st.slider(
                "Merge Distance (km)",
                min_value=0,
                max_value=20,
                value=5,
                step=1,
                help="Distance threshold for merging nearby grids"
            )
        
        # Date Selection (collapsible)
        with st.expander("Date Selection", expanded=True):
            start_date = st.date_input(
                "Start Date",
                min_date,
                min_value=min_date,
                max_value=max_date
            )
            
            max_end_date = min(max_date, start_date + timedelta(days=6))
            end_date = st.date_input(
                "End Date",
                max_end_date,
                min_value=start_date,
                max_value=max_end_date
            )
        
        # Dynamic Area Controls (collapsible)
        with st.expander("Dynamic Area Controls", expanded=True):
            for area in dynamic_areas_data['dynamic_areas']:
                area_name = area['name']
                if area_name not in st.session_state.dynamic_sizes:
                    st.session_state.dynamic_sizes[area_name] = base_grid_size
                
                st.session_state.dynamic_sizes[area_name] = st.slider(
                    f"{area_name} Grid Size (km)",
                    min_value=5,
                    max_value=50,
                    value=base_grid_size,
                    step=5,
                    help=f"Grid size for clinics in {area_name}"
                )
        
        # Generate button
        if st.button("Generate Visualization", use_container_width=True):
            # Save configuration
            config = {
                'base_grid_size': base_grid_size,
                'dynamic_sizes': st.session_state.dynamic_sizes,
                'dynamic_areas': dynamic_areas_data['dynamic_areas'],
                'merge_distance': merge_distance
            }
            with open('grid_config.json', 'w') as f:
                json.dump(config, f)
            
            # Run pipeline
            with st.spinner("Step 1: Preparing clinic data..."):
                stdout, stderr = run_command(f"python downsample_clinics.py --n_clinics {n_clinics}")
                if stderr:
                    st.error(f"Error in downsample_clinics.py: {stderr}")
                    return
            
            with st.spinner("Step 2: Generating and merging grids..."):
                stdout, stderr = run_command(f"python generate_grids.py --config grid_config.json")
                if stderr:
                    st.error(f"Error in generate_grids.py: {stderr}")
                    return
            
            with st.spinner("Step 3: Generating regions..."):
                stdout, stderr = run_command("python generate_regions.py")
                if stderr:
                    st.error(f"Error in generate_regions.py: {stderr}")
                    return
            
            st.session_state.show_visualization = True
            st.session_state.start_date = start_date
            st.session_state.end_date = end_date
    
    # Show visualization if generated
    if st.session_state.show_visualization:
        with st.spinner("Generating visualization..."):
            # Set dates in visualize_regions module
            visualize_regions.start_date = st.session_state.start_date
            visualize_regions.end_date = st.session_state.end_date
            
            # Load data using visualize_regions functions
            regions_gdf = visualize_regions.load_data()
            if regions_gdf is None:
                return
            
            # Calculate metrics using visualize_regions functions
            metrics_gdf, gaps_df = visualize_regions.calculate_metrics(
                regions_gdf,
                customers_df,
                st.session_state.start_date,
                st.session_state.end_date
            )
            
            # Create map
            m = folium.Map(location=[54.5, -2], zoom_start=6)
            
            # Add color scale
            color_scale = LinearColormap(
                colors=['green', 'yellow', 'red'],
                vmin=0,
                vmax=2,
                caption='Capacity Ratio (Customers/Hour)'
            )
            color_scale.add_to(m)
            
            # Add dynamic areas (squares)
            for area in dynamic_areas_data['dynamic_areas']:
                deg = visualize_regions.km_to_deg(area['radius_km'])
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
                popup_content = visualize_regions.create_popup_content(row)
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
            
            # Display full-width map
            folium_static(m, width=1200, height=600)  # Increased width for full-width display
            
            # Display legend below map
            st.write("### Map Legend")
            legend_cols = st.columns(4)
            
            with legend_cols[0]:
                st.write("Capacity Ratio Colors:")
                st.markdown("Green: Low utilization")
                st.markdown("Yellow: Moderate utilization")
                st.markdown("Red: High utilization")
                st.markdown("Gray: No availability")
            
            with legend_cols[1]:
                st.write("Dynamic Areas:")
                st.markdown("🟣 Purple Squares: Dynamic grid size areas")
            
            with legend_cols[2]:
                st.write("Service Gaps:")
                st.markdown("Blue: Low concentration")
                st.markdown("Green: Medium concentration")
                st.markdown("Red: High concentration")
            
            # Display statistics and tables
            st.write("### Summary Statistics")
            stat_cols = st.columns(4)
            
            with stat_cols[0]:
                st.metric("Total Regions", len(metrics_gdf))
            with stat_cols[1]:
                st.metric("Total Hours", f"{metrics_gdf['total_availability_hours'].sum():.1f}")
            with stat_cols[2]:
                st.metric("Total Customers", metrics_gdf['customer_count'].sum())
            with stat_cols[3]:
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