import os
from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('weather_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Scheduled tasks
app.conf.beat_schedule = {
    'fetch-current-weather': {
        'task': 'apps.weather.tasks.fetch_current_weather',
        'schedule': 1800.0,  # Every 30 minutes (OpenWeather free tier allows 60 calls/minute)
    },
    'fetch-16-day-forecast': {
        'task': 'apps.weather.tasks.fetch_16_day_forecast',
        'schedule': 43200.0,  # Every 12 hours (less frequent due to larger data)
    },
}