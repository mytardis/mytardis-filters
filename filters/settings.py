import os
import yaml

this_folder = os.path.dirname(os.path.realpath(__file__))
settings_filename = os.path.join(this_folder, 'settings.yaml')
with open(settings_filename) as settings_file:
    config = yaml.load(settings_file, Loader=yaml.FullLoader)

config['broker_url'] = "amqp://{user}:{password}@{host}:{port}/{vhost}".format(
    host=config['rabbitmq']['host'],
    port=config['rabbitmq']['port'],
    user=config['rabbitmq']['user'],
    password=config['rabbitmq']['password'],
    vhost=config['rabbitmq']['vhost']
)
