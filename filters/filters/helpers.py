import os
from urllib.parse import urlparse
from importlib import import_module
import subprocess
import logging

from filters.settings import config

logger = logging.getLogger(__name__)


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
    try:
        dot = filter['path'].rindex('.')
    except Exception as e:
        logger.error('%s isn\'t a filter module', filter['path'])
        logger.error(str(e))
        raise
    module_name, class_name = filter['path'][:dot], filter['path'][dot + 1:]
    try:
        module = import_module(module_name)
    except Exception as e:
        logger.error('Error importing filter %s: %s', module_name, str(e))
        logger.error(str(e))
        raise
    try:
        filter_class = getattr(module, class_name)
    except Exception as e:
        logger.error('Filter module %s does not define a %s class',
                     module_name, class_name)
        logger.error(str(e))
        raise
    filter_args = [
        filter['name'],
        filter['schema']
    ] + filter.get('args', [])
    return filter_class(*filter_args)


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
            os.path.join(config['metadata_store_path'],
                         preview_image_rel_file_path))


def exec_command(cmd):
    """execute command on shell"""
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, shell=True)
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
