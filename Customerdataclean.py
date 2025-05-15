import pandas as pd

def clean_customer_data(input_csv: str, output_csv: str):
    # Load the CSV
    df = pd.read_csv(input_csv, low_memory=False)

    # Drop rows where lat or lon is missing
    df = df.dropna(subset=['latitude', 'longitude'])

    # Convert latitude & longitude to numeric, coerce errors to NaN, then drop
    df['latitude']  = pd.to_numeric(df['latitude'],  errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df = df.dropna(subset=['latitude', 'longitude'])

    # Filter to UK bounding box
    # Approx UK extents from online sources: lat between 49°N and 61°N, lon between -8°W and +2°E
    in_uk = (
        df['latitude'].between(49.0, 61.0) &
        df['longitude'].between(-8.0, 2.0)
    )
    df_uk = df.loc[in_uk].copy()

    # Output cleaned CSV
    df_uk.to_csv(output_csv, index=False)
    print(f"Cleaned data saved to {output_csv}: {len(df_uk)} rows retained (out of {len(df)})")

if __name__ == '__main__':
    clean_customer_data(
        input_csv='customers_with_latlon.csv',
        output_csv='customers_with_latlon_cleaned.csv'
    )
