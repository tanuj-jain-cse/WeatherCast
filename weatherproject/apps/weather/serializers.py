from rest_framework import serializers
from apps.weather.models import Location, WeatherData

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'name', 'latitude', 'longitude', 'country']
        extra_kwargs = {
            'latitude': {'required': True},
            'longitude': {'required': True}
        }
class WeatherDataSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)
    
    class Meta:
        model = WeatherData
        fields = '__all__'