import traceback
import os
import json
import logging

from pymemcache.client.base import Client

from filters.settings import config
from filters.worker import app
from filters.filters.helpers import safe_import

logger = logging.getLogger(__name__)


def json_serializer(key, value):
    if isinstance(value, str):
        return value, 1
    return json.dumps(value), 2


def json_deserializer(key, value, flags):
    if flags == 1:
        return value
    if flags == 2:
        return json.loads(value)
    raise Exception("Unknown serialization format")


# Memcached client
cache = Client(
    (config['memcached']['host'], config['memcached']['port']),
    serializer=json_serializer,
    deserializer=json_deserializer
)


def acquire_lock(lock_id, expire=60):
    if cache.get(lock_id) is not None:
        return False
    cache.set(lock_id, 1, expire)
    return True


def release_lock(lock_id):
    cache.delete(lock_id)


@app.task(name='apply_filters')
def apply_filters(df_id, verified, filename, uri):
    # Accept task
    logger.debug('df=%s: apply filters %s', df_id, filename)

    # Do not process unverified files
    if not verified:
        logger.debug(
            'df_id=%s: not verified, skipping', df_id)
    else:
        # Check if file exists
        if os.path.exists(filename):
            # Create sub-task for each filter
            for filter in getattr(config, 'post_save_filters', []):
                _, extension = os.path.splitext(filename)
                if extension[1:] in filter[0][1]:
                    logger.info('df_id=%s: apply %s', df_id, filter[0][0])
                    # Run task asynchronously
                    run_filter.apply_async(args=[filter, df_id, filename, uri])
        else:
            logger.error('df=%s: file does not exist (%s)', df_id, filename)


@app.task
def run_filter(filter, df_id, filename, uri):
    # Accept task
    logger.debug('df_id=%s: run %s', df_id, filter[0][0])

    # Import filter
    callable = safe_import(filter)

    # Lock filter call
    lock_id = "filter-{}-{}".format(filter[1][0].lower(), df_id)
    if acquire_lock(lock_id, 300):  # 5 mins lock
        try:
            # Run filter
            metadata = callable(df_id, filename, uri)
            if metadata is None:
                # Something gone wrong
                logger.error('df_id=%s: can\'t get metadata for %s',
                             df_id, filter[0][0])
            else:
                # Send metadata back to mothership
                q = config['queues']['api']
                app.send_task(
                    'tardis_portal.datafile.save_metadata',
                    args=[
                        df_id,
                        filter[1][0],  # name
                        filter[1][1],  # schema
                        metadata
                    ],
                    queue=q['name'],
                    priority=q['task_priority']
                )
        except Exception as e:
            logger.error('df=%s: an error occurred', df_id)
            logger.error(str(e))
            logger.debug(traceback.format_exc())
        finally:
            # Unlock
            release_lock(lock_id)
