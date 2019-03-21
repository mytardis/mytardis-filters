import sys
import os
import traceback
import logging
import re

from ..helpers import fileFilter, get_thumbnail_paths, exec_command

logger = logging.getLogger(__name__)


def run_fcsplot(fcsplot_path, id, filename, uri):
    """
    Run fcsplot on a FCS file.
    """
    thumb_rel_path, thumb_abs_path = get_thumbnail_paths(id, filename,
                                                         uri)

    if not os.path.exists(os.path.dirname(thumb_abs_path)):
        os.makedirs(os.path.dirname(thumb_abs_path))

    exec_command(
        "{} {} '{}' '{}'".format(sys.executable, fcsplot_path, filename,
                                 thumb_abs_path))

    if os.path.exists(thumb_abs_path):
        return thumb_rel_path

    return None


def run_showinf(showinf_path, id, filename):
    """
    Run showinf on FCS file to extract metadata.
    """
    results = exec_command(
        "%s %s '%s'" % (sys.executable, showinf_path, filename))

    if results is not None:
        metadata = {
            'file': '',
            'date': '',
            'parametersAndStainsTable': ''
        }

        image_info_list = results.decode().split('\n')
        readingParametersAndStainsTable = False

        for line in image_info_list:
            m = re.match("File: (.*)", line)
            if m:
                metadata['file'] = m.group(1)
            m = re.match("Date: (.*)", line)
            if m:
                metadata['date'] = m.group(1)
            if line.strip() == "<ParametersAndStains>":
                readingParametersAndStainsTable = True
            elif line.strip() == "</ParametersAndStains>":
                readingParametersAndStainsTable = False
            elif readingParametersAndStainsTable:
                metadata['parametersAndStainsTable'] += line

        return metadata

    return None


class FcsImageFilter(fileFilter):
    """
    This filter uses the Bioconductor flowCore and flowViz
    packages to extract metadata and plot preview images for
    FCS data files.
    """

    def __init__(self, name, schema, fcsplot_path, showinf_path,
                 tagsToFind=[], tagsToExclude=[]):
        super(FcsImageFilter, self).__init__(name, schema, tagsToFind,
                                             tagsToExclude)
        self.fcsplot_path = fcsplot_path
        self.showinf_path = showinf_path

    def __call__(self, id, filename, uri, **kwargs):
        """
        param id: Datafile ID
        type id: integer

        param filename: Absolute path to a file for processing
        type filename: string

        param uri: Dataset URI
        type uri: string

        param kwargs: Extra arguments
        type kwargs: object

        return Extracted metadata
        rtype dict
        """
        if not filename.lower().endswith('.fcs'):
            return None

        logger.info("Applying FCS filter to {}...".format(filename))
        try:
            rsp = {}

            # Generate thumbnail image
            r = run_fcsplot(self.fcsplot_path, id, filename, uri)
            if r is not None:
                rsp['previewImage'] = r

            # Extract metadata
            r = run_showinf(self.showinf_path, id, filename)
            if r is not None:
                rsp.update(r)

            return self.filter_metadata(rsp)

        except Exception as e:
            logger.error(str(e))
            logger.debug(traceback.format_exc())

        return None


def make_filter(name='', schema='',
                fcsplot_path=None, showinf_path=None,
                tagsToFind=[], tagsToExclude=[]):
    if not name:
        raise ValueError("FcsImageFilter "
                         "requires a name to be specified")
    if not schema:
        raise ValueError("FcsImageFilter "
                         "requires a schema to be specified")
    if not fcsplot_path:
        raise ValueError("FcsImageFilter "
                         "requires an fcsplot path to be specified")
    if not showinf_path:
        raise ValueError("FcsImageFilter "
                         "requires a showinf path to be specified")
    return FcsImageFilter(name, schema,
                          fcsplot_path, showinf_path,
                          tagsToFind, tagsToExclude)


make_filter.__doc__ = FcsImageFilter.__doc__
