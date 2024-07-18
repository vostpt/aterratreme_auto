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

def extract_location(text):
    # Pattern to identify text within parentheses
    pattern_parentheses = r'\((.*?)\)'

    # Pattern to identify text after the word "de"
    pattern_de = r'de (.*)'

    # Try to find text within parentheses
    match_parentheses = re.search(pattern_parentheses, text)
    if match_parentheses:
        return match_parentheses.group(1).strip() + ", Portugal"

    # If not found within parentheses, try to find after "de"
    match_de = re.search(pattern_de, text)
    if match_de:
        return match_de.group(1).strip() + ", Portugal"

    # If no specific pattern is found, return None or an error message
    return ""

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
    df = df[df['Title'].str.contains("Sismo") | df['Description'].str.contains("Sismo")]

    # Extract date_time from the Description column
    df['date_time'] = df['Description'].apply(lambda x: re.search(r'(\d{2}-\d{2}-\d{4} pelas \d{2}:\d{2} \(hora local\))', x).group(1) if re.search(r'(\d{2}-\d{2}-\d{4} pelas \d{2}:\d{2} \(hora local\))', x) else None)

    # Extract scale from the Description column
    df['scale'] = df['Description'].apply(lambda x: re.search(r' magnitude (\d+\.\d+) \(Richter\)', x).group(1) if re.search(r' magnitude (\d+\.\d+) \(Richter\)', x) else None)

    # Extract location from the Description column and transform it
    df['location'] = df['Description'].apply(lambda x: re.search(r'localizou a (cerca de .*?)\.', x).group(1) if re.search(r'localizou a (cerca de .*?)\.', x) else re.search(r'localizou (próximo de .*?)\.', x).group(1) if re.search(r'localizou (próximo de .*?)\.', x) else None)
    df['location'] = df['location'].apply(transform_location)

    # Extract intensity from the Description column and fill None values
    df['intensity'] = df['Description'].apply(lambda x: re.search(r'(\w+/\w+) \(escala de Mercalli modificada\)', x).group(1) if re.search(r'(\w+/\w+) \(escala de Mercalli modificada\)', x) else (re.search(r'intensidade máxima (\w+) \(escala de Mercalli modificada\)', x).group(1) if re.search(r'intensidade máxima (\w+) \(escala de Mercalli modificada\)', x) else None))
    for i in range(len(df["intensity"])):
        if pd.isna(df['intensity'][i]):
            df['intensity'][i] = "Sem info a esta hora"

    latitude = []
    longitude = []

    for i in range(len(df)):
        # Adapter to obtain locations and transform them into a Nominatim query
        place = extract_location(str(df['location'][i]))
        # Try to search and get place coordinates
        try:
            location = geolocator.geocode(place)
            if location:
                latitude.append(location.latitude)
                longitude.append(location.longitude)
            else:
                latitude.append(None)
                longitude.append(None)
        except (GeocoderTimedOut, GeocoderServiceError) as e:
            print(f"Error getting coordinates for {place}: {e}")
            latitude.append(None)
            longitude.append(None)

    # Add coordinates to data
    df['latitude'] = latitude
    df['longitude'] = longitude
    
    for i in range(len(df)):
        # Checks if the location contains any numbers (necessary to adjust the coordinates)
        if re.search(r'\d', df['location'][i]):
            # Gets the distance and cardinal points separately
            distance, cardinal = re.search(r'(\d+)\s*km\s+a\s+([NSEW]+(?:-[NSEW]+)?)', df['location'][i]).groups()
            # Converts the cardinal point to azimuth
            azimuth = direction_to_azimuth(cardinal)
            if azimuth is not None:
                    # Get the new adjusted coordinates
                    new_latitude, new_longitude = calculate_new_coordinate(df['latitude'][i], df['longitude'][i], float(distance), azimuth)
                    df['latitude'][i] = new_latitude
                    df['longitude'][i] = new_longitude
            else:
                print("Invalid direction")

    # Establishes the connection to the server
    engine = create_engine(f"mysql+pymysql://{user}:{password}@{host}/{database}?charset=utf8mb4")
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
        earthquake = Earthquake(None, df['Title'][i], df['Description'][i], df['Publication Date'][i], df['date_time'][i], float(df['scale'][i]), df['location'][i], df['intensity'][i], df['latitude'][i], df['longitude'][i])
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
