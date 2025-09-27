from celery import shared_task
from django.utils import timezone
from utilities.api_clients import OpenWeatherClient
from .models import WeatherData, Location
import logging

logger = logging.getLogger(__name__)

@shared_task
def fetch_current_weather():
    """Fetch current weather for all locations"""
    client = OpenWeatherClient()
    for location in Location.objects.all():
        try:
            weather_data = client.get_current_weather(
                lat=location.latitude,
                lon=location.longitude
            )
            WeatherData.objects.update_or_create(
                location=location,
                timestamp=weather_data['timestamp'],
                defaults=weather_data
            )
        except Exception as e:
            logger.error(f"Current weather fetch failed for {location.name}: {str(e)}")

@shared_task
def fetch_16_day_forecast():
    """Fetch 16-day forecast (including today)"""
    client = OpenWeatherClient()
    for location in Location.objects.all():
        try:
            forecasts = client.get_16_day_forecast(
                lat=location.latitude,
                lon=location.longitude
            )
            for forecast in forecasts:
                WeatherData.objects.update_or_create(
                    location=location,
                    timestamp=forecast['timestamp'],
                    is_forecast=True,
                    defaults=forecast
                )
        except Exception as e:
            logger.error(f"Forecast fetch failed for {location.name}: {str(e)}")