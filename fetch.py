# fetch.py

import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re

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
    return pd.DataFrame(data, columns=["Title", "Description", "Publication Date"])

def transform_location(loc):
    """
    Transforms the location string by replacing full cardinal directions with their 
    abbreviations and removing unnecessary words.
    """
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

if __name__ == "__main__":
    # Define the XML data source URL
    url = "https://www.ipma.pt/resources.www/rss/comunicados.xml"
    df = fetch_xml_data(url)

    # Filter the DataFrame to only include rows with "Aviso de Sismo" in the Title column
    df = df[df["Title"].str.contains("Aviso de Sismo", case=False, na=False)]

    # Extract date_time from the Description column
    df['date_time'] = df['Description'].apply(lambda x: re.search(r'(\d{2}-\d{2}-\d{4} pelas \d{2}:\d{2} \(hora local\))', x).group(1) if re.search(r'(\d{2}-\d{2}-\d{4} pelas \d{2}:\d{2} \(hora local\))', x) else None)

    # Extract scale from the Description column
    df['scale'] = df['Description'].apply(lambda x: re.search(r' magnitude (\d+\.\d+) \(Richter\)', x).group(1) if re.search(r' magnitude (\d+\.\d+) \(Richter\)', x) else None)

    # Extract location from the Description column and transform it
    df['location'] = df['Description'].apply(lambda x: re.search(r'localizou a (cerca de .*?)\.', x).group(1) if re.search(r'localizou a (cerca de .*?)\.', x) else None)
    df['location'] = df['location'].apply(transform_location)

    # Extract intensity from the Description column and fill None values
    df['intensity'] = df['Description'].apply(lambda x: re.search(r'(\w+/\w+) \(escala de Mercalli modificada\)', x).group(1) if re.search(r'(\w+/\w+) \(escala de Mercalli modificada\)', x) else None)
    df['intensity'].fillna("Sem info a esta hora", inplace=True)

    # Check if "sismos_ipma.csv" exists and read it
    try:
        existing_df = pd.read_csv("sismos_ipma.csv")
        # Compare the most recent data in df with the most recent data in existing_df
        if df['Title'].iloc[0] != existing_df['Title'].iloc[0]:
            # If the most recent data is new, append it to the CSV
            df.to_csv("sismos_ipma.csv", mode='a', header=False, index=False)
            print("New data found and appended to sismos_ipma.csv.")
        else:
            print("No new data found.")
    except FileNotFoundError:
        # If the CSV file doesn't exist, create it
        df.to_csv("sismos_ipma.csv", index=False)
        print("sismos_ipma.csv file created.")
