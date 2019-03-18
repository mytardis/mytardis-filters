from os import path

from django.test import TransactionTestCase

import tardis.tardis_portal.tests.helpers as helpers
from tardis.tardis_portal.filters.helpers import safe_import


class BioformatsFilterTestCase(TransactionTestCase):

    def setUp(self):
        self.filter = helpers.get_filter_settings('Bioformats')
        self.callable = safe_import(self.filter)

    def testThumbnail(self):
        # Create mockup variables
        fname = 'sample.nd2'
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

        # Extracted metadata check
        self.assertTrue(
            'name' in results and results['name'] == 'sample.nd2 (series 1)')
        self.assertTrue(
            'id' in results and results['id'] == 'Image:0')
        self.assertTrue(
            'dimensionorder' in results and results[
                'dimensionorder'] == 'XYZCT')

        # Cleanup
        helpers.delete_datafile(uri)
