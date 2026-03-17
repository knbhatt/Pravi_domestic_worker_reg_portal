import os

from celery import Celery
from decouple import config

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("config")

app.config_from_object("django.conf:settings", namespace="CELERY")

broker_url = config("REDIS_URL", default="redis://127.0.0.1:6379/0")
app.conf.broker_url = broker_url
app.conf.result_backend = broker_url

app.autodiscover_tasks()

