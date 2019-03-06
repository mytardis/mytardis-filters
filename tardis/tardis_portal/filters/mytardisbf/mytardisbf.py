"""
Tasks for extracting metadata from image files using Bioformats
"""
import logging
import os
import urlparse
import sys

from django.conf import settings
from django.core.cache import caches

from celery.task import task

import javabridge  # pylint: disable=import-error
import bioformats  # pylint: disable=import-error
from bioformats import log4j  # pylint: disable=import-error

from tardis.tardis_portal.models import Schema, DatafileParameterSet
from tardis.tardis_portal.models import ParameterName, DatafileParameter
from tardis.tardis_portal.models import DataFile, DataFileObject

logger = logging.getLogger(__name__)

LOCK_EXPIRE = 60 * 5  # Lock expires in 5 minutes
mtbf_jvm_started = False  # Global to check whether JVM started on a thread

reload(sys)
sys.setdefaultencoding('utf8')


def generate_lockid(datafile_id):
    """Return a lock id for a datafile"""
    return "mtbf-lock-%d" % datafile_id


def acquire_datafile_lock(datafile_id, cache_name='celery-locks'):
    """ Lock a datafile to prevent filters from running mutliple times on
    the same datafile in quick succession.

    Parameters
    ----------
    :param datafile_id: ID of the datafile
    :type datafile_id: int
    :param cache_name: Optional specify the name of the lock cache to store
        this lock in
    :type cache_name: string

    Returns
    -------
    :return: Boolean representing whether datafile is locked
    :rtype: boolean

    """
    lockid = generate_lockid(datafile_id)
    cache = caches[cache_name]
    return cache.add(lockid, 'true', LOCK_EXPIRE)


def release_datafile_lock(datafile_id, cache_name='celery-locks'):
    """ Release lock on datafile.

    Parameters
    ----------
    :param datafile_id: ID of the datafile
    :type datafile_id: int
    :param cache_name: Optional specify the name of the lock cache to store
        this lock in
    :type cache_name: string

    """
    lockid = generate_lockid(datafile_id)
    cache = caches[cache_name]
    cache.delete(lockid)


def check_and_start_jvm():
    """ Checks global to see whether a JVM is running and if not starts
    a new one. If JVM starts successfully the global variable mtbf_jvm_started
    is updated to ensure that another JVM is not started.
    """
    global mtbf_jvm_started
    if not mtbf_jvm_started:
        logger.debug("Starting a new JVM")
        try:
            mh_size = getattr(settings, 'MTBF_MAX_HEAP_SIZE', '4G')
            javabridge.start_vm(class_path=bioformats.JARS,
                                max_heap_size=mh_size,
                                run_headless=True)
            mtbf_jvm_started = True
        except javabridge.JVMNotFoundError as err:
            logger.debug(err)


def delete_old_parameterset(ps):
    """ Remove a ParameterSet and all associated DatafileParameters

    Parameters
    ----------
    :param ps: A ParameterSet instance to remove
    :type ps: ParameterSet

    """

    params = DatafileParameter.objects.get(parameterset=ps)
    for dfp in params.iteritems():
        dfp.delete()
    ps.delete()


def save_parameters(schema, param_set, params):
    """ Save a given set of parameters as DatafileParameters.

    Parameters
    ----------
    :param schema: Schema that describes the parameter names.
    :type schema: tardis.tardis_portal.models.Schema
    :param param_set: Parameterset that these parameters are
        to be associated with.
    :type param_set: tardis.tardis_portal.models.DatafileParameterSet
    :param params:
        Dictionary with ParameterNames as keys and the Parameters as values.
        Parameters (values) can be singular strings/numerics or a list of
        strings/numeric. If it's a list, each element will be saved as a
        new DatafileParameter.
    :type params: dict

    """

    def savep(paramk, paramv):
        """
        Save a parameter, given a key/value pair
        """
        param_name = ParameterName.objects.get(schema__id=schema.id,
                                               name=paramk)
        dfp = DatafileParameter(parameterset=param_set, name=param_name)
        if paramv != "":
            if param_name.isNumeric():
                dfp.numerical_value = paramv
            else:
                dfp.string_value = paramv
            dfp.save()

    for paramk, paramv in params.iteritems():
        if isinstance(paramv, list):
            for value in paramv:
                savep(paramk, value)
        else:
            savep(paramk, paramv)


@task(name="tardis_portal.filters.mytardisbf.process_meta_file_output",
      ignore_result=True)
def process_meta_file_output(df_id, schema_name, overwrite=False, **kwargs):
    """Extract metadata from a Datafile using the get_meta function and save the
    outputs as DatafileParameters. This function differs from process_meta in
    that it generates an output directory in the metadata store and passes it
    to the metadata processing func so that outputs (e.g., preview images or
    metadata files) can be saved.

    Parameters
    ----------
    :param df_id: ID of Datafile instance to process.
    :type df_id: int
    :param schema_name: Names of schema which describes ParameterNames
    :type schema_name: string
    :param overwrite: Specifies whether to overwrite any exisiting parametersets
        for this datafile.
    :type overwrite: boolean
    :param kwargs: extra args

    """
    from .metadata import get_meta

    if not acquire_datafile_lock(df_id):
        return

    # Need to start a JVM in each thread
    check_and_start_jvm()

    try:
        javabridge.attach()
        log4j.basic_config()
        print(schema_name)
        schema = Schema.objects.get(namespace__exact=schema_name)
        df = DataFile.objects.get(id=df_id)
        if DatafileParameterSet.objects \
                .filter(schema=schema, datafile=df).exists():
            if overwrite:
                psets = DatafileParameterSet.objects.get(schema=schema,
                                                         datafile=df)
                logger.warning("Overwriting parametersets for %s",
                               df.filename)
                for ps in psets:
                    delete_old_parameterset(ps)
            else:
                logger.warning("Parametersets for %s already exist.",
                               df.filename)
                return

        dfo = DataFileObject.objects.filter(datafile__id=df.id,
                                            verified=True).first()
        input_file_path = dfo.get_full_path()

        output_rel_path = os.path.join(
            os.path.dirname(urlparse.urlparse(dfo.uri).path),
            str(df.id))
        output_path = os.path.join(
            settings.METADATA_STORE_PATH, output_rel_path)

        if not os.path.exists(output_path):
            os.makedirs(output_path)

        logger.debug("Processing file: %s" % input_file_path)
        metadata_params = get_meta(input_file_path, output_path, **kwargs)
        if not metadata_params:
            logger.debug("No metadata to save")
            return

        for sm in metadata_params:
            ps = DatafileParameterSet(schema=schema, datafile=df)
            ps.save()

            logger.debug("Saving parameters for: %s", input_file_path)
            save_parameters(schema, ps, sm)
    except Exception as err:
        logger.error(err)
    finally:
        release_datafile_lock(df_id)
        javabridge.detach()


@task(name="tardis_portal.filters.mytardisbf.process_meta", ignore_result=True)
def process_meta(df_id, schema_name, overwrite=False, **kwargs):
    """Extract metadata from a Datafile using the get_meta function and save the
    outputs as DatafileParameters.

    Parameters
    ----------
    :param df_id: ID of Datafile instance to process.
    :type df_id: int
    :param schema_name: Names of schema which describes ParameterNames
    :type schema_name: string
    :param overwrite: Specifies whether to overwrite any exisiting parametersets
        for this datafile.
    :type overwrite: boolean
    :param kwargs: extra args

    """
    from .metadata import get_meta

    if not acquire_datafile_lock(df_id):
        return

    # Need to start a JVM in each thread
    check_and_start_jvm()

    try:
        javabridge.attach()
        log4j.basic_config()
        schema = Schema.objects.get(namespace__exact=schema_name)
        df = DataFile.objects.get(id=df_id)
        if DatafileParameterSet.objects \
                .filter(schema=schema, datafile=df).exists():
            if overwrite:
                psets = DatafileParameterSet.objects.get(schema=schema,
                                                         datafile=df)
                logger.warning("Overwriting parametersets for %s",
                               df.filename)
                for ps in psets:
                    delete_old_parameterset(ps)
            else:
                logger.warning("Parametersets for %s already exist.",
                               df.filename)
                return

        dfo = DataFileObject.objects.filter(datafile__id=df.id,
                                            verified=True).first()
        input_file_path = dfo.get_full_path()

        logger.debug("Processing file: %s", input_file_path)
        metadata_params = get_meta(input_file_path, **kwargs)

        if not metadata_params:
            logger.debug("No metadata to save")
            return

        for sm in metadata_params:
            ps = DatafileParameterSet(schema=schema, datafile=df)
            ps.save()

            logger.debug("Saving parameters for: %s", input_file_path)
            save_parameters(schema, ps, sm)
    except Exception as err:
        logger.error(err)
    finally:
        release_datafile_lock(df_id)
        javabridge.detach()


class MetadataFilter(object):
    """MyTardis filter for extracting metadata from micrscopy image
    formats using the Bioformats library.

    Attributes
    ----------
    name: str
        Short name for schema
    schema: str
        Name of the schema to load the EXIF data into.
    """

    def __init__(self, name, schema):
        self.name = name
        self.schema = schema

    def __call__(self, sender, **kwargs):
        """Post save call back to invoke this filter.

        Parameters
        ----------
        :param sender: class of the model
        :type sender: class
        :param kwargs: extra args
        """
        instance = kwargs.get('instance')
        # bfqueue = getattr(settings, 'BIOFORMATS_QUEUE', 'celery')
        process_meta_file_output.apply_async(
            args=[instance.id, self.schema, False])


def make_filter(name, schema):
    return MetadataFilter(name, schema)


make_filter.__doc__ = MetadataFilter.__doc__
