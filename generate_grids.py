import pandas as pd
import geopandas as gpd
from shapely.geometry import box, Point
import numpy as np
from math import sqrt

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

def create_square_grid(lat, lon, radius_km):
    """
    Create a square grid centered at the given lat/lon with sides of 2*radius_km.
    
    Args:
        lat (float): Latitude of the center point
        lon (float): Longitude of the center point
        radius_km (float): Half the length of the square side in kilometers
        
    Returns:
        shapely.geometry.Polygon: Square grid as a polygon
    """
    # Convert radius from km to degrees
    deg = km_to_deg(radius_km)
    
    # Calculate the bounding box coordinates
    minx = lon - deg['lon']
    maxx = lon + deg['lon']
    miny = lat - deg['lat']
    maxy = lat + deg['lat']
    
    # Create a square polygon
    return box(minx, miny, maxx, maxy)

def main():
    # Read the sample clinics data
    clinics_df = pd.read_csv('sample_clinics.csv')
    
    # Create a GeoDataFrame with clinic points
    geometry = [Point(xy) for xy in zip(clinics_df['longitude'], clinics_df['latitude'])]
    clinics_gdf = gpd.GeoDataFrame(clinics_df, geometry=geometry, crs="EPSG:4326")
    
    # Create grids for each clinic
    grids = []
    for idx, row in clinics_gdf.iterrows():
        grid = create_square_grid(
            lat=row['latitude'],
            lon=row['longitude'],
            radius_km=20  # 20km radius as requested
        )
        
        grid_data = {
            'clinic_id': row['id'],
            'weekly_hours': row['weekly_availability_hours'],
            'geometry': grid
        }
        grids.append(grid_data)
    
    # Create a GeoDataFrame of all grids
    grids_gdf = gpd.GeoDataFrame(grids, crs="EPSG:4326")
    
    # Save the grids to GeoJSON and CSV for visualization and further processing
    grids_gdf.to_file('clinic_grids.geojson', driver='GeoJSON')
    
    # Save a CSV version without the geometry for easier processing
    grids_df = pd.DataFrame({
        'clinic_id': grids_gdf['clinic_id'],
        'weekly_hours': grids_gdf['weekly_hours']
    })
    grids_df.to_csv('clinic_grids.csv', index=False)
    
    # Print summary statistics
    print(f"Generated {len(grids_gdf)} grids")
    print(f"Total weekly hours: {grids_gdf['weekly_hours'].sum():.1f}")
    print("\nGrid generation complete. Files saved:")
    print("- clinic_grids.geojson: Contains the grid geometries")
    print("- clinic_grids.csv: Contains the clinic data without geometries")

if __name__ == "__main__":
    main() 