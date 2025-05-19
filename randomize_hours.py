import pandas as pd
import numpy as np

# Read the original CSV file
df = pd.read_csv('dentist_data_map.csv')

# Set random seed for reproducibility
np.random.seed(42)

# Generate random hours between 10 and 50 for active clinics (where active = 1)
df.loc[df['active'] == 1, 'weekly_availability_hours'] = np.random.uniform(10, 50, size=len(df[df['active'] == 1]))

# Round to 1 decimal place
df['weekly_availability_hours'] = df['weekly_availability_hours'].round(1)

# Save the modified dataset
df.to_csv('dentist_data_map_random_hours.csv', index=False)

print("Successfully randomized weekly availability hours for active clinics!")
print(f"Total clinics: {len(df)}")
print(f"Active clinics with randomized hours: {len(df[df['active'] == 1])}") 