from __future__ import absolute_import
from celery import Celery  # pylint: disable=import-error
from django.apps import apps  # pylint: disable=wrong-import-order

import os
from kombu import Exchange, Queue

import yaml

settings_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'settings.yaml')
with open(settings_filename) as settings_file:
    data = yaml.load(settings_file)

print(data)

DEBUG = data['debug']
SECRET_KEY = data['secret_key']

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.humanize',
    'tardis.tardis_portal'
)

DEFAULT_INSTITUTION = "Monash"

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': data['postgres']['host'],
        'PORT': data['postgres']['port'],
        'USER': data['postgres']['user'],
        'PASSWORD': data['postgres']['password'],
        'NAME': data['postgres']['db']
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'default_cache',
    },
    'celery-locks': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'celery_lock_cache',
    }
}

CELERY_RESULT_BACKEND = 'rpc'
BROKER_URL = 'amqp://{user}:{password}@{host}:{port}/{vhost}'.format(
    host = data['rabbitmq']['host'],
    port = data['rabbitmq']['port'],
    user = data['rabbitmq']['user'],
    password = data['rabbitmq']['password'],
    vhost = data['rabbitmq']['vhost']
)

MAX_TASK_PRIORITY = data['celery']['max_task_priority']
DEFAULT_TASK_PRIORITY = data['celery']['default_task_priority']

CELERY_ACKS_LATE = True
CELERY_DEFAULT_QUEUE = data['celery']['default_queue']
CELERY_QUEUES = (
    Queue(CELERY_DEFAULT_QUEUE, Exchange(CELERY_DEFAULT_QUEUE),
          routing_key = CELERY_DEFAULT_QUEUE,
          queue_arguments = {
            'x-max-priority': MAX_TASK_PRIORITY
          }),
)

CELERY_IMPORTS = data['celery']['imports']

BIOFORMATS_QUEUE = 'mytardisbf'
MTBF_MAX_HEAP_SIZE = '1G'

METADATA_STORE_PATH = data['metadata_store_path']

POST_SAVE_FILTERS = data['post_save_filters']
