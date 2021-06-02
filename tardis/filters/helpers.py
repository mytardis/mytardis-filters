import os
from urllib.parse import urlparse
from importlib import import_module
import subprocess
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.cache import caches

logger = logging.getLogger(__name__)
cache = caches['default']


class fileFilter(object):
    """
    Base class for metadata filter
    """

    def __init__(self, name, schema, tagsToFind=[], tagsToExclude=[]):
        """
        param name: the short name of the schema.
        type name: string

        param schema: the name of the schema to load the previewImage into.
        type schema: string

        param tagsToFind: a list of the tags to include.
        type tagsToFind: list of strings

        param tagsToExclude: a list of the tags to exclude.
        type tagsToExclude: list of strings
        """

        self.name = name
        self.schema = schema
        self.tagsToFind = tagsToFind
        self.tagsToExclude = tagsToExclude

    def filter_metadata(self, results):
        """
        Filter out results to include/exclude tags

        param results: Raw extracted data
        type results: dict

        return Filtered metadata
        rtype dict
        """

        metadata = {}
        for tag in results:
            if self.tagsToFind and tag not in self.tagsToFind:
                continue
            if tag in self.tagsToExclude:
                continue
            metadata[tag] = results[tag]

        return metadata


def safe_import(filter):
    filter_path = filter[0][0]
    filter_args = filter[1] if len(filter) > 1 else []
    filter_kwargs = filter[2] if len(filter) > 2 else {}
    try:
        dot = filter_path.rindex('.')
    except ValueError:
        # pylint: disable=W0707
        raise ImproperlyConfigured(
            "{} isn't a filter module".format(filter_path))
    module_name, class_name = filter_path[:dot], filter_path[dot + 1:]
    try:
        module = import_module(module_name)
    except ImportError as e:
        # pylint: disable=W0707
        raise ImproperlyConfigured(
            "Error importing filter {}: {}".format(module_name, e))
    try:
        filter_class = getattr(module, class_name)
    except AttributeError:
        # pylint: disable=W0707
        raise ImproperlyConfigured(
            "Filter module {} does not define a {} class".format(module_name,
                                                                 class_name))
    return filter_class(*filter_args, **filter_kwargs)


def get_thumbnail_paths(
        df_id, filepath, uri, ext='png', replace_ext=False):
    basename = os.path.basename(filepath)
    if replace_ext:
        basename = os.path.splitext(basename)[0]
    preview_image_rel_file_path = os.path.join(
        os.path.dirname(urlparse(uri).path),
        str(df_id),
        '%s.%s' % (basename, ext))
    return (preview_image_rel_file_path,
            os.path.join(settings.METADATA_STORE_PATH,
                         preview_image_rel_file_path))


def exec_command(cmd):
    """execute command on shell"""
    with subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            shell=True) as p:
        stdout, _ = p.communicate()
        if p.returncode != 0:
            logger.error(stdout)
            return None

    return stdout


def fileoutput(cd, bin, args=[]):
    """execute command on shell with a file output"""
    cmd = "cd %s; ./%s %s" % (cd, bin, ' '.join(args))
    logger.info(cmd)

    return exec_command(cmd)


def textoutput(cd, execfilename, inputfilename, args=''):
    """execute command on shell with a stdout output
    """
    cmd = "cd '%s'; ./'%s' '%s' %s" % \
          (cd, execfilename, inputfilename, args)
    logger.info(cmd)

    return exec_command(cmd)


# cache.add fails if if the key already exists
def acquire_lock(lock_id, expire=60):
    return cache.add(lock_id, 'true', expire)


# cache.delete() can be slow, but we have to use it
# to take advantage of using add() for atomic locking
def release_lock(lock_id):
    cache.delete(lock_id)
