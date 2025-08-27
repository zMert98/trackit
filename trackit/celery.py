import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trackit.settings")
app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.beat_schedule = {
    'clear-blacklist-every-day': {
        'task': 'user.tasks.clear_blacklist',
        'schedule': crontab(hour=0, minute=0),
    },
}

app.conf.timezone = 'UTC'