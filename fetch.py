# fetch.py

from dotenv import load_dotenv
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import os
import math
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
from sqlalchemy import create_engine, Column, String, Integer, CHAR, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy_utils import database_exists, create_database


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

def fetch_xml_data(url):
    """
    Fetches XML data from the given URL and returns a DataFrame
    with columns: "Title", "Description", "Publication Date".
    """
    response = requests.get(url)
    root = ET.fromstring(response.content)
    data = []
    for item in root.findall(".//item"):
        title = item.find("title").text
        description = item.find("description").text
        pub_date = item.find("pubDate").text
        data.append([title, description, pub_date])
    pd.set_option('display.max_colwidth', None)
    return pd.DataFrame(data, columns=["Title", "Description", "Publication Date"])

def transform_location(loc):
    """
    Transforms the location string by replacing full cardinal directions with their 
    abbreviations and removing unnecessary words.
    """
    if loc is None:
        return None
    # Define a dictionary for cardinal direction replacements
    directions = {
        "Norte": "N",
        "Sul": "S",
        "Este": "E",
        "Oeste": "W",
        "Nordeste": "NE",
        "Noroeste": "NW",
        "Sudeste": "SE",
        "Sudoeste": "SW"
    }

    # Remove "cerca de" if exists
    loc = loc.replace("cerca de ", "")
    # Replace cardinal directions
    for key, value in directions.items():
        loc = loc.replace(key, value)
    # Remove "de" before the location name
    loc = re.sub(r' a de ', ' ', loc)
    return loc

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

def get_coordinates(df):
    latitude = []
    longitude = []

    for place in df['location']:
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
    df['latitude'] = latitude
    df['longitude'] = longitude



if __name__ == "__main__":

    # Load sensitive information
    load_dotenv('.env')
    host = os.getenv('host')
    user = os.getenv('user')
    password = os.getenv('password')
    database = os.getenv('database')

    # Define the XML data source URL
    url = "https://www.ipma.pt/resources.www/rss/comunicados.xml"
    df = fetch_xml_data(url)

    Base = declarative_base()

    class Earthquake(Base):
        # Name of table
        __tablename__ = "earthquake"
        # Columns id,Title,Description,Publication Date,date_time,scale,location,intensity,latitude,longitude
        id = Column("id", Integer, primary_key=True, autoincrement="auto")
        title = Column("title", Text)
        description = Column("description", Text)
        pub_date = Column("publication_date", String(25))
        date = Column("date_time", String(50))
        scale = Column("scale", Float)
        location = Column("location", String(255))
        intensity = Column("intensity", String(255))
        latitude = Column("latitude", Float)
        longitude = Column('longitude', Float)

        def __init__(self, id, title, description, pub_date, date, scale, location, intensity, latitude, longitude):
            self.id = id
            self.title = title
            self.description = description
            self.pub_date = pub_date
            self.date = date
            self. scale = scale
            self.location = location
            self.intensity = intensity
            self.latitude = latitude
            self.longitude = longitude

        def __repr__(self):
            return f"({self.id}) ({self.title}) ({self.description}) ({self.pub_date}) ({self.date}) ({self.scale}) ({self.location}) ({self.intensity}) ({self.latitude}) ({self.longitude})"

    # Define geolocator
    geolocator = Nominatim(user_agent="AterraTreme")

    # Filter the DataFrame to only include entries with "Sismo" in the "Title" or "Description"
    df = df[(df['Title'].str.contains("Sismo", case=False, na=False) | df['Description'].str.contains("Sismo", case=False, na=False))]

    # Extract date_time from the Description column
    df['date_time'] = df['Description'].apply(lambda x: re.search(r'(\d{2}-\d{2}-\d{4} pelas \d{2}:\d{2} \(hora local\))', x).group(1) if re.search(r'(\d{2}-\d{2}-\d{4} pelas \d{2}:\d{2} \(hora local\))', x) else None)

    # Extract scale from the Description column
    df['scale'] = df['Description'].apply(lambda x: re.search(r' magnitude (\d+\.\d+) \(Richter\)', x).group(1) if re.search(r' magnitude (\d+\.\d+) \(Richter\)', x) else None)

    # Extract location from the Description column and transform it
    df['location'] = df['Description'].apply(lambda x: re.search(r'localizou a (cerca de .*?)\.', x).group(1) if re.search(r'localizou a (cerca de .*?)\.', x) else re.search(r'localizou (próximo de .*?)\.', x).group(1) if re.search(r'localizou (próximo de .*?)\.', x) else None)
    df['location'] = df['location'].apply(transform_location)

    # Extract intensity from the Description column and fill None values
    df['intensity'] = df['Description'].apply(lambda x: re.search(r'(\w+/\w+) \(escala de Mercalli modificada\)', x).group(1) if re.search(r'(\w+/\w+) \(escala de Mercalli modificada\)', x) else (re.search(r'intensidade máxima (\w+) \(escala de Mercalli modificada\)', x).group(1) if re.search(r'intensidade máxima (\w+) \(escala de Mercalli modificada\)', x) else None))
    df['intensity'] = df['intensity'].fillna("Sem info a esta hora")

    
    get_coordinates(df)

    # Establishes the connection to the server
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{database}?charset=utf8mb4")
    if not database_exists(engine.url):
        create_database(engine.url)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # Get what is in the database in the earthquake table
    current_db_data = session.query(Earthquake)
    print("\n")

    # Run so that the oldest earthquake comes first
    for i in range(len(df)-1, -1, -1):
        contains = False
        # Stores the information to be placed in the database in the variable
        earthquake = Earthquake(
        None, 
        df.iloc[i]['Title'], 
        df.iloc[i]['Description'], 
        df.iloc[i]['Publication Date'], 
        df.iloc[i]['date_time'], 
        float(df.iloc[i]['scale']), 
        df.iloc[i]['location'], 
        df.iloc[i]['intensity'], 
        df.iloc[i]['latitude'], 
        df.iloc[i]['longitude']
    )
        # Checks if somewhere in the database there is already exactly that earthquake
        for data in current_db_data:
            if (data.description == earthquake.description):
                contains = True              
        # If it does not exist, place it in the database, otherwise it will inform you that the earthquake has already been registered
        if not contains:
            session.add(earthquake)
            session.commit()
        else:
            print("Earthquake already registered ✔")