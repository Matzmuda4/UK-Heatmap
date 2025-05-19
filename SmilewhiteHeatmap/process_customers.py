import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
from datetime import datetime, timedelta
import json

def load_data():
    """Load and prepare all necessary data."""
    # Load regions data
    regions_gdf = gpd.read_file('regions.geojson')
    
    # Convert clinic_ids to string if it exists
    if 'clinic_ids' in regions_gdf.columns:
        regions_gdf['clinic_ids'] = regions_gdf['clinic_ids'].astype(str)
    else:
        # If clinic_ids doesn't exist, create it as an empty list
        regions_gdf['clinic_ids'] = '[]'
    
    # Load customer data
    customers_df = pd.read_csv('customers_with_latlon_cleaned.csv', low_memory=False)
    customers_df['assigned_date'] = pd.to_datetime(customers_df['assigned_date'])
    
    return regions_gdf, customers_df

def find_gaps(customers_gdf, regions_gdf):
    """Find customers that don't fall within any region."""
    gaps = []
    for idx, customer in customers_gdf.iterrows():
        customer_point = Point(customer['longitude'], customer['latitude'])
        if not any(region.contains(customer_point) for region in regions_gdf.geometry):
            # Create gap record with available fields
            gap_record = {
                'latitude': customer['latitude'],
                'longitude': customer['longitude'],
                'assigned_date': customer['assigned_date']
            }
            # Add postcode if it exists
            if 'postal_code' in customer:
                gap_record['postal_code'] = customer['postal_code']
            gaps.append(gap_record)
    return pd.DataFrame(gaps)

def calculate_region_capacity(regions_gdf, customers_gdf, start_date, end_date):
    """Calculate capacity ratios for each region in the given time period."""
    # Ensure the date range is within a week
    date_diff = (end_date - start_date).days
    if date_diff > 7:
        end_date = start_date + timedelta(days=6)
    
    # Filter customers by date range
    mask = (customers_gdf['assigned_date'] >= start_date) & (customers_gdf['assigned_date'] <= end_date)
    period_customers = customers_gdf[mask]
    
    # Convert customers to GeoDataFrame
    customers_gdf = gpd.GeoDataFrame(
        period_customers,
        geometry=[Point(xy) for xy in zip(period_customers['longitude'], period_customers['latitude'])],
        crs="EPSG:4326"
    )
    
    # Find gaps (customers not in any region)
    gaps = []
    for idx, customer in customers_gdf.iterrows():
        customer_point = Point(customer['longitude'], customer['latitude'])
        if not any(region.contains(customer_point) for region in regions_gdf.geometry):
            gap_record = {
                'latitude': customer['latitude'],
                'longitude': customer['longitude'],
                'assigned_date': customer['assigned_date']
            }
            if 'postal_code' in customer:
                gap_record['postal_code'] = customer['postal_code']
            gaps.append(gap_record)
    gaps_df = pd.DataFrame(gaps)
    
    # Start with a copy of the regions GeoDataFrame to preserve all original data
    metrics_gdf = regions_gdf.copy()
    
    # Calculate additional metrics for each region
    for idx, region in metrics_gdf.iterrows():
        # Find customers in this region for the selected period
        region_customers = customers_gdf[customers_gdf.geometry.within(region.geometry)]
        customer_count = len(region_customers)
        
        # Get the weekly hours from the region data (already exists in the GeoDataFrame)
        try:
            weekly_hours = float(region['total_availability_hours'])
        except (ValueError, TypeError):
            weekly_hours = 0.0
            print(f"Warning: Invalid total_availability_hours for region {region['region_id']}")
        
        # Calculate days in the selected period
        days_in_period = min((end_date - start_date).days + 1, 7)
        period_hours = (weekly_hours / 7) * days_in_period
        
        # Calculate capacity ratio
        capacity_ratio = customer_count / period_hours if period_hours > 0 else float('inf')
        
        # Determine status
        if capacity_ratio == float('inf'):
            status = "No Availability"
        elif capacity_ratio == 0:
            status = "Empty"
        elif capacity_ratio <= 0.25:
            status = "Low Utilization"
        elif capacity_ratio <= 0.5:
            status = "Partially Full"
        elif capacity_ratio <= 0.75:
            status = "Moderately Full"
        elif capacity_ratio <= 0.9:
            status = "Near Capacity"
        elif capacity_ratio <= 1.0:
            status = "At Capacity"
        else:
            status = "Overcrowded"
        
        # Update the metrics in the GeoDataFrame
        metrics_gdf.at[idx, 'customer_count'] = customer_count
        metrics_gdf.at[idx, 'capacity_ratio'] = capacity_ratio
        metrics_gdf.at[idx, 'status'] = status
    
    return metrics_gdf, gaps_df

def main():
    # Load data
    regions_gdf, customers_df = load_data()
    
    # Get date range from data
    min_date = customers_df['assigned_date'].min()
    max_date = customers_df['assigned_date'].max()
    
    # Calculate metrics for the entire period
    metrics_gdf, gaps_df = calculate_region_capacity(
        regions_gdf,
        customers_df,
        min_date,
        max_date
    )
    
    # Save results
    metrics_gdf.to_file('region_metrics.geojson', driver='GeoJSON')
    gaps_df.to_csv('service_gaps.csv', index=False)
    
    # Print summary
    print(f"Processed {len(metrics_gdf)} regions")
    print(f"Found {len(gaps_df)} service gaps")
    print(f"Date range: {min_date.date()} to {max_date.date()}")
    print(f"Total weekly hours: {metrics_gdf['total_availability_hours'].sum():.1f}")

if __name__ == "__main__":
    main() 