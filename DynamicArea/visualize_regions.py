import streamlit as st
import pandas as pd
import geopandas as gpd
import folium
from branca.colormap import LinearColormap
import json
from streamlit_folium import folium_static
from area_config import CITY_BOUNDARIES, GRID_SIZES, CITY_TYPES

def load_data():
    """Load and prepare all necessary data."""
    try:
        # Load base regions
        regions_gdf = gpd.read_file('regions.geojson')
        regions_df = pd.read_csv('regions.csv')
        
        # Ensure clinic_ids are properly loaded from CSV
        regions_gdf['clinic_ids'] = regions_df['clinic_ids']
        
        # Add clinic count
        regions_gdf['clinic_count'] = regions_gdf['clinic_ids'].apply(
            lambda x: len(json.loads(x)) if isinstance(x, str) else 1
        )
        
        # Load grid data
        grids_gdf = gpd.read_file('clinic_grids.geojson')
        
        # Determine area type for regions based on their centroid
        def get_area_type(geometry):
            centroid = geometry.centroid
            for city, bounds in CITY_BOUNDARIES.items():
                min_lon, min_lat, max_lon, max_lat = bounds
                if min_lon <= centroid.x <= max_lon and min_lat <= centroid.y <= max_lat:
                    return CITY_TYPES[city]
            return 'rural'
        
        # Add area_type to regions based on their centroid location
        regions_gdf['area_type'] = regions_gdf.geometry.apply(get_area_type)
        
        return regions_gdf, grids_gdf
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

def create_area_type_colors():
    """Create color mapping for different area types."""
    return {
        'metropolitan': '#FF0000',  # Red
        'urban': '#FFA500',        # Orange
        'suburban': '#FFFF00',     # Yellow
        'rural': '#90EE90'         # Light green
    }

def create_popup_content(region_data):
    """Create HTML content for region popups."""
    clinic_ids = json.loads(region_data['clinic_ids']) if isinstance(region_data['clinic_ids'], str) else []
    return f"""
        <div style="font-family: Arial, sans-serif; min-width: 200px;">
            <h4 style="margin: 0 0 10px 0;">Region {region_data['region_id']}</h4>
            <p style="margin: 5px 0;"><b>Number of Clinics:</b> {len(clinic_ids)}</p>
            <p style="margin: 5px 0;"><b>Weekly Hours:</b> {region_data['total_availability_hours']:.1f}</p>
            <p style="margin: 5px 0;"><b>Area Type:</b> {region_data['area_type']}</p>
        </div>
    """

def add_city_boundaries(m):
    """Add city boundary rectangles to the map."""
    for city, bounds in CITY_BOUNDARIES.items():
        min_lon, min_lat, max_lon, max_lat = bounds
        area_type = CITY_TYPES[city]
        color = create_area_type_colors()[area_type]
        
        folium.Rectangle(
            bounds=[[min_lat, min_lon], [max_lat, max_lon]],
            color=color,
            weight=2,
            fill=True,
            fillColor=color,
            fillOpacity=0.1,
            popup=f"{city} ({area_type})"
        ).add_to(m)

def main():
    st.set_page_config(layout="wide", page_title="UK Dental Regions Map")
    st.title("UK Dental Regions Map")
    
    # Create a placeholder for the map
    status_placeholder = st.empty()
    
    # Load data
    regions_gdf, grids_gdf = load_data()
    if regions_gdf is None or grids_gdf is None:
        return
    
    # Sidebar controls
    st.sidebar.header("Display Settings")
    
    # Show area boundaries toggle
    show_areas = st.sidebar.checkbox("Show Area Boundaries", value=True)
    
    # Show grids toggle
    show_grids = st.sidebar.checkbox("Show Grid Squares", value=True)
    
    # Create map
    m = folium.Map(location=[54.5, -2], zoom_start=6)
    
    # Add city boundaries if enabled
    if show_areas:
        add_city_boundaries(m)
    
    # Add grid squares if enabled
    if show_grids and 'area_type' in grids_gdf.columns:
        area_colors = create_area_type_colors()
        for idx, row in grids_gdf.iterrows():
            area_type = row['area_type']
            color = area_colors.get(area_type, '#808080')  # Default to gray if area_type not found
            
            folium.GeoJson(
                row.geometry,
                style_function=lambda x, color=color: {
                    'fillColor': color,
                    'color': 'black',
                    'weight': 1,
                    'fillOpacity': 0.3
                },
                tooltip=f"Grid - {area_type}"
            ).add_to(m)
    
    # Add regions
    area_colors = create_area_type_colors()
    for idx, row in regions_gdf.iterrows():
        # Create popup content
        popup_content = create_popup_content(row)
        
        # Get color based on area type
        color = area_colors.get(row['area_type'], '#3388ff')  # Default to blue if no area type
        
        # Add region to map with both popup and tooltip
        folium.GeoJson(
            row.geometry,
            style_function=lambda x, color=color: {
                'fillColor': color,
                'color': 'black',
                'weight': 2,
                'fillOpacity': 0.4
            },
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"Region {row['region_id']} - {row['area_type']}"
        ).add_to(m)
    
    # Create two columns for the map and legend
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Display map
        folium_static(m, width=800)
    
    with col2:
        # Display legends
        st.write("### Map Legend")
        
        # Area type legend
        st.write("Area Types:")
        area_colors = create_area_type_colors()
        for area_type, color in area_colors.items():
            st.markdown(
                f'<div style="background-color: {color}; padding: 5px; margin: 2px; border-radius: 3px;">'
                f'{area_type.title()}</div>',
                unsafe_allow_html=True
            )
        
        st.write("---")
        
        # Grid size legend
        st.write("Grid Sizes:")
        for area_type, size in GRID_SIZES.items():
            st.markdown(f"**{area_type.title()}**: {size}km")
    
    # Display summary statistics
    st.write("### Summary Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Regions", len(regions_gdf))
    with col2:
        st.metric("Total Hours", f"{regions_gdf['total_availability_hours'].sum():.1f}")
    with col3:
        total_clinics = regions_gdf['clinic_count'].sum()
        st.metric("Total Clinics", total_clinics)
    
    # Display region data table
    st.write("### Region Details")
    
    # Select columns to display (only if they exist in the DataFrame)
    available_columns = ['region_id', 'total_availability_hours', 'clinic_count', 'area_type']
    columns_to_display = [col for col in available_columns if col in regions_gdf.columns]
    display_df = regions_gdf[columns_to_display].copy()
    
    # Sort by region_id
    display_df = display_df.sort_values('region_id')
    
    # Format numeric columns
    if 'total_availability_hours' in display_df.columns:
        display_df['total_availability_hours'] = display_df['total_availability_hours'].round(1)
    
    st.dataframe(display_df)
    
    # Display statistics by area type
    if 'area_type' in display_df.columns:
        st.write("### Statistics by Area Type")
        area_stats = display_df.groupby('area_type').agg({
            'region_id': 'count',
            'total_availability_hours': 'sum',
            'clinic_count': 'sum'
        }).round(1)
        area_stats.columns = ['Number of Regions', 'Total Hours', 'Total Clinics']
        st.dataframe(area_stats)

if __name__ == "__main__":
    main() 