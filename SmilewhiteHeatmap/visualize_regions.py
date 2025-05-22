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
from shapely.geometry import Point

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
        
        # Load customer data
        customers_df = pd.read_csv('customers_with_latlon_cleaned.csv', low_memory=False)
        customers_df['assigned_date'] = pd.to_datetime(customers_df['assigned_date'])
        
        return regions_gdf, customers_df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None, None

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
    
    # Determine status based on capacity ratio
    def get_status(ratio):
        if ratio == 0:
            return "No customers"
        elif ratio < 0.5:
            return "Under capacity"
        elif ratio < 1:
            return "Optimal capacity"
        else:
            return "Over capacity"
    
    metrics_gdf['status'] = metrics_gdf['capacity_ratio'].apply(get_status)
    
    # Find service gaps
    gaps_df = find_service_gaps(customers_df, regions_gdf, start_date, end_date)
    
    return metrics_gdf, gaps_df

def main():
    st.set_page_config(layout="wide", page_title="UK Dental Capacity Map")
    st.title("UK Dental Capacity Map")
    
    # Initialize session state for date selection
    if 'date_selected' not in st.session_state:
        st.session_state.date_selected = False
    
    # Load data for date range selection
    try:
        customers_df = pd.read_csv('customers_with_latlon_cleaned.csv', low_memory=False)
        customers_df['assigned_date'] = pd.to_datetime(customers_df['assigned_date'])
        min_date = customers_df['assigned_date'].dt.date.min()
        max_date = customers_df['assigned_date'].dt.date.max()
    except Exception:
        st.error("Error loading customer data. Please check if the file exists.")
        return
    
    # Date range selection in sidebar
    st.sidebar.header("Date Selection")
    
    # Date input fields
    start_date = st.sidebar.date_input(
        "Start Date",
        min_date,
        min_value=min_date,
        max_value=max_date
    )
    
    # Ensure end_date is at most 7 days after start_date
    max_end_date = min(max_date, start_date + timedelta(days=6))
    end_date = st.sidebar.date_input(
        "End Date",
        max_end_date,
        min_value=start_date,
        max_value=max_end_date
    )
    
    # Add a button to trigger visualization
    if st.sidebar.button("Generate Visualization"):
        st.session_state.date_selected = True
        st.session_state.start_date = start_date
        st.session_state.end_date = end_date
    
    # Show instructions if dates haven't been selected
    if not st.session_state.date_selected:
        st.info("Please select a date range (maximum 7 days) in the sidebar and click 'Generate Visualization' to view the map.")
        return
    
    # Show loading message
    with st.spinner("Calculating metrics and generating visualization..."):
        # Load data
        regions_gdf, customers_df = load_data()
        if regions_gdf is None or customers_df is None:
            return
        
        # Calculate metrics for the selected date range
        metrics_gdf, gaps_df = calculate_metrics(
            regions_gdf,
            customers_df,
            st.session_state.start_date,
            st.session_state.end_date
        )
        
        # Create map
        m = folium.Map(location=[54.5, -2], zoom_start=6)
        
        # Add regions with color based on capacity ratio
        color_scale = create_color_scale()
        color_scale.add_to(m)
        
        for idx, row in metrics_gdf.iterrows():
            # Create popup content
            popup_content = create_popup_content(row)
            
            # Determine fill color based on capacity ratio
            fill_color = color_scale(row['capacity_ratio']) if row['capacity_ratio'] != float('inf') else 'gray'
            
            # Add region to map with both popup and tooltip
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
        
        # Add gap points as a heatmap
        if not gaps_df.empty:
            gap_points = gaps_df[['latitude', 'longitude']].values.tolist()
            HeatMap(
                gap_points,
                radius=15,
                blur=10,
                max_zoom=1,
                gradient={0.4: 'blue', 0.65: 'lime', 1: 'red'}
            ).add_to(m)
        
        # Create two columns for the map and legend
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Display map
            folium_static(m, width=800)
        
        with col2:
            # Display color scale legend
            st.write("### Map Legend")
            st.write("Capacity Ratio Colors:")
            st.markdown("Green: Low utilization")
            st.markdown("Yellow: Moderate utilization")
            st.markdown("Red: High utilization")
            st.markdown("Gray: No availability")
            st.write("---")
            st.write("Heatmap (Blue-Green-Red):")
            st.markdown("Shows concentration of service gaps")
        
        # Display summary statistics
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
        
        # Select columns to display
        columns_to_display = ['region_id', 'total_availability_hours', 'customer_count', 
                            'capacity_ratio', 'status', 'clinic_count']
        display_df = metrics_gdf[columns_to_display].copy()
        
        # Sort by capacity ratio
        display_df = display_df.sort_values('capacity_ratio', ascending=False)
        
        # Format numeric columns
        display_df['total_availability_hours'] = display_df['total_availability_hours'].round(1)
        display_df['capacity_ratio'] = display_df['capacity_ratio'].round(2)
        
        st.dataframe(display_df)
        
        # Display gaps information
        if not gaps_df.empty:
            st.write("### Service Gaps")
            st.write("Areas not serviced by any clinic:")
            
            if 'postal_code' in gaps_df.columns:
                st.write("#### Gaps by Postal Code")
                gaps_by_postcode = gaps_df.groupby('postal_code').size().reset_index(name='count')
                gaps_by_postcode = gaps_by_postcode.sort_values('count', ascending=False)
                st.dataframe(gaps_by_postcode)
            
            st.write("#### Detailed Gap Locations")
            st.dataframe(gaps_df[['latitude', 'longitude', 'assigned_date'] + 
                               (['postal_code'] if 'postal_code' in gaps_df.columns else [])])
        
        # Display overcrowded regions
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