#Integration of Dashboards for sorfML's Blockchain
#Author: Léa Saxton
#Date: 19/02/2024

#Import Library
import pandas as pd 
import numpy as np
import os
import dash
from dash import Dash, dash_table, html,dcc
import dash_bootstrap_components as dbc
import plotly.express as px
from datetime import datetime as dt 
from geopy.geocoders import Nominatim
from dash.dependencies import Input, Output
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
import dash_cytoscape as cyto
import json

#Opening data and save it in pandas dataframe

with open('./tx_history_cheese.json') as file:
        data = json.load(file)
        df= pd.json_normalize(data, meta=['ProductID', 'PreviousProductID', 'RootProductID', 'Owner', 
        'ProductName', 'ProductType', 'Location', 'Weight', 'Temperature', 'UseByDate', 'AssetStatus',
        'TransferFrom', 'TransferTo', 'TransferWeight', 'EventTimestamp', 'EventBy', 'LinkedExperiments', 'Hash',
        'PreviousHash'])
        df = df.drop(["LinkedExperiments", "Hash", "PreviousHash", 'TransferFrom', 'TransferTo', 'TransferWeight', 'EventTimestamp'], axis=1)
        df = df.iloc[::-1]
        df.drop(df[(df["AssetStatus"] == 'Edited') | (df["AssetStatus"]=="Requested")].index, axis=0, inplace=True)
        df['Owner_type']= ['Producer','Deliverer','Manufacturer','Deliverer','Carrier','Deliverer','Retailer']
        df['EventTimestamp']=['2024-02-05','2024-02-08','2024-02-10', '2024-02-11','2024-02-12','2024-02-13', '2024-02-14']
        #print(df["AssetStatus"])
        # Convert location names to latitude and longitude coordinates
        geolocator = Nominatim(user_agent="sorfML_dashboard")
        df['location'] = df['Location'].apply(lambda x: geolocator.geocode(x))
        df['Latitude'] = df['location'].apply(lambda x: x.latitude if x else None)
        df['Longitude'] = df['location'].apply(lambda x: x.longitude if x else None)

        # Drop unnecessary columns
        df = df.drop(['location'], axis=1)

        df["Temperature"] = pd.to_numeric(df["Temperature"], errors="coerce")

        df["Weight"]=pd.to_numeric(df['Weight'], errors="coerce")

        #df['UseByDate']=['2024-02-29','2024-02-29','2024-02-20', '2024-02-20','2024-02-20','2024-02-20', '2024-02-20']
        #df['UseByDate']=['2024-02-24','2024-02-24','2024-02-24', '2024-02-24','2024-02-24','2024-02-24', '2024-02-24']


def is_constant_temperature(product):
    unique_temperatures = df['Temperature'].unique()
    if len(unique_temperatures) == 1:
        return True
    else:
        return False

products_with_inconstant_temperature = [product for product in df['ProductID'].unique() if not is_constant_temperature(product)]

def is_constant_weight(product):
    unique_weights = df["Weight"].unique()
    if len(unique_weights) == 1:
        return True
    else:
        return False

products_with_inconstant_weight = [product for product in df['ProductID'].unique() if not is_constant_weight(product)]

current_date = dt.now().date()
expired_products = [product for product in df['ProductID'].unique() if pd.to_datetime(df[df['ProductID'] == product]['UseByDate'].iloc[0]).date() <= current_date]

expired_products_locations = [
        (product, df[df['ProductID'] == product]['Location'].iloc[0]) 
        for product in df['ProductID'].unique() 
        if pd.to_datetime(df[df['ProductID'] == product]['UseByDate'].iloc[0]).date() <= current_date
    ]

# Convert each tuple to a string and join them together
expired_products_locations_str = [f"('{prod}', '{loc}')" for prod, loc in expired_products_locations]

#Initialise a dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

app.layout = dbc.Container(
    [
        dcc.Store(id='store', data=df.to_dict('records')),  # Store DataFrame as a list of dictionaries
        html.H1('Supply Chain Insight Dashboard', style={'color': 'white', 'font-family': 'Arial, sans-serif',
                                                        'text-align': 'center', 'font-size': '250%', 'font-weight': 'bold', 
                                                        'text-shadow':'-1px -1px 0 black, 1px -1px 0 black, -1px 1px 0 black, 1px 1px 0 black'}),
        html.Hr(),
        html.Div('Navigate Between Tabs To Explore Your Products Parameters', style={'color': 'white'}),        
        dbc.Alert(
            f"Warning: Temperature values for the following products are not constant: {', '.join(products_with_inconstant_temperature)}",
            id="alert",
            color="danger",
            dismissable=True,
            is_open=False 
        ),
        dbc.Alert(
            f"Warning: Weight values for the following products are not constant: {', '.join(products_with_inconstant_weight)}",
            id="alert_weight",
            color="danger",
            dismissable=True,
            is_open=False
        ),
        dbc.Alert(
            f"Warning: The following products have expired:{', '.join(expired_products_locations_str)}",
            id="alert_expired",
            color="danger",
            dismissable=True,
            is_open=False
        ),
        dbc.Alert(
            "No products have expired yet!",
            id="alert_not_expired",
            color="success",
            dismissable=True,
            is_open=False
        ),
        html.Div(id='main-tab-content', className='p-4'),

    ],
    fluid=True,
    style={'backgroundColor': '#6c757d'}
)

# Define callback to render the main content
@app.callback(
    Output('main-tab-content', 'children'),
    [Input('store', 'data')]
)
def render_main_content(data):
    if data is None:
        # Return a placeholder message or an empty div if no data is available
        return html.Div("No data available.")

    # Convert the stored data (list of dictionaries) back to a DataFrame
    df = pd.DataFrame(data)
    #To display map
    fig_map = px.scatter_geo(df, lat="Latitude", lon="Longitude",
                              hover_data=["ProductID", "Owner", "Location", "Weight", "Temperature", "UseByDate"],
                              projection="natural earth")
    fig_map.update_traces(marker=dict(color='red', size=10))  # Change color to red and size to 10
    fig_map.update_layout(title_x=0.5, title_text=f"Products Locations", title_font=dict(size=30),
                          paper_bgcolor='#adb5bd')
    #To display line graph for Temperature 
    fig_line = px.line(df, x='EventTimestamp', y='Temperature', hover_data=['ProductID','Owner', 'ProductName','Location'], 
    labels={'EventTimestamp':'Transfers Dates', 
            'Temperature':'Temperatures'})
    fig_line.update_layout(title_x=0.5, title_text='Products Temperatures across the Supply Chain', title_font=dict(size=20),
                          paper_bgcolor='#adb5bd', plot_bgcolor="#adb5bd")
    #To display bar chart for Weight
    fig_line2= px.line(df, x='EventTimestamp', y='Weight', hover_data=['ProductID', 'Owner', 'ProductName', 'Location'], 
    labels={'EventTimestamp':'Transfers Dates', 
            'Weight':'Weights'})
    fig_line2.update_layout(title_x= 0.5, title_text='Products Weights across the Supply Chain', title_font=dict(size=20), 
    paper_bgcolor='#adb5bd',plot_bgcolor="#adb5bd")
    #To Display Treemap chart 
    treemap_tab_layout = html.Div([
            dcc.Dropdown(
                id='treemap-dropdown',
                options=[
                    {'label':html.Span(['Temperature'], style={'color':'#374257','font-family':'Calibri, sans-serif'}), 'value': 'Temperature'},
                    {'label':html.Span(['Weight'], style={'color':'#374257','font-family':'Calibri, sans-serif'}), 'value': 'Weight'}
                ],
                value='Weight',  
                clearable=False,
                style={'backgroundColor': '#adb5bd','color':'#374257', 'font-family':'Calibri, sans-serif'}
            ),
            dcc.Graph(id='treemap-chart')
        ])

    return html.Div([
        dbc.Row([
        dbc.Col(dcc.Graph(figure=fig_map), width=6),
        dbc.Col(dcc.Graph(figure=fig_line), width=6)
    ],className="mb-3"), 
        dbc.Row([
            dbc.Col(treemap_tab_layout, width=6),
            dbc.Col(dcc.Graph(figure=fig_line2), width=6)
            
            ])
    ])

@app.callback(
    Output("alert", "is_open"),
    [Input("store", "data")]
)
def update_alert(data):
    inconsistent_products = [product for product in df['ProductID'].unique() if not is_constant_temperature(product)]
    return len(inconsistent_products) > 0

@app.callback(
    Output("alert_weight", "is_open"),
    [Input("store", "data")]
)
def weight_alert(data):
    inconsistent_products = [product for product in df['ProductID'].unique() if not is_constant_weight(product)]
    return len(inconsistent_products) > 0

@app.callback(
    Output("alert_expired", "is_open"),
    [Input("store", "data")]
)
def product_expired(data):
    expiry_dates = pd.to_datetime(df['UseByDate'].unique()).date
    current_date = dt.now().date()
    expired_products = [product for product in df['ProductID'].unique() if pd.to_datetime(df[df['ProductID'] == product]['UseByDate'].iloc[0]).date() <= current_date]
    return len(expired_products)>0

@app.callback(
    Output("alert_not_expired", "is_open"),
    [Input("store", "data")]
)
def product_not_expired(data):
    expiry_dates = pd.to_datetime(df['UseByDate'].unique()).date
    current_date = dt.now().date()
    not_expired_products = [
        product for product in df['ProductID'].unique() 
        if pd.to_datetime(df[df['ProductID'] == product]['UseByDate'].iloc[0]).date() >= current_date
    ]
    return len(not_expired_products) == len(df['ProductID'].unique())

@app.callback(
    Output('treemap-chart', 'figure'),
    [Input('treemap-dropdown', 'value')]
)
def update_treemap_chart(selected_value):
    if selected_value == 'Temperature':
        fig = px.treemap(df, path=[px.Constant("Products"), "ProductType","EventTimestamp", "Location", "Owner"], values="Temperature",
                         color="Temperature", color_continuous_scale='Blues')
        fig.update_layout(title="Treemap Chart for Temperature", title_font=dict(size=30),
                          plot_bgcolor="#adb5bd", paper_bgcolor='#adb5bd')
        fig.update_traces(marker=dict(cornerradius=5))
        return fig
    elif selected_value == 'Weight':
        fig = px.treemap(df, path=[px.Constant("Products"),"ProductType", "EventTimestamp", "Location", "Owner"], values="Weight",
                         color="Weight", color_continuous_scale='Blues')
        fig.update_layout(title="Treemap Chart for Weight", title_font=dict(size=30),
                          plot_bgcolor="#adb5bd", paper_bgcolor='#adb5bd')
        fig.update_traces(marker=dict(cornerradius=5))
        return fig

# Run the app
if __name__ == '__main__':
    port_number=8080
    print(f"Report Accessible at http://localhost:{port_number}")
    app.run_server(debug=True, host='localhost', port=port_number)


warnings.filterwarnings("ignore", category=FutureWarning, module="plotly")

# Start the Dash app in local development mode
if __name__ == '__main__':
    port_number=8080
    print(f"Report Accessible at http://localhost:{port_number}")
    app.run_server(debug=True, host='localhost', port=port_number)