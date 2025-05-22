import pandas as pd
import numpy as np
import argparse

def main():
    parser = argparse.ArgumentParser(description='Sample clinics from the full dataset')
    parser.add_argument('--n_clinics', type=int, help='Number of clinics to sample')
    args = parser.parse_args()
    
    # Read the full dataset
    df = pd.read_csv('dentist_data_map_random_hours.csv')
    
    # Filter for active clinics
    active_clinics = df[df['active'] == 1].copy()
    total_active = len(active_clinics)
    
    if args.n_clinics is None or args.n_clinics >= total_active:
        # Use all active clinics
        sampled_clinics = active_clinics
    else:
        # Sample the specified number of clinics
        sampled_clinics = active_clinics.sample(n=args.n_clinics, random_state=42)
    
    # Save the sampled clinics
    sampled_clinics.to_csv('sample_clinics.csv', index=False)
    print(f"Sampled {len(sampled_clinics)} clinics from {total_active} active clinics")

if __name__ == '__main__':
    main() 