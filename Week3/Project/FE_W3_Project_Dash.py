#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import dash
from dash import dcc, html
import plotly.express as px
import pandas as pd
from pymongo import MongoClient
from dash.dependencies import Input, Output

# Connect to MongoDB
client = MongoClient("mongodb+srv://faysalelawar:pb6LB2kBPQ5Be5vN@dataengineeringcluster.61mrj.mongodb.net/?retryWrites=true&w=majority&appName=DataEngineeringCluster")
db = client["sales_db"]
#updated Colelction imported using Apache Airflow 
collection = db["sales_weather"]

# Fetch data from MongoDB
#removing id column
df = pd.DataFrame(list(collection.find({}, {"_id": 0}))) 

# Convert 'date' column to datetime format for proper time-series visualization
df["date"] = pd.to_datetime(df["date"])

# Scatter plot: Temperature vs. Sales
scatter_temp = px.scatter(df, 
                          x="Temperature (°C)",  
                          y="sales_amount",      
                          color="store_location", 
                          title="Sales vs. Temperature",
                          hover_data=["store_location", "Humidity (%)", "sales_amount"])

# Scatter plot: Humidity vs. Sales 
scatter_humidity = px.scatter(df, 
                               x="Humidity (%)",  
                               y="sales_amount",      
                               color="store_location", 
                               title="Sales vs. Humidity",
                               hover_data=["store_location", "Temperature (°C)", "sales_amount"])

# Bar chart: Total Sales per Store Location
sales_per_location = df.groupby("store_location")["sales_amount"].sum().reset_index()
bar_location = px.bar(sales_per_location, 
                      x="store_location", 
                      y="sales_amount", 
                      title="Total Sales per Store Location",
                      color="store_location",
                      hover_data=["sales_amount"])

# Bar chart: Total Sales per Weather Condition 
sales_per_weather = df.groupby("Weather Description")["sales_amount"].sum().reset_index()
bar_weather = px.bar(sales_per_weather, 
                     x="Weather Description", 
                     y="sales_amount", 
                     title="Total Sales by Weather Condition",
                     color="Weather Description",
                     hover_data=["sales_amount"])

# Line chart: Sales per Day for Each Store Location (with hover)
sales_per_day = df.groupby(["date", "store_location", "Weather Description", "Humidity (%)", "Temperature (°C)"])["sales_amount"].sum().reset_index()
line_sales = px.line(sales_per_day, 
                     x="date", 
                     y="sales_amount", 
                     color="store_location",
                     title="Daily Sales Trends by Store Location",
                     markers=True,  # Adds points on the line
                     hover_data=["store_location", "sales_amount", "Humidity (%)", "Temperature (°C)"])

# Bar chart: Most Selling Products
sales_per_product = df.groupby("product_id")["sales_amount"].sum().reset_index()
sales_per_product = sales_per_product.sort_values(by="sales_amount", ascending=False).head(10)  # Get top 10 products

# Add average weather data for hover
avg_weather_data = df.groupby("product_id")[["Temperature (°C)", "Humidity (%)"]].mean().reset_index()

# Merge the average weather data with the product sales data
sales_per_product = pd.merge(sales_per_product, avg_weather_data, on="product_id", how="left")

bar_products = px.bar(sales_per_product, 
                      x="product_id", 
                      y="sales_amount", 
                      title="Top 10 Most Selling Products",
                      color="product_id",
                      hover_data=["sales_amount", "Temperature (°C)", "Humidity (%)"])

# Dash app layout
app = dash.Dash(__name__)

# Layout of the dashboard
app.layout = html.Div(children=[
    html.H1("Sales & Weather Analysis"),
    
    html.H3("Sales vs. Temperature"),
    dcc.Graph(figure=scatter_temp),

    html.H3("Sales vs. Humidity"),
    dcc.Graph(figure=scatter_humidity),

    html.H3("Total Sales per Store Location"),
    dcc.Graph(figure=bar_location),

    html.H3("Total Sales by Weather Condition"),
    dcc.Graph(figure=bar_weather),

    html.H3("Daily Sales Trends by Store Location"),
    dcc.Graph(figure=line_sales),

    # Dropdown menu for selecting store location only for the "Top 10 Most Selling Products" graph
    dcc.Dropdown(
        id='store-location-dropdown',
        options=[{'label': location, 'value': location} for location in df['store_location'].unique()],
        value=df['store_location'].unique()[0],  
        style={'width': '50%'}
    ),

    html.H3("Top Selling Products"),
    dcc.Graph(id='bar-products'),
])

# Update the "Top Selling Products" graph based on the selected store location
@app.callback(
    Output('bar-products', 'figure'),
    [Input('store-location-dropdown', 'value')]
)
def update_top_products(selected_location):
    # Filter the dataframe based on selected location
    filtered_df = df[df['store_location'] == selected_location]

    # Bar chart: Most Selling Products (with hover)
    sales_per_product = filtered_df.groupby("product_id")["sales_amount"].sum().reset_index()
    sales_per_product = sales_per_product.sort_values(by="sales_amount", ascending=False).head(10)  # Get top 10 products

    # Add average weather data for hover (no weather description)
    avg_weather_data = filtered_df.groupby("product_id")[["Temperature (°C)", "Humidity (%)"]].mean().reset_index()

    # Merge the average weather data with the product sales data
    sales_per_product = pd.merge(sales_per_product, avg_weather_data, on="product_id", how="left")

    bar_products = px.bar(sales_per_product, 
                          x="product_id", 
                          y="sales_amount", 
                          title="Top 10 Most Selling Products",
                          color="product_id",
                          hover_data=["sales_amount", "Temperature (°C)", "Humidity (%)"])

    return bar_products

if __name__ == "__main__":
    app.run_server(debug=True)

