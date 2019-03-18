from os import path

from django.test import TransactionTestCase

import tardis.tardis_portal.tests.helpers as helpers
from tardis.tardis_portal.filters.helpers import safe_import


class CsvFilterTestCase(TransactionTestCase):

    def setUp(self):
        self.filter = helpers.get_filter_settings('CSV')
        self.callable = safe_import(self.filter)

    def testThumbnail(self):
        # Create mockup variables
        fname = 'sample.csv'
        id = helpers.get_datafile_id()
        dsn = helpers.get_dataset_name()
        filename = helpers.create_datafile(fname, dsn)
        uri = path.join(dsn, fname)

        # Generate thumbnail
        results = self.callable(id, filename, uri)

        # Basic schema checks
        self.assertTrue(isinstance(results, dict))
        self.assertTrue(
            'previewImage' in results and len(results['previewImage']))

        # Check that thumbnail file exists
        self.assertTrue(
            path.exists(helpers.get_thumbnail_file(results['previewImage'])))

        # Cleanup
        helpers.delete_datafile(uri)
