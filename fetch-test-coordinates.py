# fetch-test-coordinates.py


import re
import math
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


municipios = {
    "São Miguel": ["Ponta Delgada", "Ribeira Grande", "Lagoa", "Vila Franca do Campo", "Nordeste", "Povoação"],
    "Terceira": ["Angra do Heroísmo", "Praia da Vitória"],
    "Pico": ["Madalena", "São Roque do Pico", "Lajes do Pico"],
    "Faial": ["Horta"],
    "Graciosa": ["Santa Cruz da Graciosa"],
    "São Jorge": ["Velas", "Calheta"],
    "Flores": ["Santa Cruz das Flores", "Lajes das Flores"],
    "Corvo": ["Vila do Corvo"],
    "Madeira": ["Funchal", "Câmara de Lobos", "Machico", "Calheta", "Ponta do Sol",
                "Ribeira Brava", "São Vicente", "Santana", "Porto Moniz", "Santa Cruz"],
    "Porto Santo": ["Porto Santo"]
}

def obter_municipios(ilha):
    ilha = ilha.capitalize()  # Capitaliza a primeira letra para garantir que seja case-insensitive
    if ilha in municipios:
        return municipios[ilha]
    else:
        return None  # Retorna None se a ilha não existir no dicionário

def direction_to_azimuth(direction):
    directions = {
        'N': 0,
        'N-NE': 22.5,
        'NE': 45,
        'E-NE': 67.5,
        'E': 90,
        'E-SE': 112.5,
        'SE': 135,
        'S-SE': 157.5,
        'S': 180,
        'S-SW': 202.5,
        'SW': 225,
        'W-SW': 247.5,
        'W': 270,
        'W-NW': 292.5,
        'NW': 315,
        'N-NW': 337.5
    }
    return directions.get(direction)

def calculate_new_coordinate(lat, lon, distance_km, azimuth):
    # Earth's radius in km
    R = 6371.0

    # Convert latitude and longitude from degrees to radians
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    # Convert distance to radians
    distance_rad = distance_km / R

    # Convert azimuth from degrees to radians
    azimuth_rad = math.radians(azimuth)

    # Calculate the new latitude
    new_lat_rad = math.asin(math.sin(lat_rad) * math.cos(distance_rad) +
                             math.cos(lat_rad) * math.sin(distance_rad) * math.cos(azimuth_rad))

    # Calculate the new longitude
    new_lon_rad = lon_rad + math.atan2(math.sin(azimuth_rad) * math.sin(distance_rad) * math.cos(lat_rad),
                                        math.cos(distance_rad) - math.sin(lat_rad) * math.sin(new_lat_rad))

    # Convert coordinates back to degrees
    new_lat = math.degrees(new_lat_rad)
    new_lon = math.degrees(new_lon_rad)

    return new_lat, new_lon

def get_coordinates(locais):
    global latitudes
    global longitudes
    latitude = []
    longitude = []

    for place in locais:
        # Search for text within parentheses to get the island
        match = re.search(r'\((.*?)\)', place)
        if match:
            island = match.group(1).strip()
            municipios = obter_municipios(island)
            if municipios:
                found = False
                for municipio in municipios:
                    # Remove parentheses content for search
                    location_text = re.sub(r'\(.*?\)', '', place)
                    # Extract the actual location name
                    pattern = r'(?:de|da)\s(.*)'
                    match2 = re.search(pattern, location_text, re.IGNORECASE)
                    if match2:
                        location_name = match2.group(1).strip()
                        full_location = f"{location_name}, {municipio}, Portugal"
                        try:
                            location = geolocator.geocode(full_location)
                            if location:
                                lat, lon = location.latitude, location.longitude
                                print(f"Conseguido: {full_location} | {lat} and {lon}")
                                found = True
                                
                                # Adjust coordinates if distance and direction are provided
                                distance_match = re.search(r'(\d+)\s*km\s*a\s+([NSEW]+(?:-[NSEW]+)?)', place)
                                if distance_match:
                                    distance, direction = distance_match.groups()
                                    azimuth = direction_to_azimuth(direction)
                                    if azimuth is not None:
                                        new_lat, new_lon = calculate_new_coordinate(lat, lon, float(distance), azimuth)
                                        latitude.append(new_lat)
                                        longitude.append(new_lon)
                                    else:
                                        latitude.append(lat)
                                        longitude.append(lon)
                                else:
                                    latitude.append(lat)
                                    longitude.append(lon)
                                
                                break  # Exit the loop once we have found a valid location
                            else:
                                print(f"Location not found: {full_location}")
                        except (GeocoderTimedOut, GeocoderServiceError) as e:
                            print(f"Error getting coordinates for {place}: {e}")
                if not found:
                    latitude.append(None)
                    longitude.append(None)
            else:
                latitude.append(None)
                longitude.append(None)
        else:
            # Handle continental cases directly
            pattern = r'(?:de|da)\s(.*)'
            match2 = re.search(pattern, place, re.IGNORECASE)
            if match2:
                location_name = match2.group(1).strip()
                full_location = f"{location_name}, Portugal"
                try:
                    location = geolocator.geocode(full_location)
                    if location:
                        lat, lon = location.latitude, location.longitude
                        print(f"Conseguido: {full_location}")
                        
                        # Adjust coordinates if distance and direction are provided
                        distance_match = re.search(r'(\d+)\s*km\s*a\s+([NSEW]+(?:-[NSEW]+)?)', place)
                        if distance_match:
                            distance, direction = distance_match.groups()
                            azimuth = direction_to_azimuth(direction)
                            if azimuth is not None:
                                new_lat, new_lon = calculate_new_coordinate(lat, lon, float(distance), azimuth)
                                latitude.append(new_lat)
                                longitude.append(new_lon)
                            else:
                                latitude.append(lat)
                                longitude.append(lon)
                        else:
                            latitude.append(lat)
                            longitude.append(lon)
                    else:
                        latitude.append(None)
                        longitude.append(None)
                except (GeocoderTimedOut, GeocoderServiceError) as e:
                    print(f"Error getting coordinates for {place}: {e}")
                    latitude.append(None)
                    longitude.append(None)
            else:
                latitude.append(None)
                longitude.append(None)

    # Add coordinates to data
    latitudes = latitude
    longitudes = longitude



if __name__ == "__main__":

    latitudes = []
    longitudes = []

    # Places to test to obtain coordinates
    locais=[
        "40 km a Sudoeste de Faro",
        "4 km a Norte-Nordeste de Sta Bárbara (Terceira)",
        "12 km a Oeste-Noroeste de Ferreira do Alentejo",
        "4 km a Nordeste de Sta Bárbara (Terceira)",
        "Próximo de Raminho (Terceira)"
    ]

    # Define geolocator
    geolocator = Nominatim(user_agent="AterraTreme")
    
    # Get coordinates
    get_coordinates(locais)

    # If all is correct print all index's
    for i in range(len(latitudes)):
        print(f"Indice [{i}] {latitudes[i]} {longitudes[i]}")