def calculate_risks(weather_data, day_index):
    daily = weather_data['daily']
    
    # Extract relevant data
    temp_max = daily['temperature_2m_max'][day_index]
    precip = daily['precipitation_sum'][day_index]
    wind = daily['windspeed_10m_max'][day_index]
    
    # Calculate risks (0-100 scale)
    flood_risk = min(100, precip * 1.5) if precip > 30 else 0
    storm_risk = min(100, (wind - 25) * 3) if wind > 25 else 0
    wildfire_risk = min(100, (temp_max - 30) * 2) if temp_max > 30 and precip < 5 else 0
    
    return {
        'flood_risk': flood_risk,
        'storm_risk': storm_risk,
        'wildfire_risk': wildfire_risk,
    }