from tardis.celery import tardis_app
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from .models.datafile import DataFile, DataFileObject
from importlib import import_module


def safe_import(path, args, kw):
    try:
        dot = path.rindex('.')
    except ValueError:
        raise ImproperlyConfigured('%s isn\'t a filter module' % path)
    filter_module, filter_classname = path[:dot], path[dot + 1:]
    try:
        mod = import_module(filter_module)
    except ImportError as e:
        raise ImproperlyConfigured('Error importing filter %s: "%s"' %
                                   (filter_module, e))
    try:
        filter_class = getattr(mod, filter_classname)
    except AttributeError:
        raise ImproperlyConfigured(
            'Filter module "%s" does not define a "%s" class' %
            (filter_module, filter_classname))

    filter_instance = filter_class(*args, **kw)
    return filter_instance


@tardis_app.task(name='mytardis.apply_filters', ignore_result=True)
def post_save_filters(dfo_id, **kwargs):
    print('apply_filters for id=', dfo_id)
    dfo = DataFileObject.objects.get(id=dfo_id)
    if dfo.verified:
        for filter in getattr(settings, 'POST_SAVE_FILTERS', []):
            filter_class = filter[0]
            filter_args = filter[1] if len(filter) > 1 else []
            filter_kwargs = filter[2] if len(filter) > 2 else {}
            callable = safe_import(filter_class, filter_args, filter_kwargs)
            callable(sender=DataFile, instance=dfo.datafile)
    else:
        print('DFO {} is not verified, skipping filters'.format(dfo_id))
