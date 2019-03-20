import os
import random
import uuid
from shutil import copyfile

from django.conf import settings

base_path = os.path.abspath(os.path.dirname(__file__))


def get_filter_settings(filter_name):
    for filter in getattr(settings, 'POST_SAVE_FILTERS', []):
        if filter[1][0] == filter_name:
            return filter
    return None


def get_datafile_id():
    return random.randint(1, 2147483647)


def get_dataset_name():
    return str(uuid.uuid4())


def get_thumbnail_file(filename):
    return os.path.join(settings.METADATA_STORE_PATH, filename)


def get_assets_file(filename):
    return os.path.join(base_path, 'assets', filename)


def create_datafile(filename, dataset_name):
    df_abs_path = os.path.join(settings.STORE_DATA, dataset_name, filename)
    if not os.path.exists(os.path.dirname(df_abs_path)):
        os.makedirs(os.path.dirname(df_abs_path))
    copyfile(get_assets_file(filename), df_abs_path)
    return df_abs_path


def delete_datafile(filename):
    pass
