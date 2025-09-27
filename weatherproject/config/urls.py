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
    UserSearchHistoryAPI
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/locations/', LocationListAPI.as_view()),
    path('api/forecast/<str:city_name>/', WeatherForecastAPI.as_view()),
    # Changed from /api/current/ to /api/weather/ to match frontend expectations
    path('api/weather/<str:city_name>/', CurrentWeatherAPI.as_view()),
    path('api/search-history/', UserSearchHistoryAPI.as_view()),
        path('api-token-auth/', authtoken_views.obtain_auth_token),

    path('', TemplateView.as_view(template_name="index.html"), name="index"),
    path('dashboard/', TemplateView.as_view(template_name="finalvalafinal.html"), name="finalvalafinal"),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    