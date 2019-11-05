import os
import random
import uuid
from shutil import copyfile

from filters.settings import config

base_path = os.path.abspath(os.path.dirname(__file__))


def get_filter_settings(filter_name):
    for filter in config['post_save_filters']:
        if filter['name'] == filter_name:
            return filter
    raise ValueError("Can\'t find filter {} in settings".format(filter_name))


def get_datafile_id():
    return random.randint(1, 2147483647)


def get_dataset_name():
    return str(uuid.uuid4())


def get_thumbnail_file(filename):
    return os.path.join(config['metadata_store_path'], filename)


def get_assets_file(filename):
    return os.path.join(base_path, 'assets', filename)


def create_datafile(filename, dataset_name):
    df_abs_path = os.path.join(config['default_store_path'],
                               dataset_name, filename)
    if not os.path.exists(os.path.dirname(df_abs_path)):
        os.makedirs(os.path.dirname(df_abs_path))
    copyfile(get_assets_file(filename), df_abs_path)
    return df_abs_path


def delete_datafile(filename):
    pass
