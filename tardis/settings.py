from __future__ import absolute_import
import os
from kombu import Exchange, Queue
import yaml

settings_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                 'settings.yaml')
with open(settings_filename) as settings_file:
    data = yaml.load(settings_file, Loader=yaml.FullLoader)

DEBUG = data['debug']
SECRET_KEY = data['secret_key']
INSTALLED_APPS = data['installed_apps']
CACHES = data['caches']

BROKER_URL = 'amqp://{user}:{password}@{host}:{port}/{vhost}'.format(
    host=data['rabbitmq']['host'],
    port=data['rabbitmq']['port'],
    user=data['rabbitmq']['user'],
    password=data['rabbitmq']['password'],
    vhost=data['rabbitmq']['vhost']
)

MAX_TASK_PRIORITY = data['celery']['max_task_priority']

CELERY_DEFAULT_QUEUE = data['celery']['default_queue']
DEFAULT_TASK_PRIORITY = data['celery']['default_task_priority']

API_QUEUE = data['api']['queue']
API_TASK_PRIORITY = data['api']['task_priority']

CELERY_RESULT_BACKEND = data['celery']['result_backend']
CELERY_ACKS_LATE = data['celery']['acks_late']

CELERY_QUEUES = (
    Queue(
        CELERY_DEFAULT_QUEUE,
        Exchange(CELERY_DEFAULT_QUEUE),
        routing_key=CELERY_DEFAULT_QUEUE,
        queue_arguments={
            'x-max-priority': MAX_TASK_PRIORITY
        }
    ),
    Queue(
        API_QUEUE,
        Exchange(API_QUEUE),
        routing_key=API_QUEUE,
        queue_arguments={
            'x-max-priority': MAX_TASK_PRIORITY
        }
    )
)

DEFAULT_FILE_STORAGE = data['default_file_storage']
STORE_DATA = data['store_data']
METADATA_STORE_PATH = data['metadata_store_path']

POST_SAVE_FILTERS = data['post_save_filters']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:'
    }
}

MTBF_MAX_HEAP_SIZE = '1G'
