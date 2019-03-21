from os import path

from django.test import TransactionTestCase

import tardis.tests.helpers as helpers
from tardis.filters.helpers import safe_import


class BioformatsFilterTestCase(TransactionTestCase):

    def setUp(self):
        self.filter = helpers.get_filter_settings('Bioformats')
        self.callable = safe_import(self.filter)

    def atestSimple(self):
        # Create mockup variables
        fname = 'sample.nd2'
        id = helpers.get_datafile_id()
        dsn = helpers.get_dataset_name()
        filename = helpers.create_datafile(fname, dsn)
        uri = path.join(dsn, fname)

        # Generate thumbnail and extract metadata
        results = self.callable(id, filename, uri)
        print(results)

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

    def testMulti(self):
        # Create mockup variables
        fname = 'z-series.ome.tif'
        id = helpers.get_datafile_id()
        dsn = helpers.get_dataset_name()
        filename = helpers.create_datafile(fname, dsn)
        uri = path.join(dsn, fname)

        # Generate thumbnails and extract metadata
        results = self.callable(id, filename, uri)
        # print(results)

        # Basic schema checks
        self.assertTrue(isinstance(results, dict))
        self.assertTrue(
            'previewImage' in results and len(results['previewImage']))

        # Check that thumbnail file exists
        self.assertTrue(
            path.exists(helpers.get_thumbnail_file(results['previewImage'])))

        # Extracted metadata check
        self.assertTrue(
            'name' in results and results['name'] == 'z-series.ome.tif')
        self.assertTrue(
            'id' in results and results['id'] == 'Image:0')
        self.assertTrue(
            'dimensionorder' in results and results[
                'dimensionorder'] == 'XYCZT')
        self.assertTrue(
            'sizex' in results and results['sizex'] == '439')
        self.assertTrue(
            'sizey' in results and results['sizey'] == '167')
        self.assertTrue(
            'sizez' in results and results['sizez'] == '5')
        self.assertTrue(
            'sizec' in results and results['sizec'] == '1')
        self.assertTrue(
            'sizet' in results and results['sizet'] == '1')

        # Cleanup
        helpers.delete_datafile(uri)
