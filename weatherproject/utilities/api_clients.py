import requests
from datetime import datetime, timedelta
import os
from django.conf import settings

class OpenWeatherClient:
    BASE_URL = os.getenv('OPENWEATHER_BASE_URL', 'https://api.openweathermap.org/data/3.0/')
    
    def __init__(self):
        self.api_key = os.getenv('OPENWEATHER_API_KEY')
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY not set in environment variables")

    def get_current_weather(self, lat, lon):
        response = requests.get(
            f"{self.BASE_URL}onecall",
            params={
                'lat': lat,
                'lon': lon,
                'exclude': 'minutely,hourly,daily,alerts',
                'appid': self.api_key,
                'units': 'metric'
            }
        )
        data = response.json()
        return {
            'timestamp': datetime.fromtimestamp(data['current']['dt']),
            'temperature': data['current']['temp'],
            'humidity': data['current']['humidity'],
            'wind_speed': data['current']['wind_speed'] * 3.6,  # Convert m/s to km/h
            'precipitation': data['current'].get('rain', {}).get('1h', 0),
            'weather_code': self._convert_weather_code(data['current']['weather'][0]['id']),
        }

    def get_16_day_forecast(self, lat, lon):
        """OpenWeatherMap provides 16-day forecasts (including today)"""
        response = requests.get(
            f"{self.BASE_URL}forecast/daily",
            params={
                'lat': lat,
                'lon': lon,
                'cnt': 16,  # 16 days (including today)
                'appid': self.api_key,
                'units': 'metric'
            }
        )
        data = response.json()
        forecasts = []
        
        for day in data['list']:
            forecasts.append({
                'timestamp': datetime.fromtimestamp(day['dt']),
                'temperature': (day['temp']['max'] + day['temp']['min']) / 2,
                'humidity': day['humidity'],
                'wind_speed': day['speed'] * 3.6,  # Convert m/s to km/h
                'precipitation': day.get('rain', 0),
                'weather_code': self._convert_weather_code(day['weather'][0]['id']),
                'is_forecast': True,
                **self._calculate_risks(day)
            })
        return forecasts

    def _convert_weather_code(self, owm_code):
        """Convert OpenWeatherMap weather codes to our system"""
        # Thunderstorm
        if 200 <= owm_code < 300:
            return 5  # THUNDERSTORM
        # Drizzle/Rain
        elif 300 <= owm_code < 600:
            return 3  # RAIN
        # Snow
        elif 600 <= owm_code < 700:
            return 4  # SNOW
        # Atmosphere (Fog, etc.)
        elif 700 <= owm_code < 800:
            return 6  # FOG
        # Clear
        elif owm_code == 800:
            return 0  # CLEAR
        # Clouds
        else:
            return 2  # CLOUDY

    def _calculate_risks(self, day_data):
        """Calculate disaster risks from forecast data"""
        risks = {
            'flood_risk': 0,
            'storm_risk': 0,
            'wildfire_risk': 0
        }
        
        # Flood risk (mm of precipitation)
        precip = day_data.get('rain', 0)
        if precip > 30:
            risks['flood_risk'] = min(100, precip * 1.5)
        
        # Storm risk (wind speed in km/h)
        wind_speed = day_data['speed'] * 3.6
        if wind_speed > 25:
            risks['storm_risk'] = min(100, (wind_speed - 25) * 3)
        
        # Wildfire risk (high temp + low humidity)
        temp_max = day_data['temp']['max']
        humidity = day_data['humidity']
        if temp_max > 30 and humidity < 30:
            risks['wildfire_risk'] = min(100, (temp_max - 30) * 2 + (30 - humidity))
            
        return risks