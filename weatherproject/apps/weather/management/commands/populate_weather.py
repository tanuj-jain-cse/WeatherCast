# apps/weather/management/commands/populate_weather.py
from django.core.management.base import BaseCommand
from apps.weather.models import Location, WeatherData
from django.utils import timezone

class Command(BaseCommand):
    help = 'Populates initial weather data'

    def handle(self, *args, **options):
        # Create sample locations
        pune = Location.objects.create(
            name="Pune",
            latitude=18.5204,
            longitude=73.8567,
            country="India"
        )

        # Create current weather data
        WeatherData.objects.create(
            location=pune,
            timestamp=timezone.now(),
            temperature=28.5,
            humidity=65,
            wind_speed=12.3,
            weather_type=0  # Clear
        )