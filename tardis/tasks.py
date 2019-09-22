import traceback
import logging
import os

from django.conf import settings

from tardis.celery import app
from tardis.filters.helpers import safe_import, acquire_lock, \
    release_lock

logger = logging.getLogger(__name__)


@app.task(name='mytardis.apply_filters')
def apply_filters(id, verified, filename, uri):
    # Accept task
    logger.info("Applying filters for datafile id={}".format(id))

    # Do not process unverified files
    if not verified:
        logger.warning(
            'Datafile (id={}) is not verified, skipping filters'.format(id))
    else:
        # Create sub-task for each filter
        for filter in getattr(settings, 'POST_SAVE_FILTERS', []):
            _, extension = os.path.splitext(filename)
            if extension[1:] in filter[0][1]:
                logger.info("Apply: filter={}, id={}, filename={}".format(
                    filter[0][0], id, filename))
                # Run task asynchronously
                run_filter.apply_async(args=[filter, id, filename, uri])


@app.task
def run_filter(filter, id, filename, uri):
    # Accept task
    logger.info("Run: filter={}, id={}, filename={}".format(
        filter[0][0], id, filename))

    # Import filter
    callable = safe_import(filter)

    # Lock filter call
    lock_id = "filter-{}-{}".format(filter[1][0].lower(), id)
    if acquire_lock(lock_id, 300):  # 5 mins lock
        try:
            # Run filter
            metadata = callable(id, filename, uri)
            if metadata is None:
                # Something gone wrong
                s = "Can't get metadata for filter={}, id={}, filename={}"
                logger.error(s.format(filter[0][0], id, filename))
            else:
                # Send metadata back to mothership
                app.send_task(
                    'tardis_portal.datafile.save_metadata',
                    args=[
                        id,
                        filter[1][0],  # name
                        filter[1][1],  # schema
                        metadata
                    ],
                    queue=settings.API_QUEUE,
                    priority=settings.API_TASK_PRIORITY
                )
        except Exception as e:
            logger.error(str(e))
            logger.debug(traceback.format_exc())
        finally:
            # Unlock
            release_lock(lock_id)
