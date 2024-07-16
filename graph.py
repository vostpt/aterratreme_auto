import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import plotly.graph_objs as go
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import re


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

# Title of APP
title = "AterraTreme Dashboard"

proxies = [
    '31.170.22.127:1080',
    '195.201.2.11:58462',
    '51.91.106.22:61284',
    '94.23.220.136:19386',
    '94.23.222.122:31242',
    '51.89.21.99:10118',
    '92.204.40.109:56082',
    '91.150.189.122:60647',
    '95.31.5.29:51528',
    '91.223.52.141:5678',
    # Add all other proxies here
]
geolocator = Nominatim(user_agent=title, proxies={'http': proxies})
df = pd.DataFrame()

def update_data():
    global df
    df_temp = pd.read_csv('sismos_ipma.csv')
    if df.empty:
        df = df_temp
    if not df.equals(df_temp.iloc[0:50]):
        df = df_temp
        print("Data updated - Different data detected or df is empty")
    
    # Slice df and copy to df
    df = df.iloc[0:50].copy()
    latitude = []
    longitude = []

    for i in range(0, 50):
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

    # Filter rows without coordinates
    df = df.dropna(subset=['latitude', 'longitude'])

    return df

# Initialize the Dash application
app = dash.Dash(__name__)
app.title = title
# Get data
df = update_data()

# Layout of the Dash app
app.layout = html.Div(
    style={"background-color":"white", "font-family" : "sans-serif", "display" : "flex", "width":"97vw", "overflow": "hidden"},
    children=[
        html.Div(
            style={"background-color":"black", "width":"28vw", "padding-left":"5px", "padding-right":"5px"},
            children = [
                html.Div(
                    style = {"color" : "white"},
                    children = [
                        html.H1(title)
                    ]
                ),
                # Dropdown for title selection
                dcc.Dropdown(
                    id='title-dropdown',
                    options=[{'label': title, 'value': title} for title in df['Title']],
                    value=df['Title'].iloc[0],  # Initial value
                    style={"width": "100%"}
                ),
                html.Br(),
                # Div to display description and publication date
                html.Div(id='description-date', style={"color" : "white"}),
                html.Br(),
                dcc.Markdown(
                style={"color" : "white"},
                children = [
                '''
                #### Dados extraídos do [IPMA](https://www.ipma.pt)
                '''])
            ]
        ),
        html.Div(
            id='map-container',
            style={"height":"100vh"},
            children = [
                # Map to show the location of earthquakes
                dcc.Graph(id='map', style={"height":"100vh", "width":"65.5vw"}),
            ]
        )
])

# Callback to update description and publication date
@app.callback(
    Output('description-date', 'children'),
    [Input('title-dropdown', 'value')]
)
def update_description_data(selected_title):
    row = df[df['Title'] == selected_title]
    description = html.Table(
        style={"text-align": "left", "font-size":"15px"},
        children=[
            html.Tr([html.Th("Hora: "), html.Td(row['date_time'])]),
            html.Tr([html.Th("Epicentro: "), html.Td(row['location'])]),
            html.Tr([html.Th("Intensidade (MMI): "), html.Td(row['intensity'])]),
            html.Tr([html.Th("Magnitude: "), html.Td(row['scale'])])
        ])
    return description
# Callback to update the map with earthquake locations
@app.callback(
    Output('map', 'figure'),
    [Input('title-dropdown', 'value')]
)
def update_map(selected_title):
    #update_data()
    custom_colors = [
        "#006400", # Green
        "#00FF00", # Lime
        "#ffbf00", # Yellow
        "#ff4000", # Orange
        "#ff0000", # Red
    ]
    fig = px.scatter_mapbox(df,
                            lat='latitude',
                            lon='longitude', 
                            hover_name='Title',
                            hover_data=['intensity', 'location'],
                            color=df['scale'],
                            color_continuous_scale=custom_colors,
                            range_color=[1, 10],
                            size=df['scale'],
                            size_max=10,
                            zoom=4.5,
                            center=dict(lat=37.200, lon=-18.000),
                            )
    fig.update_layout(mapbox_style="open-street-map")
    fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})

    return fig


if __name__ == '__main__':
    app.run_server(debug=True)
