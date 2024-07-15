# fetch.py


from dotenv import load_dotenv
import requests
import xml.etree.ElementTree as ET
import pandas as pd
import re
import os
import mysql.connector

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

def add_to_mysql():
    for i in range(len(df) - 1, -1, -1):
        info = (df_current['Title'][i], df_current['Description'][i], df_current['Publication Date'][i], df_current['date_time'][i], float(df_current['scale'][i]), df_current['location'][i], df_current['intensity'][i])
        mycursor.execute(sql, info)
        mydb.commit()
        print(mycursor.rowcount, "record inserted.")

if __name__ == "__main__":

    # Loading the sensative information
    load_dotenv('.env')
    Host: str = os.getenv('host')
    User: str = os.getenv('user')
    Password: str = os.getenv('password')
    Database: str = os.getenv('database')

    # Conecting to the MySQL server
    mydb = mysql.connector.connect(
        host=Host,
        user=User,
        password=Password, # Substituir password
        database=Database
    )

    # Define the XML data source URL
    url = "https://www.ipma.pt/resources.www/rss/comunicados.xml"
    df = fetch_xml_data(url)

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

    df_current = df 

    mycursor = mydb.cursor()
    sql = "INSERT INTO sismos (title, description, publication_date, date_time, scale, location, intensity) VALUES (%s, %s, %s, %s, %s, %s ,%s)"
    # Check if "sismos_ipma.csv" exists and read it
    try:
        existing_df = pd.read_csv("sismos_ipma.csv")
        # Compare the most recent data in df with the most recent data in existing_df
        if df_current['Title'].iloc[0] != existing_df['Title'].iloc[0]:
            temp_df = pd.concat([df_current, existing_df], ignore_index=True)

            # Check if the file size exceeds 50MB
            if os.path.getsize("sismos_ipma.csv") > 50 * 1024 * 1024:  # 50MB in bytes
                # Find the next available sequential file name
                i = 1
                while os.path.exists(f"sismos_ipma_{i}.csv"):
                    i += 1
                os.rename("sismos_ipma.csv", f"sismos_ipma_{i}.csv")
                # Create a new file for new data
                temp_df.to_csv("sismos_ipma.csv", index=False)
                print(f"File size exceeded 50MB, existing data moved to sismos_ipma_{i}.csv, and new data written to sismos_ipma.csv.")
                
            else:
                # If the file size is within limit, append the data
                temp_df.to_csv("sismos_ipma.csv", index=False)
                print("New data found and appended to sismos_ipma.csv.")

            # Add informations to MySQL database
            add_to_mysql()

        else:
            print("No new data found.")
            
    except FileNotFoundError:
        # If the CSV file doesn't exist, create it
        df_current.to_csv("sismos_ipma.csv", index=False)
        print("sismos_ipma.csv file created.")

        # Add informations to MySQL database
        add_to_mysql()

