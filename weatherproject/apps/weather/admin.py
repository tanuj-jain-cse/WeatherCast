from django.contrib import admin
from .models import Location, WeatherData, UserSearchHistory

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('name', 'country', 'latitude', 'longitude')
    search_fields = ('name', 'country')
    list_filter = ('country',)

@admin.register(WeatherData)
class WeatherDataAdmin(admin.ModelAdmin):
    list_display = ('location', 'timestamp', 'temperature', 'weather_type')
    list_filter = ('is_forecast', 'weather_type')
    search_fields = ('location__name',)
    date_hierarchy = 'timestamp'

@admin.register(UserSearchHistory)
class UserSearchHistoryAdmin(admin.ModelAdmin):
    list_display = ('user', 'location', 'search_time', 'via_api')
    list_filter = ('via_api', 'search_time')
    search_fields = ('user__username', 'location__name')
    date_hierarchy = 'search_time' 