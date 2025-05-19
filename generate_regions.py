import pandas as pd
import numpy as np
from shapely.geometry import Polygon, box, Point
import geopandas as gpd
from geopy.distance import geodesic
from shapely.ops import unary_union
import json
from typing import Dict, List, Tuple
from shapely.geometry import MultiPolygon

def calculate_grid_boundaries(lat: float, lon: float, distance_km: float) -> Dict[str, float]:
    """Calculate the boundaries of a grid square centered on a point."""
    north = geodesic(kilometers=distance_km).destination(point=(lat, lon), bearing=0).latitude
    south = geodesic(kilometers=distance_km).destination(point=(lat, lon), bearing=180).latitude
    east = geodesic(kilometers=distance_km).destination(point=(lat, lon), bearing=90).longitude
    west = geodesic(kilometers=distance_km).destination(point=(lat, lon), bearing=270).longitude
    
    return {
        'north': north,
        'south': south,
        'east': east,
        'west': west
    }

def create_clinic_grid(row: pd.Series, distance_km: float) -> Tuple[Polygon, Dict]:
    """Create a grid square for a clinic and return both geometry and metadata."""
    boundaries = calculate_grid_boundaries(row['latitude'], row['longitude'], distance_km)
    
    # Create the grid polygon
    grid = box(
        boundaries['west'],
        boundaries['south'],
        boundaries['east'],
        boundaries['north']
    )
    
    metadata = {
        'clinic_id': int(row['id']),  # Convert to regular int
        'weekly_hours': float(row['weekly_availability_hours'])  # Convert to regular float
    }
    
    return grid, metadata

def find_regions_for_grid_pair(grid1: Polygon, grid2: Polygon, metadata1: Dict, metadata2: Dict) -> List[Dict]:
    """Find regions created by two potentially overlapping grids."""
    regions = []
    
    if grid1.intersects(grid2):
        # Get the intersection (overlapping region)
        intersection = grid1.intersection(grid2)
        if intersection.area > 0:
            regions.append({
                'geometry': intersection,
                'clinic_ids': [metadata1['clinic_id'], metadata2['clinic_id']],
                'total_availability': metadata1['weekly_hours'] + metadata2['weekly_hours']
            })
            
            # Get the non-overlapping parts
            diff1 = grid1.difference(grid2)
            if not diff1.is_empty:
                regions.append({
                    'geometry': diff1,
                    'clinic_ids': [metadata1['clinic_id']],
                    'total_availability': metadata1['weekly_hours']
                })
            
            diff2 = grid2.difference(grid1)
            if not diff2.is_empty:
                regions.append({
                    'geometry': diff2,
                    'clinic_ids': [metadata2['clinic_id']],
                    'total_availability': metadata2['weekly_hours']
                })
    else:
        # No overlap, return both grids as separate regions
        regions.extend([
            {
                'geometry': grid1,
                'clinic_ids': [metadata1['clinic_id']],
                'total_availability': metadata1['weekly_hours']
            },
            {
                'geometry': grid2,
                'clinic_ids': [metadata2['clinic_id']],
                'total_availability': metadata2['weekly_hours']
            }
        ])
    
    return regions

def find_all_regions(grids_with_metadata: List[Tuple[Polygon, Dict]]) -> List[Dict]:
    """Find all unique regions formed by all grid overlaps."""
    all_regions = []
    processed_geometries = set()
    
    n = len(grids_with_metadata)
    for i in range(n):
        grid1, metadata1 = grids_with_metadata[i]
        
        # Start with the grid itself as a potential region
        current_regions = [{
            'geometry': grid1,
            'clinic_ids': [metadata1['clinic_id']],
            'total_availability': metadata1['weekly_hours']
        }]
        
        # Check overlaps with all other grids
        for j in range(i + 1, n):
            grid2, metadata2 = grids_with_metadata[j]
            new_regions = []
            
            # For each existing region, check if it overlaps with the new grid
            for region in current_regions:
                if region['geometry'].intersects(grid2):
                    # Find sub-regions created by this overlap
                    sub_regions = find_regions_for_grid_pair(
                        region['geometry'], 
                        grid2,
                        {'clinic_id': region['clinic_ids'][0], 'weekly_hours': region['total_availability']},
                        metadata2
                    )
                    new_regions.extend(sub_regions)
                else:
                    new_regions.append(region)
            
            current_regions = new_regions
        
        # Add unique regions to the final list
        for region in current_regions:
            geom_wkt = region['geometry'].wkt
            if geom_wkt not in processed_geometries:
                processed_geometries.add(geom_wkt)
                all_regions.append(region)
    
    return all_regions

def find_overlapping_regions(grids_gdf):
    """
    Find all unique regions created by overlapping grids.
    A region is defined as an area covered by a unique set of clinics.
    """
    regions = []
    region_id = 1
    
    # Create a list of all grid polygons with their clinic IDs and hours
    grid_list = [(row.geometry, row.clinic_id, row.weekly_hours) for idx, row in grids_gdf.iterrows()]
    n_grids = len(grid_list)
    
    # Process each grid
    processed_geometries = set()
    
    for i in range(n_grids):
        base_geom, base_id, base_hours = grid_list[i]
        
        # Start with the base grid's geometry
        current_geom = base_geom
        
        # Remove any parts that have been processed
        for processed_geom in processed_geometries:
            if current_geom.intersects(processed_geom):
                current_geom = current_geom.difference(processed_geom)
        
        if current_geom.is_empty:
            continue
        
        # Find all grids that overlap with the current geometry
        overlapping = []
        for j in range(n_grids):
            if i != j:
                other_geom, other_id, other_hours = grid_list[j]
                if current_geom.intersects(other_geom):
                    intersection = current_geom.intersection(other_geom)
                    if not intersection.is_empty and intersection.area > 0:
                        overlapping.append((other_id, other_hours, intersection))
        
        # Process the base geometry (non-overlapping part)
        if not current_geom.is_empty:
            # Remove overlapping parts
            for _, _, overlap_geom in overlapping:
                current_geom = current_geom.difference(overlap_geom)
            
            if not current_geom.is_empty:
                regions.append({
                    'region_id': region_id,
                    'clinic_ids': [base_id],
                    'total_availability_hours': base_hours,
                    'geometry': current_geom
                })
                region_id += 1
        
        # Process overlapping regions
        for j, (other_id, other_hours, intersection) in enumerate(overlapping):
            current_intersection = intersection
            
            # Remove any parts that have been processed
            for processed_geom in processed_geometries:
                if current_intersection.intersects(processed_geom):
                    current_intersection = current_intersection.difference(processed_geom)
            
            if not current_intersection.is_empty:
                regions.append({
                    'region_id': region_id,
                    'clinic_ids': sorted([base_id, other_id]),
                    'total_availability_hours': base_hours + other_hours,
                    'geometry': current_intersection
                })
                region_id += 1
        
        # Add the processed geometries to the set
        processed_geometries.add(base_geom)
    
    return regions

def main():
    # Parameters
    GRID_SIZE_KM = 30  # Size of grid squares (can be adjusted)
    
    # Load clinic data
    clinics_df = pd.read_csv('sample_clinics.csv')
    print(f"Loaded {len(clinics_df)} clinics")
    
    # Create grids for each clinic
    grids_with_metadata = []
    for _, row in clinics_df.iterrows():
        grid, metadata = create_clinic_grid(row, GRID_SIZE_KM)
        grids_with_metadata.append((grid, metadata))
    
    print("Created clinic grids")
    
    # Find all unique regions
    regions = find_all_regions(grids_with_metadata)
    print(f"Found {len(regions)} unique regions")
    
    # Create regions GeoDataFrame
    regions_gdf = gpd.GeoDataFrame({
        'geometry': [region['geometry'] for region in regions],
        'clinic_ids': [json.dumps([int(cid) for cid in region['clinic_ids']]) for region in regions],
        'total_availability_hours': [float(region['total_availability']) for region in regions]
    }, crs="EPSG:4326")
    
    # Add region_id
    regions_gdf['region_id'] = [f'R{i+1}' for i in range(len(regions_gdf))]
    
    # Save to GeoJSON
    regions_gdf.to_file('regions.geojson', driver='GeoJSON')
    print("Saved regions to regions.geojson")
    
    # Also save a CSV version for easier reading
    regions_df = pd.DataFrame({
        'region_id': regions_gdf['region_id'],
        'clinic_ids': regions_gdf['clinic_ids'],
        'total_availability_hours': regions_gdf['total_availability_hours'],
        'geometry': regions_gdf['geometry'].apply(lambda x: x.wkt)
    })
    regions_df.to_csv('regions.csv', index=False)
    print("Saved regions to regions.csv")

    # Load the clinic grids
    grids_gdf = gpd.read_file('clinic_grids.geojson')
    
    # Find all unique regions
    regions = find_overlapping_regions(grids_gdf)
    
    # Create a GeoDataFrame from the regions
    regions_gdf = gpd.GeoDataFrame(regions, crs="EPSG:4326")
    
    # Convert clinic_ids to JSON strings for storage
    regions_gdf['clinic_ids'] = regions_gdf['clinic_ids'].apply(json.dumps)
    
    # Save the regions to GeoJSON and CSV
    regions_gdf.to_file('regions.geojson', driver='GeoJSON')
    
    # Save a CSV version
    regions_df = pd.DataFrame({
        'region_id': regions_gdf['region_id'],
        'clinic_ids': regions_gdf['clinic_ids'],
        'total_availability_hours': regions_gdf['total_availability_hours']
    })
    regions_df.to_csv('regions.csv', index=False)
    
    # Print summary statistics
    print(f"\nRegion generation complete:")
    print(f"Generated {len(regions_gdf)} unique regions")
    print(f"Total weekly hours across all regions: {regions_gdf['total_availability_hours'].sum():.1f}")
    
    # Print distribution of overlap
    overlap_counts = regions_gdf['clinic_ids'].apply(lambda x: len(json.loads(x)))
    for n in range(1, overlap_counts.max() + 1):
        count = (overlap_counts == n).sum()
        print(f"Regions with {n} clinic{'s' if n > 1 else ''}: {count}")

if __name__ == '__main__':
    main() 