import os
from kombu import Exchange, Queue
from .default_settings import *

DEBUG = True

SECRET_KEY = os.environ['SECRET_KEY']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', 5432),
        'USER': os.environ.get('POSTGRES_USER', 'user'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', 'password'),
        'NAME': os.environ.get('POSTGRES_NAME', 'postgres')
    }
}

BROKER_URL = 'amqp://%(user)s:%(password)s@%(host)s:5672/%(vhost)s' % {
    'host': os.environ.get('RABBITMQ_HOST', 'localhost'),
    'port': os.environ.get('RABBITMQ_PORT', 5672),
    'user': os.environ.get('RABBITMQ_USER', 'guest'),
    'password': os.environ.get('RABBITMQ_PASSWORD', 'guest'),
    'vhost': os.environ.get('RABBITMQ_VHOST', '/')
}

DEFAULT_STORAGE_BASE_DIR = '/var/store/'
METADATA_STORE_PATH = '/var/store/metadata/'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        }
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO'
        },
    }
}

CELERY_QUEUES += (
    Queue(
        'filters',
        Exchange('filters'),
        routing_key='filters',
        queue_arguments={
            'x-max-priority': MAX_TASK_PRIORITY
        }
    ),
)
