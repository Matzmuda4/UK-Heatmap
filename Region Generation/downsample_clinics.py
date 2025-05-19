import pandas as pd
import numpy as np
import argparse

def downsample_clinics(input_file, n_clinics):
    """Downsample the clinics dataset to n_clinics while maintaining geographic distribution."""
    # Read the full dataset
    df = pd.read_csv(input_file)
    
    # Filter active clinics
    active_clinics = df[df['active'] == 1].copy()
    
    # Extract postcode area (first two characters)
    active_clinics['postcode_area'] = active_clinics['postcode'].str[:2]
    
    # Calculate number of clinics to sample from each postcode area
    area_counts = active_clinics['postcode_area'].value_counts()
    area_proportions = area_counts / area_counts.sum()
    n_per_area = (area_proportions * n_clinics).round().astype(int)
    
    # Ensure we get exactly n_clinics
    while n_per_area.sum() != n_clinics:
        if n_per_area.sum() > n_clinics:
            # Remove one from the largest area
            largest_area = n_per_area.idxmax()
            n_per_area[largest_area] -= 1
        else:
            # Add one to the largest area
            largest_area = n_per_area.idxmax()
            n_per_area[largest_area] += 1
    
    # Sample clinics from each area
    sampled_clinics = []
    for area, n in n_per_area.items():
        area_clinics = active_clinics[active_clinics['postcode_area'] == area]
        if len(area_clinics) > 0:
            sampled = area_clinics.sample(n=min(n, len(area_clinics)), random_state=42)
            sampled_clinics.append(sampled)
    
    # Combine all sampled clinics
    result = pd.concat(sampled_clinics)
    
    # If we still don't have enough clinics, add more from remaining active clinics
    if len(result) < n_clinics:
        remaining = active_clinics[~active_clinics.index.isin(result.index)]
        additional = remaining.sample(n=n_clinics - len(result), random_state=42)
        result = pd.concat([result, additional])
    
    return result

def main():
    parser = argparse.ArgumentParser(description='Downsample clinics dataset')
    parser.add_argument('--n_clinics', type=int, default=30, help='Number of clinics to sample')
    args = parser.parse_args()
    
    # Downsample clinics
    sampled_clinics = downsample_clinics('/Users/matzmuda/Desktop/UK-Heatmap-1/dentist_data_map_random_hours.csv', args.n_clinics)
    # Save to CSV
    sampled_clinics.to_csv('sample_clinics.csv', index=False)
    print(f"Successfully sampled {len(sampled_clinics)} clinics")

if __name__ == "__main__":
    main() 