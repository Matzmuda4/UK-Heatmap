import pandas as pd
import numpy as np

# Read the randomized hours dataset
df = pd.read_csv('dentist_data_map_random_hours.csv')

# Set random seed for reproducibility
np.random.seed(42)

# Filter active clinics first
active_clinics = df[df['active'] == 1].copy()

# Ensure we have a good geographic distribution by stratifying based on the first two characters of postcodes
active_clinics['postcode_area'] = active_clinics['postcode'].str[:2]

# Group by postcode area and sample proportionally
sampled_clinics = []
n_samples = 30

# Calculate the number of clinics to sample from each postcode area
postcode_counts = active_clinics['postcode_area'].value_counts()
total_active = len(active_clinics)

for postcode, count in postcode_counts.items():
    # Calculate proportional number of clinics to sample from this area
    n_from_area = max(1, int(round((count / total_active) * n_samples)))
    area_clinics = active_clinics[active_clinics['postcode_area'] == postcode]
    
    # Sample clinics from this area
    sampled = area_clinics.sample(min(n_from_area, len(area_clinics)))
    sampled_clinics.append(sampled)

# Combine all sampled clinics
final_sample = pd.concat(sampled_clinics)

# If we have more than 30 clinics, randomly remove some to get exactly 30
if len(final_sample) > 30:
    final_sample = final_sample.sample(30)
# If we have less than 30, add more random active clinics
elif len(final_sample) < 30:
    remaining_clinics = active_clinics[~active_clinics.index.isin(final_sample.index)]
    additional_needed = 30 - len(final_sample)
    additional_sample = remaining_clinics.sample(additional_needed)
    final_sample = pd.concat([final_sample, additional_sample])

# Save the downsampled dataset
final_sample.to_csv('sample_clinics.csv', index=False)

print(f"Successfully created sample of 30 clinics!")
print(f"Number of unique postcode areas: {len(final_sample['postcode_area'].unique())}")
print("\nDistribution of clinics by postcode area:")
print(final_sample['postcode_area'].value_counts()) 