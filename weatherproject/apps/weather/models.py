from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Location(models.Model):
    """Stores geographic locations without GIS dependencies"""
    name = models.CharField(max_length=100, db_index=True)
    latitude = models.DecimalField(
        max_digits=9, 
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)]
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)]
    )
    country = models.CharField(max_length=100, db_index=True)
    elevation = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
        ]

    def __str__(self):
        return f"{self.name}, {self.country}"

class WeatherData(models.Model):
    """Weather observations and forecasts"""
    class WeatherType(models.IntegerChoices):
        CLEAR = 0, 'Clear'
        CLOUDY = 1, 'Cloudy'
        RAIN = 2, 'Rain'
        SNOW = 3, 'Snow'
        THUNDERSTORM = 4, 'Thunderstorm'

    location = models.ForeignKey(
        Location,
        on_delete=models.CASCADE,
        related_name='weather_data'
    )
    timestamp = models.DateTimeField(db_index=True)
    temperature = models.FloatField(
        help_text="Temperature in °C",
        validators=[MinValueValidator(-50), MaxValueValidator(60)]
    )
    humidity = models.FloatField(
        help_text="Relative humidity in %",
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    wind_speed = models.FloatField(help_text="Wind speed in km/h")
    precipitation = models.FloatField(default=0, help_text="Precipitation in mm")
    weather_type = models.IntegerField(choices=WeatherType.choices, default=WeatherType.CLEAR)
    is_forecast = models.BooleanField(default=False)
    forecast_day = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MaxValueValidator(14)]
    )
    flood_risk = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    storm_risk = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    wildfire_risk = models.FloatField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    class Meta:
        indexes = [
            models.Index(fields=['location', 'timestamp']),
            models.Index(fields=['is_forecast', 'forecast_day']),
        ]
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.location} | {self.timestamp.date()} | {self.get_weather_type_display()}"

class UserSearchHistory(models.Model):
    """Tracks user weather searches"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='searches')
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    search_time = models.DateTimeField(auto_now_add=True)
    via_api = models.BooleanField(default=False)

    class Meta:
        ordering = ['-search_time']
        verbose_name_plural = 'User Search History'

    def __str__(self):
        return f"{self.user.username} searched {self.location.name} at {self.search_time}"