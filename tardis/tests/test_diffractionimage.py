from os import path

from django.test import TransactionTestCase

import tardis.tests.helpers as helpers
from tardis.filters.helpers import safe_import


class DiffractionImageFilterTestCase(TransactionTestCase):

    def setUp(self):
        self.filter = helpers.get_filter_settings('IMG')
        self.callable = safe_import(self.filter)

    def testThumbnail(self):
        # Create mockup variables
        fname = 'sample.img'
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
        thumbnail_path = helpers.get_thumbnail_file(results['previewImage'])
        self.assertTrue(
            path.exists(thumbnail_path),
            "Path %s doesn't exist" % thumbnail_path)

        # Check for metadata
        self.assertEqual(results['detectorSN'], "457")
        self.assertEqual(results['wavelength'], "0.953700")

        # Cleanup
        helpers.delete_datafile(uri)
