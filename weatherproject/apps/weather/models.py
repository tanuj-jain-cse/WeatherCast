from django.db import models
from django.conf import settings

class Location(models.Model):
    name = models.CharField(max_length=100)
    latitude = models.FloatField()
    longitude = models.FloatField()
    country = models.CharField(max_length=100, blank=True)
    
    def __str__(self):
        return self.name

class WeatherData(models.Model):
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    timestamp = models.DateTimeField()
    temperature = models.FloatField()
    humidity = models.FloatField()
    wind_speed = models.FloatField()
    weather_type = models.IntegerField(choices=[
        (0, 'Clear'), (1, 'Clouds'), (2, 'Rain'),
        (3, 'Snow'), (4, 'Thunderstorm')
    ])
    
    def __str__(self):
        return f"{self.location.name} - {self.timestamp}"

class UserSearchHistory(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    location = models.ForeignKey(Location, on_delete=models.CASCADE)
    search_time = models.DateTimeField(auto_now_add=True)
    via_api = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.user} searched {self.location.name}"
