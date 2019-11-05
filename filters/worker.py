from celery import Celery
from kombu import Exchange, Queue

from filters.settings import config


app = Celery('filters')
app.conf.update({
    'broker_url': config['broker_url'],
    'imports': ('filters.tasks'),
    'result_persistent': False,
    'task_serializer': 'json',
    'result_serializer': 'json',
    'accept_content': ['json']
})

app.conf.task_queues = []
for k in config['queues']:
    q = config['queues'][k]
    app.conf.task_queues.append(
        Queue(
            q['name'],
            exchange=Exchange(q['name']),
            routing_key=q['name'],
            max_priority=q['max_task_priority']
        )
    )

for k in ['queue', 'exchange', 'routing_key']:
    app.conf.update({
        "task_default_{}".format(k): config['queues']['filters']['name']
    })
