from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path
from django.views.generic import TemplateView
from rest_framework.authtoken import views as authtoken_views
from apps.weather.views import (
    LocationListAPI, 
    WeatherForecastAPI, 
    CurrentWeatherAPI,
    UserSearchHistoryAPI,
    ARIMAForecastAPI,
    CombinedForecastAPI
)

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # ONLY the API endpoints you need
    path('api/locations/', LocationListAPI.as_view(), name='location-list'),
    path('api/weather/<str:city_name>/', CurrentWeatherAPI.as_view(), name='current-weather'),
    path('api/forecast/<str:city_name>/', WeatherForecastAPI.as_view(), name='weather-forecast'),
    path('api/arima-forecast/<str:city_name>/', ARIMAForecastAPI.as_view(), name='arima-forecast'),
    path('api/combined-forecast/<str:city_name>/', CombinedForecastAPI.as_view(), name='combined-forecast'),
    path('api/search-history/', UserSearchHistoryAPI.as_view(), name='search-history'),
    path('api-token-auth/', authtoken_views.obtain_auth_token, name='api-token-auth'),

    # Frontend views
    path('', TemplateView.as_view(template_name="index.html"), name="index"),
    path('dashboard/', TemplateView.as_view(template_name="finalvalafinal.html"), name="dashboard"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
