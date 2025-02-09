import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from pymongo import MongoClient
import logging
import os
import pandas as pd
from datetime import datetime, timedelta

# Setup Logging for Airflow
log_directory = 'C:/Users/Faisal/Desktop/errors/'
if not os.path.exists(log_directory):
    os.makedirs(log_directory)

logger = logging.getLogger()
file_handler = logging.FileHandler('C:/Users/Faisal/Desktop/errors/pipeline.log2')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# MongoDB URI
uri = "mongodb+srv://faysalelawar:pb6LB2kBPQ5Be5vN@dataengineeringcluster.61mrj.mongodb.net/?retryWrites=true&w=majority&appName=DataEngineeringCluster"

# Weather API URL and Key (replace with your actual API key)
WEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"
API_KEY = "3cb535b45b20509643dcb1f06587f284"  # Replace with your OpenWeatherMap API key

# Function to get weather data from API
def fetch_weather_data(city, api_key=API_KEY):
    base_url = f"{WEATHER_API_URL}?q={city}&appid={api_key}"
    response = requests.get(base_url)
    data = response.json()

    if response.status_code == 200:
        # Extract temperature, humidity, and weather description
        temperature = data['main']['temp'] - 273.15  # Convert from Kelvin to Celsius
        humidity = data['main']['humidity']
        weather_description = data['weather'][0]['description']
        return temperature, humidity, weather_description
    else:
        logger.error(f"Weather data fetch failed for city: {city}. Status code: {response.status_code}")
        return None, None, None

# Extract function to load data from a source (e.g., CSV file)
def extract_data(**kwargs):
    try:
        # Read the CSV file containing sales data
        url = "https://raw.githubusercontent.com/falawar7/AAI_634O/refs/heads/main/Week3/Project/sales_data_FEB2025.csv"
        sales_data = pd.read_csv(url)
        
        # Push the sales_data to XCom for downstream tasks
        kwargs['ti'].xcom_push(key='sales_data', value=sales_data)
        
        # Print the extracted data (this will be logged in the Airflow UI)
        logger.info("Extracted Data:")
        logger.info(sales_data.head())
    except Exception as e:
        logger.error(f"ETL task failed: {str(e)}")
        raise

# Function to test API connection
def test_api_connection(**kwargs):
    try:
        # Test the API connection by fetching weather data for a sample city
        sample_city = "New York"
        temp, humidity, description = fetch_weather_data(sample_city, API_KEY)
        
        if temp is not None and humidity is not None and description is not None:
            logger.info(f"API Connection Successful! Sample Data for {sample_city}:")
            logger.info(f"Temperature: {temp}°C, Humidity: {humidity}%, Description: {description}")
        else:
            logger.error("API Connection Test Failed: No data returned.")
            raise Exception("API Connection Test Failed: No data returned.")
    except Exception as e:
        logger.error(f"API Connection Test Failed: {str(e)}")
        raise

# Define the transform task
def transform_data(**kwargs):
    try:
        # Pull the extracted data from XCom
        sales_data = kwargs['ti'].xcom_pull(key='sales_data', task_ids='extract_data')
        
        # Loop through each row of the sales_data DataFrame and fetch weather data
        for index, row in sales_data.iterrows():
            # Fetch weather data based on the store location (city)
            temp, humidity, description = fetch_weather_data(row["store_location"], API_KEY)

            # Update the DataFrame with new weather columns
            sales_data.at[index, "Temperature (°C)"] = temp
            sales_data.at[index, "Humidity (%)"] = humidity
            sales_data.at[index, "Weather Description"] = description

        # Push the transformed data to XCom for downstream tasks
        kwargs['ti'].xcom_push(key='transformed_data', value=sales_data)
        
        # Print the transformed data (this will be logged in the Airflow UI)
        logger.info("Transformed Data:")
        logger.info(sales_data.head())
        return sales_data
    except Exception as e:
        logger.error(f"ETL task failed: {str(e)}")
        raise

# Load function to insert transformed data into MongoDB
def load_data(**kwargs):
    try:
        # Pull the transformed data from XCom
        transformed_data = kwargs['ti'].xcom_pull(key='transformed_data', task_ids='transform_data')
        
        # Connect to MongoDB
        client = MongoClient(uri)
        client.admin.command('ping')  # Test connection
        logger.info("Successfully connected to MongoDB!")

        db = client['sales_db']
        collection = db["sales_weather"]

        # Convert DataFrame to dictionary and insert into MongoDB
        sales_data_dict = transformed_data.to_dict("records")
        result = collection.insert_many(sales_data_dict)

        logger.info(f"Total records added: {len(sales_data_dict)}")
        print(f"Total records added: {len(sales_data_dict)}")
    except Exception as e:
        logger.error(f"Error in data loading: {str(e)}")
        raise

# Define default arguments for the DAG
default_args = {
    'owner': 'airflow',
    'start_date': datetime(2025, 2, 8),
    'retries': 2,
}

# Define the DAG
dag = DAG(
    'Project_FE_DE',
    default_args=default_args,
    schedule='0 6 * * *',  # Run every day at 6:00 AM
)
# Define the tasks in the DAG
extract_task = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    dag=dag
)

api_test_task = PythonOperator(
    task_id='test_api_connection',
    python_callable=test_api_connection,
    dag=dag
)

transform_task = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    dag=dag
)

load_task = PythonOperator(
    task_id='load_data',
    python_callable=load_data,
    dag=dag
)

# Set the task dependencies
extract_task >> api_test_task >> transform_task >> load_task