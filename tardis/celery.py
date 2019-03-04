from __future__ import absolute_import
from celery import Celery  # pylint: disable=import-error

tardis_app = Celery('tardis')
tardis_app.config_from_object('django.conf:settings')
tardis_app.autodiscover_tasks()