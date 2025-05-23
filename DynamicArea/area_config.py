from typing import Dict, List, Tuple

# Define major UK cities and their approximate bounding boxes
# Format: [min_lon, min_lat, max_lon, max_lat]
CITY_BOUNDARIES = {
    'London': [-0.5103, 51.2868, 0.3340, 51.6923],
    'Manchester': [-2.3026, 53.3997, -2.0632, 53.5397],
    'Birmingham': [-2.0336, 52.3810, -1.7288, 52.5730],
    'Leeds': [-1.7229, 53.7457, -1.3847, 53.8957],
    'Glasgow': [-4.3932, 55.7944, -4.0661, 55.9288],
    'Edinburgh': [-3.2973, 55.8927, -3.1383, 56.0011],
    'Liverpool': [-3.0187, 53.3336, -2.8219, 53.4875],
    'Newcastle': [-1.7062, 54.9479, -1.5231, 55.0421],
    'Sheffield': [-1.5437, 53.3220, -1.3924, 53.4308],
    'Bristol': [-2.7129, 51.4094, -2.5157, 51.5429]
}

# Define grid sizes (in km) for different area types
GRID_SIZES = {
    'metropolitan': 15,  # Dense urban areas like London
    'urban': 20,        # Major cities
    'suburban': 25,     # Surrounding areas
    'rural': 30        # Rural areas
}

# Define area types for each city
CITY_TYPES = {
    'London': 'metropolitan',
    'Manchester': 'urban',
    'Birmingham': 'urban',
    'Leeds': 'urban',
    'Glasgow': 'urban',
    'Edinburgh': 'urban',
    'Liverpool': 'urban',
    'Newcastle': 'urban',
    'Sheffield': 'urban',
    'Bristol': 'urban'
}

# Default grid size for areas not covered by cities
DEFAULT_GRID_SIZE = GRID_SIZES['rural']

def get_area_type(lon: float, lat: float) -> str:
    """Determine the area type based on coordinates."""
    # Check if coordinates fall within any city boundary
    for city, bounds in CITY_BOUNDARIES.items():
        min_lon, min_lat, max_lon, max_lat = bounds
        if min_lon <= lon <= max_lon and min_lat <= lat <= max_lat:
            return CITY_TYPES[city]
    
    return 'rural'

def get_grid_size(lon: float, lat: float) -> float:
    """Get the appropriate grid size for given coordinates."""
    area_type = get_area_type(lon, lat)
    return GRID_SIZES[area_type] 