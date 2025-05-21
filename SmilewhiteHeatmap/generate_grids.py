import pandas as pd
import geopandas as gpd
from shapely.geometry import box, Point
import numpy as np
from math import sqrt
import argparse
from sklearn.cluster import DBSCAN
from shapely.ops import unary_union
from typing import List, Dict, Tuple
import json

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

def merge_nearby_squares(grids: List[Dict], distance_km: float) -> List[Dict]:
    """
    Merge grid squares that are within a certain distance of each other.
    Uses DBSCAN clustering on centroids with a distance threshold.
    """
    if distance_km <= 0:
        return grids

    # Convert the distance threshold from km to degrees (approx. 1 deg ~ 111 km)
    eps_deg = distance_km / 111.0

    # Extract centroids and create array for DBSCAN
    centroids = np.array([
        [grid['geometry'].centroid.x, grid['geometry'].centroid.y]
        for grid in grids
    ])

    # Apply DBSCAN clustering
    clustering = DBSCAN(eps=eps_deg, min_samples=1).fit(centroids)
    
    merged_grids = []
    for cluster_id in np.unique(clustering.labels_):
        # Get indices of grids in this cluster
        indices = np.where(clustering.labels_ == cluster_id)[0]
        
        # Get all grids in this cluster
        cluster_grids = [grids[i] for i in indices]
        
        # Merge geometries using unary_union
        merged_geom = unary_union([grid['geometry'] for grid in cluster_grids])
        
        # Sum up weekly hours
        total_hours = sum(grid['weekly_hours'] for grid in cluster_grids)
        
        # Collect all clinic IDs
        clinic_ids = [grid['clinic_id'] for grid in cluster_grids]
        
        # Create merged grid
        merged_grid = {
            'clinic_id': clinic_ids[0],  # Use first clinic ID as primary
            'all_clinic_ids': clinic_ids,  # Keep track of all merged clinic IDs
            'weekly_hours': total_hours,
            'geometry': merged_geom
        }
        merged_grids.append(merged_grid)
    
    return merged_grids

def main():
    parser = argparse.ArgumentParser(description='Generate clinic grids')
    parser.add_argument('--grid_size', type=float, default=20, help='Grid size in kilometers (radius)')
    parser.add_argument('--merge_distance', type=float, default=5, help='Distance in kilometers for merging nearby grids')
    args = parser.parse_args()
    
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
            radius_km=args.grid_size
        )
        
        grid_data = {
            'clinic_id': row['id'],
            'weekly_hours': row['weekly_availability_hours'],
            'geometry': grid
        }
        grids.append(grid_data)
    
    print(f"Created {len(grids)} initial grids")
    
    # Merge nearby grids if merge_distance > 0
    merged_grids = merge_nearby_squares(grids, args.merge_distance)
    print(f"Merged into {len(merged_grids)} grids")
    
    # Create two versions of the data: one for GeoJSON (without all_clinic_ids) and one for CSV
    geojson_grids = []
    csv_grids = []
    
    for grid in merged_grids:
        # Version for GeoJSON (without all_clinic_ids)
        geojson_grid = {
            'clinic_id': grid['clinic_id'],
            'weekly_hours': grid['weekly_hours'],
            'geometry': grid['geometry']
        }
        geojson_grids.append(geojson_grid)
        
        # Version for CSV (with all_clinic_ids as JSON string)
        csv_grid = {
            'clinic_id': grid['clinic_id'],
            'all_clinic_ids': json.dumps(grid['all_clinic_ids']),
            'weekly_hours': grid['weekly_hours']
        }
        csv_grids.append(csv_grid)
    
    # Create and save GeoJSON version
    grids_gdf = gpd.GeoDataFrame(geojson_grids, crs="EPSG:4326")
    grids_gdf.to_file('clinic_grids.geojson', driver='GeoJSON')
    
    # Save CSV version
    grids_df = pd.DataFrame(csv_grids)
    grids_df.to_csv('clinic_grids.csv', index=False)
    
    # Print summary statistics
    print(f"\nGrid generation complete:")
    print(f"Total weekly hours: {grids_gdf['weekly_hours'].sum():.1f}")
    print("\nFiles saved:")
    print("- clinic_grids.geojson: Contains the grid geometries")
    print("- clinic_grids.csv: Contains the clinic data with merged IDs")

if __name__ == "__main__":
    main() 