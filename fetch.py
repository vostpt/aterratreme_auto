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

def extract_locale(text):
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
    direcoes = {
        'N': 0,
        'N-NE': 22.5,
        'NE': 45,
        'E-NE': 67.5,
        'L': 90,
        'E-SE': 112.5,
        'SE': 135,
        'S-SE': 157.5,
        'S': 180,
        'S-SW': 202.5,
        'SW': 225,
        'W-SW': 247.5,
        'O': 270,
        'W-NW': 292.5,
        'NW': 315,
        'N-NW': 337.5
    }
    return direcoes.get(direction)

def calculate_new_coordinate(lat, lon, distance_km, azimute):
    # Raio da Terra em km
    R = 6371.0

    # Converter latitude e longitude de graus para radianos
    lat_rad = math.radians(lat)
    lon_rad = math.radians(lon)

    # Converter distância para radianos
    distance_rad = distance_km / R

    # Converter azimute de graus para radianos
    azimute_rad = math.radians(azimute)

    # Calcular a nova latitude
    new_lat_rad = math.asin(math.sin(lat_rad) * math.cos(distance_rad) +
                             math.cos(lat_rad) * math.sin(distance_rad) * math.cos(azimute_rad))

    # Calcular a nova longitude
    new_lon_rad = lon_rad + math.atan2(math.sin(azimute_rad) * math.sin(distance_rad) * math.cos(lat_rad),
                                        math.cos(distance_rad) - math.sin(lat_rad) * math.sin(new_lat_rad))

    # Converter coordenadas de volta para graus
    new_lat = math.degrees(new_lat_rad)
    new_lon = math.degrees(new_lon_rad)

    return new_lat, new_lon


if __name__ == "__main__":

    # Loading the sensative information
    load_dotenv('.env')
    Host: str = os.getenv('host')
    User: str = os.getenv('user')
    Password: str = os.getenv('password')
    Database: str = os.getenv('database')

    # Define the XML data source URL
    url = "https://www.ipma.pt/resources.www/rss/comunicados.xml"
    df = fetch_xml_data(url)

    Base = declarative_base()

    class Earthquake(Base):
        __tablename__ = "earthquake"
        # Title,Description,Publication Date,date_time,scale,location,intensity,latitude,longitude
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
    print(df['Description'])

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
        place = extract_locale(str(df['location'][i]))
        # Try to search and get place coordinates from csv
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
        if re.search(r'\d', df['location'][i]):
            distance, coordinate = re.search(r'(\d+)\s*km\s+a\s+([NSEW]+(?:-[NSEW]+)?)', df['location'][i]).groups()
            azimute = direction_to_azimuth(coordinate)
            print(azimute)
            if azimute is not None:
                    new_latitude, new_longitude = calculate_new_coordinate(df['latitude'][i], df['longitude'][i], float(distance), azimute)
                    print(f'Nova latitude: {new_latitude}, Nova longitude: {new_longitude}')
                    df['latitude'][i] = new_latitude
                    df['longitude'][i] = new_longitude
            else:
                print("Direção inválida")
        else:
                print(f"Coordinates remain the same: {df['latitude'][i]}, {df['longitude'][i]}")

    engine = create_engine("mysql+pymysql://root:@localhost/aterratreme?charset=utf8mb4")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    for i in range(len(df)-1, -1, -1):
        sismo = Earthquake(id, df['Title'][i], df['Description'][i], df['Publication Date'][i], df['date_time'][i], float(df['scale'][i]), df['location'][i], df['intensity'][i], df['latitude'][i], df['longitude'][i])
        session.add(sismo)
        session.commit()