import pandas as pd
import numpy as np
import argparse
import os

def get_clinics(input_file, n_clinics=None, random_seed=None):
    """
    Get a sample of clinics or all active clinics.
    
    Args:
        input_file (str): Path to the input CSV file
        n_clinics (int, optional): Number of clinics to sample. If None, returns all active clinics.
        random_seed (int, optional): Random seed for reproducibility
    """
    # Get the absolute path to the input file
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    file_path = os.path.join(parent_dir, input_file)
    
    # Read the full dataset
    df = pd.read_csv(file_path)
    
    # Filter active clinics
    active_clinics = df[df['active'] == 1].copy()
    total_active = len(active_clinics)
    print(f"\nFound {total_active} active clinics out of {len(df)} total clinics")
    
    if n_clinics is None:
        print("Using all active clinics")
        return active_clinics
    
    if n_clinics > total_active:
        print(f"\nWarning: Requested {n_clinics} clinics but only {total_active} active clinics available")
        print("Using all active clinics instead")
        return active_clinics
    
    # Sample clinics randomly
    sampled = active_clinics.sample(n=n_clinics, random_state=random_seed)
    print(f"Randomly sampled {len(sampled)} clinics from {total_active} active clinics")
    
    return sampled

def main():
    parser = argparse.ArgumentParser(description='Sample or get all active clinics from dataset')
    parser.add_argument('--n_clinics', type=int, help='Number of clinics to sample. If not provided, uses all active clinics.')
    parser.add_argument('--random_seed', type=int, default=42, help='Random seed for reproducibility')
    parser.add_argument('--input_file', type=str, default='dentist_data_map_random_hours.csv', help='Input CSV file path')
    args = parser.parse_args()
    
    # Get clinics
    selected_clinics = get_clinics(args.input_file, args.n_clinics, args.random_seed)
    
    # Save to CSV
    selected_clinics.to_csv('sample_clinics.csv', index=False)
    print(f"Successfully saved {len(selected_clinics)} clinics to sample_clinics.csv")

if __name__ == "__main__":
    main() 