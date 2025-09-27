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
            geo_response = requests.get(geo_url)
            geo_data = geo_response.json()
            
            if not geo_data:
                raise ValueError("City not found")
            
            # Then get weather
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={geo_data[0]['lat']}&lon={geo_data[0]['lon']}&appid={settings.WEATHER_API_KEY}&units=metric&lang=en"
            weather_response = requests.get(weather_url)
            weather_data = weather_response.json()
            
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