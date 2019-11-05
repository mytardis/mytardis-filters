import os
import unittest

import filters.tests.helpers as helpers
from filters.filters.helpers import safe_import


class XlsxFilterTestCase(unittest.TestCase):

    def setUp(self):
        self.filter = helpers.get_filter_settings('XLSX')
        self.callable = safe_import(self.filter)

    def testThumbnail(self):
        # Create mockup variables
        fname = 'sample.xlsx'
        id = helpers.get_datafile_id()
        dsn = helpers.get_dataset_name()
        filename = helpers.create_datafile(fname, dsn)
        uri = os.path.join(dsn, fname)

        # Generate thumbnail
        results = self.callable(id, filename, uri)

        # Basic schema checks
        self.assertTrue(results is not None)
        self.assertTrue(isinstance(results, dict))
        self.assertTrue(
            'previewImage' in results and len(results['previewImage']))

        # Check that thumbnail file exists
        self.assertTrue(
            os.path.exists(helpers.get_thumbnail_file(results['previewImage'])))

        # Cleanup
        helpers.delete_datafile(uri)
