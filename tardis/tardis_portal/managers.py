"""
managers.py

.. moduleauthor::  Ulrich Felzmann <ulrich.felzmann@versi.edu.au>

"""

from django.db import models


class OracleSafeManager(models.Manager):
    """
    Implements a custom manager which automatically defers the
    retreival of any TextField fields on calls to get_queryset. This
    is to avoid the known issue that 'distinct' calls on query_sets
    containing TextFields fail when Oracle is being used as the
    backend.
    """

    def get_queryset(self):
        from django.db import connection
        if connection.settings_dict['ENGINE'] == 'django.db.backends.oracle':
            fields = [a.attname for a in self.model._meta.fields
                      if a.db_type(connection=connection) == 'NCLOB']
            return \
                super(OracleSafeManager, self).get_queryset().defer(*fields)
        return super(OracleSafeManager, self).get_queryset()


class ParameterNameManager(models.Manager):
    def get_by_natural_key(self, namespace, name):
        return self.get(schema__namespace=namespace, name=name)


class SchemaManager(models.Manager):
    def get_by_natural_key(self, namespace):
        return self.get(namespace=namespace)
