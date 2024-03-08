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

# Import networkgraph utils
from networkgraph_util import create_networkgraph_inputdata, get_nodes, set_node_colours, get_edges, set_networkgraph_default_stylesheet, set_networkgraph_tab_layout

# Show content of call back variables
def show_content(content):
    print(content) 

#Opening data and save it in pandas dataframe
with open('./tx_monitor_milk_V2.json.txt') as file:
        data_json = json.load(file)
        # Pick up 'txHistory' object
        data_txhistory = data_json['txHistory']

        # Convert it into data frame
        df_txhistory = pd.json_normalize(data_txhistory,
            meta = [
                'ProductID',
                'PreviousProductID',
                'RootProductID',
                'Owner',
                'ProductName',
                'ProductType',
                'Location',
                'Weight',
                'Temperature',
                'UseByDate',
                'AssetStatus',
                'TransferFrom',
                'TransferTo',
                'TransferWeight',
                'EventTimestamp',
                'EventBy',
                'LinkedExperiments',
                'Hash',
                'PreviousHash'
            ]
        )
        df_txhistory = df_txhistory.drop(
            [
                'LinkedExperiments',
                'Hash',
                'PreviousHash',
                'TransferFrom',
                'TransferTo',
                'TransferWeight',
                'EventTimestamp'
            ],
            axis=1
        )
        df_txhistory = df_txhistory.iloc[::-1]
        df_txhistory.drop(df_txhistory[(df_txhistory['AssetStatus']=='Edited') | (df_txhistory['AssetStatus']=='Requested')].index, axis=0, inplace=True)

        # It should be dynamic!!! It should be dynamic!!! It should be dynamic!!! It should be dynamic!!! It should be dynamic!!!
        df_txhistory['EventTimestamp'] = ['2024-02-05','2024-02-08','2024-02-10','2024-02-11','2024-02-12','2024-02-13','2024-02-14']
        # It should be dynamic!!! It should be dynamic!!! It should be dynamic!!! It should be dynamic!!! It should be dynamic!!!

        #print(df_txhistory['AssetStatus'])
        # Convert location names to latitude and longitude coordinates
        geolocator = Nominatim( user_agent = 'sorfML_dashboard' )
        df_txhistory['location' ] = df_txhistory['Location'].apply(lambda x: geolocator.geocode( x )   )
        df_txhistory['Latitude' ] = df_txhistory['location'].apply(lambda x: x.latitude  if x else None)
        df_txhistory['Longitude'] = df_txhistory['location'].apply(lambda x: x.longitude if x else None)

        # Drop unnecessary columns
        df_txhistory = df_txhistory.drop(['location'], axis=1)

        df_txhistory['Temperature'] = pd.to_numeric( df_txhistory['Temperature'], errors='coerce')

        df_txhistory['Weight'] = pd.to_numeric(df_txhistory['Weight'], errors='coerce')

        # Modified by Shintaro Kinoshita:
        # Then, create another input data for network graph
        data_networkgraph = data_json['branches']

        # Pre-process the data for network graph visualisation
        data_networkgraph = create_networkgraph_inputdata(data_networkgraph)
        print('Fetched network graph data')
        #print(data_networkgraph)

        # Extract network grapgh nodes info
        data_nodes = get_nodes(data_networkgraph)
        print('Extracted network graph nodes')
        #print(data_nodes)

        # Get node colours
        data_nodes = set_node_colours(data_nodes)
        print('Set node colours')
        #print(data_nodes)

        # Get edges info
        data_edges = get_edges(data_networkgraph)
        print('Get edge info')
        #print(data_edges)

        # Get network graph default style sheet
        networkgraph_stylesheet = set_networkgraph_default_stylesheet()
        print('Fetched default network graph style sheet')
        #print(networkgraph_stylesheet)

        # Get netwok graph tab app page style
        networkgraph_tab_layout = set_networkgraph_tab_layout()
        print('Fetched network graph tab layout')
        print(networkgraph_tab_layout)



def is_constant_temperature(product):
    unique_temperatures = df_txhistory['Temperature'].unique()
    if len(unique_temperatures) == 1:
        return True
    else:
        return False

products_with_inconstant_temperature = [product for product in df_txhistory['ProductID'].unique() if not is_constant_temperature(product)]

def is_constant_weight(product):
    unique_weights = df_txhistory['Weight'].unique()
    if len(unique_weights) == 1:
        return True
    else:
        return False

products_with_inconstant_weight = [product for product in df_txhistory['ProductID'].unique() if not is_constant_weight(product)]

current_date = dt.now().date()
expired_products = [product for product in df_txhistory['ProductID'].unique() if pd.to_datetime(df_txhistory[df_txhistory['ProductID'] == product]['UseByDate'].iloc[0]).date() <= current_date]

expired_products_locations = [
        (product, df_txhistory[df_txhistory['ProductID'] == product]['Location'].iloc[0]) 
        for product in df_txhistory['ProductID'].unique() 
        if pd.to_datetime(df_txhistory[df_txhistory['ProductID'] == product]['UseByDate'].iloc[0]).date() <= current_date
    ]

# Convert each tuple to a string and join them together
expired_products_locations_str = [f"('{prod}', '{loc}')" for prod, loc in expired_products_locations]

#Initialise a dash app
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)

app.layout = dbc.Container(
    [
        dcc.Store(id='store', data=df_txhistory.to_dict('records')),  # Store DataFrame as a list of dictionaries
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
        html.Div('Naviguate Between Tabs To Explore Your Products Parameters', style={'color': 'white'}),
        dbc.Tabs(
            [
                dbc.Tab(label = 'Main panels',   tab_id = 'tab1',   label_style={"color": "black"}),
                dbc.Tab(label = 'Network graph', tab_id = 'tab2',   label_style={"color": "black"}),
            ],
            id = 'main-tabs',
            active_tab = 'tab1',
        ),
        html.Div(id='main-tab-content', className='p-4'),

    ],
    fluid=True,
    style={'backgroundColor': '#6c757d'}
)

# Define callback to render the main content
@app.callback(
    Output('main-tab-content', 'children'),
    [Input('store', 'data'), Input('main-tabs', 'active_tab')]
)
def render_main_content(data, active_tab):
    if active_tab == 'tab1':
        # Return a placeholder message or an empty div if no data is available
        if data is None : return html.Div('No data available.')

        # Convert the stored data (list of dictionaries) back to a DataFrame
        df_txhistory = pd.DataFrame(data)
        #To display map
        fig_map = px.scatter_geo(
            df_txhistory,
            lat        = 'Latitude',
            lon        = 'Longitude',
            hover_data = ['ProductID', 'Owner', 'Location', 'Weight', 'Temperature', 'UseByDate'],
            projection = 'natural earth'
        )
        # Change color to red and size to 10
        fig_map.update_traces(marker=dict(color='red', size=10))
        fig_map.update_layout(
            title_x       = 0.5,
            title_text    = f'Products Locations',
            title_font    = dict(size=30),
            paper_bgcolor = '#adb5bd'
        )
        #To display line graph for Temperature 
        fig_line = px.line(
            df_txhistory,
            x          = 'EventTimestamp',
            y          = 'Temperature',
            hover_data = ['ProductID','Owner', 'ProductName','Location'],
            labels     = {'EventTimestamp':'Transfers Dates', 'Temperature':'Temperatures'}
        )
        # Note note note blah blah blah blah 
        fig_line.update_layout(
            title_x       = 0.5,
            title_text    = 'Products Temperatures across the Supply Chain',
            title_font    = dict(size=20),
            paper_bgcolor = '#adb5bd',
            plot_bgcolor  = '#adb5bd'
        )
        # To display bar chart for Weight
        fig_line2 = px.line(
            df_txhistory,
            x          = 'EventTimestamp',
            y          = 'Weight',
            hover_data = ['ProductID', 'Owner', 'ProductName', 'Location'], 
            labels     = {'EventTimestamp':'Transfers Dates', 'Weight':'Weights'}
        )
        # Note note note blah blah blah
        fig_line2.update_layout(
            title_x       = 0.5,
            title_text    = 'Products Weights across the Supply Chain',
            title_font    = dict(size=20),
            paper_bgcolor = '#adb5bd',
            plot_bgcolor  = '#adb5bd'
        )
        #To Display Treemap chart 
        treemap_tab_layout = html.Div([
                dcc.Dropdown(
                    id     = 'treemap-dropdown',
                    options = [
                        {'label':html.Span(['Temperature'], style={'color':'#374257','font-family':'Calibri, sans-serif'}), 'value': 'Temperature'},
                        {'label':html.Span(['Weight'], style={'color':'#374257','font-family':'Calibri, sans-serif'}), 'value': 'Weight'}
                    ],
                    value     = 'Weight',
                    clearable = False,
                    style     = {'backgroundColor': '#adb5bd','color':'#374257', 'font-family':'Calibri, sans-serif'}
                ),
            dcc.Graph(id='treemap-chart')
        ])

        return html.Div([
            dbc.Row([
                dbc.Col(dcc.Graph(figure=fig_map), width=6),
                dbc.Col(dcc.Graph(figure=fig_line), width=6)
            ],className='mb-3'), 
            dbc.Row([
                dbc.Col(treemap_tab_layout, width=6),
                dbc.Col(dcc.Graph(figure=fig_line2), width=6)
            ])
        ])

    # If tab2, show network graph
    elif active_tab == 'tab2':
        return html.Div([
        # Main Cytoscape network graph window
        html.Div(
            cyto.Cytoscape(
            id         = 'network-gragh',
            layout     = { 'name' : 'breadthfirst', 'roots' : '[ previous_hash *= "GenesisBlock" ]' },
            elements   = data_edges + data_nodes,
            stylesheet = networkgraph_stylesheet,
            style      = networkgraph_tab_layout[ 'networkgraph-plot' ]
            )
        ),
        # html.Div for sidebar menu
        html.Div(
            [
                # Network graph style dropdown
                # THIS CODE BLOCK IS NOT USED ANYMORE!!!
                #html.P( 'Graph style', style = styles[ 'dropdown-title' ] ),
                #html.Div(
                #    dcc.Dropdown(
                #        id      = 'networkstyle-dropdown',
                #        options = [
                #            { 'label' : 'Random',       'value' : 'random'       },
                #            { 'label' : 'Grid',         'value' : 'grid'         },
                #            { 'label' : 'Circle',       'value' : 'circle'       },
                #            { 'label' : 'Concentric',   'value' : 'concentric'   },
                #            { 'label' : 'Breadthfirst', 'value' : 'breadthfirst' }
                #        ],
                #        value       = 'breadthfirst',
                #        clearable   = False,
                #        style       = networkgraph_tab_layout[ 'dropdown' ]
                #    )
                #),
                # Node size option dropdown
                html.P( 'Node size', style = networkgraph_tab_layout[ 'dropdown-title' ] ),
                html.Div(
                    dcc.Dropdown(
                        id      = 'nodesize-dropdown',
                        options = [
                            { 'label' : 'Weight',      'value' : 'data(node_size_weight)'      },
                            { 'label' : 'Temperature', 'value' : 'data(node_size_temperature)' }
                        ],
                        value     = 'data(node_size_weight)',
                        clearable = False,
                        style     = networkgraph_tab_layout[ 'dropdown' ]
                    )
                ),
                # Node colour option dropdown
                html.P( 'Node colour', style = networkgraph_tab_layout[ 'dropdown-title' ] ),
                html.Div(
                    dcc.Dropdown(
                        id      = 'nodecolour-dropdown',
                        options = [
                            { 'label' : 'Owner',        'value' : 'data(colour_owner)'    },
                            { 'label' : 'Product name', 'value' : 'data(colour_product)'  },
                            { 'label' : 'Location',     'value' : 'data(colour_location)' }
                        ],
                        value     = 'data(colour_owner)',
                        clearable = False,
                        style     = networkgraph_tab_layout[ 'dropdown' ]
                    )
                ),
                # Temperature threshold highlight. This is number input but
                # the style is the same as dropdown
                html.P( 'Temperature filter', style = networkgraph_tab_layout[ 'dropdown-title' ] ),
                html.Div(
                    dcc.Input(
                        id          = 'filtertemperature-input',
                        type        = 'number',
                        placeholder = 'Temperature / ℃',
                        style       = networkgraph_tab_layout[ 'number-input' ]
                    )
                ),
                # Weight threshold highlight. This is number input but
                # the style is the same as dropdown
                html.P( 'Weight filter', style = networkgraph_tab_layout[ 'dropdown-title' ] ),
                html.Div(
                    dcc.Input(
                        id          = 'filterweight-input',
                        type        = 'number',
                        placeholder = 'Weight / Kg',
                        style       = networkgraph_tab_layout[ 'number-input' ]
                    )
                ),
                # Owner organisation filter dropdown
                #html.P( 'Owner filter', style = networkgraph_tab_layout[ 'dropdown-title' ] ),
                #html.Div(
                #    dcc.Dropdown(
                #        id        = 'ownerfilter-dropdown',
                #        options   = owner_dropdown,
                #        clearable = True,
                #        style     = networkgraph_tab_layout[ 'dropdown' ]
                #    )
                #),
                ## Product name filter dropdown
                #html.P( 'Product filter', style = networkgraph_tab_layout[ 'dropdown-title' ] ),
                #html.Div(
                #    dcc.Dropdown(
                #        id        = 'productfilter-dropdown',
                #        options   = product_dropdown,
                #        clearable = True,
                #        style     = networkgraph_tab_layout[ 'dropdown' ]
                #    )
                #),
                # Network graph reset button
                html.P(
                    'If the filter does not seem to work, push Reset Filter below and try again.',
                    style = networkgraph_tab_layout[ 'reset-note' ]
                ),
                html.Button(
                    'Reset Filter',
                    id       = 'reset-button',
                    style    = networkgraph_tab_layout[ 'reset-button' ],
                    n_clicks = 0
                )
            ],
            style = networkgraph_tab_layout[ 'sidebar-menu' ]
        ),
        # Show block content in TOP-LEFT box
        html.Pre(
            id       = 'block-content',
            children = 'Block content shows up here.',
            style    = networkgraph_tab_layout[ 'block-content' ]
        )
    ])



@app.callback(
    Output("alert", "is_open"),
    [Input("store", "data")]
)
def update_alert(data):
    inconsistent_products = [product for product in df_txhistory['ProductID'].unique() if not is_constant_temperature(product)]
    return len(inconsistent_products) > 0

@app.callback(
    Output("alert_weight", "is_open"),
    [Input("store", "data")]
)
def weight_alert(data):
    inconsistent_products = [product for product in df_txhistory['ProductID'].unique() if not is_constant_weight(product)]
    return len(inconsistent_products) > 0

@app.callback(
    Output("alert_expired", "is_open"),
    [Input("store", "data")]
)
def product_expired(data):
    expiry_dates = pd.to_datetime(df_txhistory['UseByDate'].unique()).date
    current_date = dt.now().date()
    expired_products = [product for product in df_txhistory['ProductID'].unique() if pd.to_datetime(df_txhistory[df_txhistory['ProductID'] == product]['UseByDate'].iloc[0]).date() <= current_date]
    return len(expired_products)>0

@app.callback(
    Output("alert_not_expired", "is_open"),
    [Input("store", "data")]
)
def product_not_expired(data):
    expiry_dates = pd.to_datetime(df_txhistory['UseByDate'].unique()).date
    current_date = dt.now().date()
    not_expired_products = [
        product for product in df_txhistory['ProductID'].unique() 
        if pd.to_datetime(df_txhistory[df_txhistory['ProductID'] == product]['UseByDate'].iloc[0]).date() >= current_date
    ]
    return len(not_expired_products) == len(df_txhistory['ProductID'].unique())

@app.callback(
    Output('treemap-chart', 'figure'),
    [Input('treemap-dropdown', 'value')]
)
def update_treemap_chart(selected_value):
    if selected_value == 'Temperature':
        fig = px.treemap(df_txhistory, path=[px.Constant("Products"), "ProductType","EventTimestamp", "Location", "Owner"], values="Temperature",
                         color="Temperature", color_continuous_scale='Blues')
        fig.update_layout(title="Treemap Chart for Temperature", title_font=dict(size=30),
                          plot_bgcolor="#adb5bd", paper_bgcolor='#adb5bd')
        fig.update_traces(marker=dict(cornerradius=5))
        return fig
    elif selected_value == 'Weight':
        fig = px.treemap(df_txhistory, path=[px.Constant("Products"),"ProductType", "EventTimestamp", "Location", "Owner"], values="Weight",
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