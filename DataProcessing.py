import csv
from geopy.geocoders import Nominatim
from functools import lru_cache
import time

geolocator = Nominatim(user_agent="postcode_locator")

@lru_cache(maxsize=5000)
def get_lat_lon(postcode: str):
    """Return latitude and longitude for a given postcode using Nominatim."""
    try:
        location = geolocator.geocode(postcode)
        time.sleep(1)  # Respect Nominatim's usage policy (1 request/sec)
        if location:
            return location.latitude, location.longitude
    except Exception as e:
        print(f"Error fetching location for {postcode}: {e}")
    return None, None

with open('customers_with_postcodes.csv', mode='r', newline='', encoding='utf-8') as file:
    reader = csv.reader(file)
    final_data = []
    for index, row in enumerate(reader):
        if index == 0:
            headers = row + ["latitude", "longitude"]
        else:
            row_dict = dict(zip(headers[:-2], row))  # exclude lat/lon for now
            postcode = row_dict.get("postal_code", "")
            lat, lon = get_lat_lon(postcode)
            row_dict["latitude"] = lat
            row_dict["longitude"] = lon
            final_data.append(row_dict)
            print(row_dict)

# Write the enriched data to a new CSV
with open('customers_with_latlon.csv', mode='w', newline='', encoding='utf-8') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=headers)
    writer.writeheader()
    writer.writerows(final_data)

print("Enriched dataset saved to 'customers_with_latlon.csv'")