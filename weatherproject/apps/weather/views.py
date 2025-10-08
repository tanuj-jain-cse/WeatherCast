from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from datetime import timedelta
from .models import WeatherData, Location, UserSearchHistory
from .serializers import WeatherDataSerializer, LocationSerializer 
import requests
from django.conf import settings
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
import warnings
warnings.filterwarnings('ignore')

class LocationListAPI(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        """List all locations stored in the database"""
        locations = Location.objects.all()
        serializer = LocationSerializer(locations, many=True)
        return Response(serializer.data)

class CurrentWeatherAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, city_name):
        # Validate city_name parameter
        if not city_name or not city_name.strip():
            return Response(
                {"error": "City name is required and cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Clean the city name
        city_name = city_name.strip().lower()
        
        try:
            # Fetch fresh data directly from OpenWeatherMap
            weather_data = self._fetch_weather_data(city_name)
            
            # Optionally save to database if needed
            if request.user.is_authenticated:
                self._save_to_database(city_name, weather_data)
                location = self._get_or_create_location(city_name, weather_data)
                UserSearchHistory.objects.create(
                    user=request.user,
                    location=location,
                    via_api=True
                )
            
            return Response(weather_data)
            
        except Exception as e:
            return Response(
                {"error": f"Could not fetch weather data: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _fetch_weather_data(self, city_name):
        """Fetch live weather data from OpenWeatherMap"""
        try:
            # First get coordinates
            geo_url = f"http://api.openweathermap.org/geo/1.0/direct?q={city_name}&limit=1&appid={settings.WEATHER_API_KEY}"
            geo_response = requests.get(geo_url, timeout=10)
            
            if geo_response.status_code != 200:
                raise ValueError(f"Geocoding API error: {geo_response.status_code}")
                
            geo_data = geo_response.json()
            
            if not geo_data:
                raise ValueError("City not found")
            
            # Then get weather
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={geo_data[0]['lat']}&lon={geo_data[0]['lon']}&appid={settings.WEATHER_API_KEY}&units=metric&lang=en"
            weather_response = requests.get(weather_url, timeout=10)
            
            if weather_response.status_code != 200:
                raise ValueError(f"Weather API error: {weather_response.status_code}")
                
            weather_data = weather_response.json()
            
            # Check if weather data contains required fields
            if 'weather' not in weather_data or 'main' not in weather_data:
                raise ValueError("Invalid weather data received")
            
            # Format the response
            return {
                "city": city_name.title(),
                "country": geo_data[0].get('country', ''),
                "coordinates": {
                    "latitude": geo_data[0]['lat'],
                    "longitude": geo_data[0]['lon']
                },
                "weather": {
                    "main": weather_data['weather'][0]['main'],
                    "description": weather_data['weather'][0]['description'],
                    "icon": f"https://openweathermap.org/img/wn/{weather_data['weather'][0]['icon']}@2x.png"
                },
                "temperature": {
                    "current": weather_data['main']['temp'],
                    "feels_like": weather_data['main']['feels_like'],
                    "min": weather_data['main']['temp_min'],
                    "max": weather_data['main']['temp_max']
                },
                "humidity": weather_data['main']['humidity'],
                "wind": {
                    "speed": weather_data['wind']['speed'],
                    "direction": weather_data['wind'].get('deg', 0)
                },
                "visibility": weather_data.get('visibility', 'N/A'),
                "clouds": weather_data['clouds']['all'],
                "sunrise": timezone.datetime.fromtimestamp(weather_data['sys']['sunrise']).strftime('%H:%M'),
                "sunset": timezone.datetime.fromtimestamp(weather_data['sys']['sunset']).strftime('%H:%M'),
                "timezone": weather_data['timezone'],
                "last_updated": timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            raise Exception(f"Weather service error: {str(e)}")

    def _get_or_create_location(self, city_name, weather_data):
        """Helper to get or create location with coordinates"""
        # Try to find existing location first
        try:
            location = Location.objects.get(name__iexact=city_name)
            # Update coordinates if they've changed
            if (abs(location.latitude - weather_data['coordinates']['latitude']) > 0.001 or
                abs(location.longitude - weather_data['coordinates']['longitude']) > 0.001):
                location.latitude = weather_data['coordinates']['latitude']
                location.longitude = weather_data['coordinates']['longitude']
                location.save()
            return location
        except Location.DoesNotExist:
            # Create new location
            return Location.objects.create(
                name=city_name.title(),
                latitude=weather_data['coordinates']['latitude'],
                longitude=weather_data['coordinates']['longitude'],
                country=weather_data['country']
            )

    def _save_to_database(self, city_name, weather_data):
        """Save weather data to database"""
        location = self._get_or_create_location(city_name, weather_data)
        
        WeatherData.objects.create(
            location=location,
            timestamp=timezone.now(),
            temperature=weather_data['temperature']['current'],
            humidity=weather_data['humidity'],
            wind_speed=weather_data['wind']['speed'],
            weather_type=self._map_weather_type(weather_data['weather']['main'])
        )

    def _map_weather_type(self, weather_main):
        """Map weather condition to our model"""
        mapping = {
            'Clear': 0, 'Clouds': 1, 'Rain': 2,
            'Snow': 3, 'Thunderstorm': 4
        }
        return mapping.get(weather_main, 1)

class WeatherForecastAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, city_name):
        try:
            # First get current weather to establish location
            current_api = CurrentWeatherAPI()
            current_data = current_api._fetch_weather_data(city_name)
            location = current_api._get_or_create_location(city_name, current_data)
            
            if request.user.is_authenticated:
                UserSearchHistory.objects.create(
                    user=request.user,
                    location=location,
                    via_api=True
                )
            
            # Fetch forecast from OpenWeatherMap
            forecast_url = f"https://api.openweathermap.org/data/2.5/forecast?lat={location.latitude}&lon={location.longitude}&appid={settings.WEATHER_API_KEY}&units=metric"
            forecast_response = requests.get(forecast_url)
            forecast_data = forecast_response.json()
            
            # Process forecast data
            forecasts = []
            for period in forecast_data['list'][:40]:  # Get first 40 periods (5 days)
                forecast_time = timezone.datetime.fromtimestamp(period['dt'])
                forecasts.append({
                    "datetime": forecast_time.strftime('%Y-%m-%d %H:%M:%S'),
                    "temperature": period['main']['temp'],
                    "feels_like": period['main']['feels_like'],
                    "weather": {
                        "main": period['weather'][0]['main'],
                        "description": period['weather'][0]['description'],
                        "icon": f"https://openweathermap.org/img/wn/{period['weather'][0]['icon']}@2x.png"
                    },
                    "humidity": period['main']['humidity'],
                    "wind_speed": period['wind']['speed'],
                    "precipitation": period.get('rain', {}).get('3h', 0)
                })
            
            return Response({
                "location": location.name,
                "country": location.country,
                "forecasts": forecasts
            })
            
        except Exception as e:
            return Response(
                {"error": f"Could not fetch forecast: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class ARIMAForecastAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, city_name):
        """Generate 7-day ARIMA forecast for a city"""
        try:
            # Get location coordinates
            current_api = CurrentWeatherAPI()
            current_data = current_api._fetch_weather_data(city_name)
            location = current_api._get_or_create_location(city_name, current_data)
            
            # Get historical data from Open-Meteo for ARIMA training
            historical_data = self._get_historical_weather_data(
                location.latitude, 
                location.longitude
            )
            
            if historical_data is None or historical_data.empty:
                return Response(
                    {"error": "Could not fetch sufficient historical data for ARIMA training", "fallback": "using_default"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Generate ARIMA forecast
            arima_forecast, model_status = self._generate_arima_forecast(historical_data)
            
            # Prepare response
            response_data = {
                "location": location.name,
                "country": location.country,
                "coordinates": {
                    "latitude": location.latitude,
                    "longitude": location.longitude
                },
                "forecast_type": "ARIMA_7Day",
                "historical_data_points": len(historical_data),
                "model_status": model_status,
                "forecast": arima_forecast,
                "generated_at": timezone.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return Response(response_data)
            
        except Exception as e:
            return Response(
                {"error": f"Could not generate ARIMA forecast: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

    def _get_historical_weather_data(self, lat, lon, days=60):
        """Fetch historical weather data for ARIMA training - FIXED VERSION"""
        try:
            # Use the CORRECT historical API endpoint
            url = "https://archive-api.open-meteo.com/v1/archive"
            params = {
                "latitude": lat,
                "longitude": lon,
                "start_date": (timezone.now() - timedelta(days=days)).strftime('%Y-%m-%d'),
                "end_date": (timezone.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m,relative_humidity_2m",
                "timezone": "auto"
            }
            
            response = requests.get(url, params=params, timeout=15)
            data = response.json()
            
            if 'daily' not in data:
                print(f"No historical data found for {lat},{lon}")
                return None
            
            # Convert to DataFrame
            daily_data = data['daily']
            df = pd.DataFrame({
                'date': pd.to_datetime(daily_data['time']),
                'temperature_max': daily_data['temperature_2m_max'],
                'temperature_min': daily_data['temperature_2m_min'],
                'precipitation': daily_data['precipitation_sum'],
                'wind_speed': daily_data['wind_speed_10m'],
                'humidity': daily_data['relative_humidity_2m']
            })
            
            print(f"Successfully fetched {len(df)} days of historical data")
            return df
            
        except Exception as e:
            print(f"Error fetching historical data: {e}")
            return None

    def _generate_arima_forecast(self, historical_data):
        """Generate 7-day forecast using ARIMA models - IMPROVED VERSION"""
        forecast_results = {}
        model_errors = {}
        model_status = {}
        
        # Define ARIMA parameters for different weather variables
        arima_config = {
            'temperature_max': {'order': (3, 1, 2), 'steps': 7},
            'temperature_min': {'order': (3, 1, 2), 'steps': 7},
            'precipitation': {'order': (1, 1, 1), 'steps': 7},
            'wind_speed': {'order': (2, 1, 1), 'steps': 7},
            'humidity': {'order': (2, 1, 1), 'steps': 7}
        }
        
        for column, config in arima_config.items():
            try:
                # Handle missing values better
                series = historical_data[column].fillna(method='ffill').fillna(method='bfill')
                
                if len(series) < 30:
                    raise ValueError(f"Not enough data points: {len(series)}")
                
                # Train ARIMA model
                model = ARIMA(series, order=config['order'])
                model_fit = model.fit()
                
                # Generate forecast
                forecast = model_fit.forecast(steps=config['steps'])
                forecast_results[column] = forecast.tolist()
                model_errors[column] = "success"
                model_status[column] = "trained"
                
            except Exception as e:
                error_msg = f"ARIMA failed for {column}: {str(e)}"
                print(error_msg)
                model_errors[column] = error_msg
                model_status[column] = "failed"
                # Use simple average as fallback
                avg_value = series.mean() if len(series) > 0 else 0
                forecast_results[column] = [avg_value] * config['steps']
        
        # Format response with error information
        formatted_forecast = self._format_forecast_response(forecast_results, model_errors)
        return formatted_forecast, model_status

    def _format_forecast_response(self, forecast_results, model_errors):
        """Format the forecast response with confidence levels"""
        today = timezone.now().date()
        formatted_forecast = []
        
        for i in range(7):
            forecast_date = today + timedelta(days=i+1)
            
            # Determine confidence based on model errors
            has_errors = any("failed" in error for error in model_errors.values())
            confidence = "low" if has_errors else "high"
            
            formatted_forecast.append({
                "date": forecast_date.strftime('%Y-%m-%d'),
                "day": forecast_date.strftime('%A'),
                "temperature": {
                    "max": round(forecast_results['temperature_max'][i], 1),
                    "min": round(forecast_results['temperature_min'][i], 1),
                    "average": round((forecast_results['temperature_max'][i] + 
                                    forecast_results['temperature_min'][i]) / 2, 1)
                },
                "precipitation": round(max(0, forecast_results['precipitation'][i]), 2),
                "wind_speed": round(max(0, forecast_results['wind_speed'][i]), 1),
                "humidity": round(max(0, min(100, forecast_results['humidity'][i])), 1),
                "confidence": confidence,
                "model_notes": "ARIMA forecast based on 60 days of historical data" if confidence == "high" else "Partial ARIMA forecast with some fallback values"
            })
        
        return formatted_forecast

class CombinedForecastAPI(APIView):
    permission_classes = [AllowAny]

    def get(self, request, city_name):
        """Combine OpenWeatherMap forecast with ARIMA predictions"""
        try:
            # Get OpenWeatherMap forecast
            forecast_api = WeatherForecastAPI()
            owm_forecast_response = forecast_api.get(request, city_name)
            
            # Check if the response is an error
            if owm_forecast_response.status_code != status.HTTP_200_OK:
                return owm_forecast_response
                
            owm_data = owm_forecast_response.data
            
            # Get ARIMA forecast
            arima_api = ARIMAForecastAPI()
            arima_forecast_response = arima_api.get(request, city_name)
            
            # Check if the response is an error
            if arima_forecast_response.status_code != status.HTTP_400_BAD_REQUEST:
                arima_data = arima_forecast_response.data
                arima_available = True
            else:
                arima_data = {"error": "ARIMA forecast not available"}
                arima_available = False
            
            # Combine both forecasts
            combined_data = {
                "location": owm_data.get('location'),
                "country": owm_data.get('country'),
                "openweathermap_forecast": {
                    "days": len(owm_data.get('forecasts', [])),
                    "data": owm_data.get('forecasts', [])
                },
                "arima_forecast_available": arima_available,
                "arima_forecast": arima_data if arima_available else {"error": "ARIMA not available"},
                "comparison_notes": "ARIMA provides 7-day forecast using historical patterns, while OpenWeatherMap provides detailed 5-day forecast"
            }
            
            return Response(combined_data)
            
        except Exception as e:
            return Response(
                {"error": f"Could not generate combined forecast: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST
            )

class UserSearchHistoryAPI(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Get search history for authenticated users"""
        searches = UserSearchHistory.objects.filter(
            user=request.user
        ).select_related('location').order_by('-search_time')[:50]
        
        data = [{
            'location': search.location.name,
            'country': search.location.country,
            'timestamp': search.search_time,
            'via_api': search.via_api
        } for search in searches]
        
        return Response(data)
