from __future__ import absolute_import
from celery import Celery

app = Celery('tardis')
app.config_from_object('django.conf:settings')
app.autodiscover_tasks()
