import os
import traceback
import logging

import javabridge
import bioformats
from bioformats import log4j

from django.conf import settings

from ..helpers import fileFilter, get_thumbnail_paths
from .metadata import get_meta

logger = logging.getLogger(__name__)

mtbf_jvm_started = False  # Global to check whether JVM started on a thread


def check_and_start_jvm():
    """
    Checks global to see whether a JVM is running and if not starts
    a new one. If JVM starts successfully the global variable mtbf_jvm_started
    is updated to ensure that another JVM is not started.
    """
    global mtbf_jvm_started
    if not mtbf_jvm_started:
        logger.debug('Starting a new JVM')
        try:
            mh_size = getattr(settings, 'MTBF_MAX_HEAP_SIZE', '4G')
            javabridge.start_vm(class_path=bioformats.JARS,
                                max_heap_size=mh_size,
                                run_headless=True)
            mtbf_jvm_started = True
        except javabridge.JVMNotFoundError as e:
            logger.debug(e)


class BioformatsFilter(fileFilter):
    """
    MyTardis filter for extracting metadata from micrscopy image
    formats using the Bioformats library.
    """

    def __call__(self, id, filename, uri, **kwargs):
        """
        Extract metadata from a Datafile using the get_meta function and save
        the outputs as DatafileParameters. This function differs from
        process_meta in that it generates an output directory in the metadata
        store and passes it to the metadata processing func so that outputs
        e.g., preview images or metadata files) can be saved.

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

        _, extension = os.path.splitext(filename)
        if extension[1:] not in bioformats.READABLE_FORMATS:
            return None

        logger.info("Applying Bioformats filter to {}...".format(filename))

        # Need to start a JVM in each thread
        check_and_start_jvm()

        try:
            javabridge.attach()
            log4j.basic_config()

            thumb_rel_path, thumb_abs_path = get_thumbnail_paths(id, filename,
                                                                 uri)

            if not os.path.exists(os.path.dirname(thumb_abs_path)):
                os.makedirs(os.path.dirname(thumb_abs_path))

            rsp = get_meta(filename, os.path.dirname(thumb_abs_path), **kwargs)
            if rsp is not None:
                return self.filter_metadata(rsp[0])

        except Exception as e:
            logger.error(str(e))
            logger.debug(traceback.format_exc())
        finally:
            javabridge.detach()
            javabridge.kill_vm()

        return None


def make_filter(name='', schema='',
                tagsToFind=[], tagsToExclude=[]):
    if not name:
        raise ValueError("BioformatsFilter "
                         "requires a name to be specified")
    if not schema:
        raise ValueError("BioformatsFilter "
                         "requires a schema to be specified")
    return BioformatsFilter(name, schema,
                            tagsToFind, tagsToExclude)


make_filter.__doc__ = BioformatsFilter.__doc__
