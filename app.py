import pandas as pd
import numpy as np
import pickle
import json
import requests
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def fetch_data(start_date, end_date):
    # Define the API endpoint URL
    url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/42182099999/{start_date}/{end_date}?unitGroup=metric&include=days&key=B443CQFJ9K7DJ3ARVCA96EGK6&contentType=json&elements=datetime,pm2p5,pm10,tempmin,tempmax,temp,precip"

    # Make the API request
    response = requests.get(url)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        # Parse the JSON response
        data = response.json()
        # Extract the "days" list from the response
        days_list = data.get('days', [])
        # Sort the "days" list in descending order based on datetime
        sorted_days = sorted(days_list, key=lambda x: x['datetime'], reverse=True)
        return sorted_days
    else:
        raise HTTPException(status_code=response.status_code, detail=f"API request failed with status code {response.status_code}")


# Load the trained model from the .pkl file
def load_model(model_path):
    with open(model_path, 'rb') as file:
        model = pickle.load(file)
    return model

# Function to preprocess JSON data into a format suitable for prediction
def preprocess_input_data(json_data, pollutant):
    # Initialize lists to store extracted feature values
    tavg_values = []
    tmin_values = []
    tmax_values = []
    prcp_values = []
    pm_lag_values = []
    input_data = []

    # Process each entry in the JSON data
    for entry in json_data:
        tavg_values.append(entry['temp'])
        tmin_values.append(entry['tempmin'])
        tmax_values.append(entry['tempmax'])
        prcp_values.append(entry['precip'])
        
        # Check if specified pollutant is present (for lagged values)
        if pollutant in entry:
            pm_lag_values.append(entry[pollutant])

    # Prepare input data for prediction using the last 5 days
    for i in range(0,6):
        input_data.append(tavg_values[i])
        input_data.append(tmin_values[i])
        input_data.append(tmax_values[i])
        input_data.append(prcp_values[i])

        if i != 0:
            input_data.append(pm_lag_values[i-1])

    return np.array(input_data).reshape(1, -1)  # Reshape to a single sample array

# Function to make predictions using the loaded model
def predict_values(model, input_data):
    predicted_values = model.predict(input_data)
    return predicted_values[0]  # Return the predicted values (assuming single prediction)

# Load the trained models
model_pm25_path = 'model/pm2p5_model.pkl'
model_pm10_path = 'model/pm10_model.pkl'
trained_model_pm25 = load_model(model_pm25_path)
trained_model_pm10 = load_model(model_pm10_path)



@app.get("/extract/")
def get_weather(date: str = None):
    if date is None:
        current_date_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        current_date_str = date
    five_days_earlier_str = (datetime.strptime(current_date_str, '%Y-%m-%d') - timedelta(days=5)).strftime('%Y-%m-%d')
    
    try:
        weather_data = fetch_data(five_days_earlier_str, current_date_str)
        if weather_data:
            # Remove pm2.5 and pm10 values for the latest date (first entry in sorted list)
            weather_data[0].pop('pm2p5', None)
            weather_data[0].pop('pm10', None)
             # Define the output file path
            output_file = 'sorted_days.json'
    
            # Write the modified sorted "days" list to a JSON file
            with open(output_file, 'w') as json_file:
                json.dump(weather_data, json_file, indent=4)
            return weather_data
        else:
            raise HTTPException(status_code=404, detail="Weather data not found")
    except HTTPException as e:
        raise e


# API endpoint to predict PM values
@app.get("/predict/")
async def predict_pm_values(pm_type: str):
    if pm_type not in ['pm2p5', 'pm10']:
        raise HTTPException(status_code=400, detail="Invalid pollutant type. Use 'pm2p5' or 'pm10'.")
    
    # Load JSON input data from file
    with open('sorted_days.json', 'r') as file:
        json_data = json.load(file)

    # Preprocess JSON data for the specified pollutant
    input_data = preprocess_input_data(json_data, pm_type)

    # Use the appropriate model to predict PM values
    if pm_type == 'pm2p5':
        predicted_value = predict_values(trained_model_pm25, input_data)
    elif pm_type == 'pm10':
        predicted_value = predict_values(trained_model_pm10, input_data)

    return {"pollutant": pm_type, "predicted_value": round(predicted_value,2)}

@app.get("/items/")
async def read_item():
    # Load JSON input data from file
    with open('sorted_days.json', 'r') as file:
        json_data = json.load(file)

    return json_data

@app.get()
async def greet():
    return {"Hello! Developer"}
