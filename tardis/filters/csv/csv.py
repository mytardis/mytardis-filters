import os
import traceback
import logging

from ..helpers import fileFilter, get_thumbnail_paths, fileoutput

logger = logging.getLogger(__name__)


class CsvImageFilter(fileFilter):
    """
    This filter uses Gnumeric's ssconvert to generate a
    preview image for a CSV (comma-separated values) file.
    """

    def __init__(self, name, schema, ssconvert,
                 tagsToFind=[], tagsToExclude=[]):
        super().__init__(name, schema, tagsToFind, tagsToExclude)
        self.ssconvert = ssconvert

    def __call__(self, id, filename, uri, **kwargs):
        """
        param id: Datafile ID
        type id: integer

        param filename: Absolute path to a file for processing
        type filename: string

        param uri: Dataset URI
        type uri: string

        param kwargs: Extra arguments
        type kwargs: object

        return Extracted metadata
        rtype dict
        """
        if not filename.lower().endswith('.csv'):
            return None

        logger.info("Applying CSV filter to {}...".format(filename))

        try:
            thumb_rel_path, thumb_abs_path = get_thumbnail_paths(id, filename,
                                                                 uri)

            if not os.path.exists(os.path.dirname(thumb_abs_path)):
                os.makedirs(os.path.dirname(thumb_abs_path))

            # Create file name for PDF temp file
            pdf_abs_path = os.path.splitext(thumb_abs_path)[0] + '.pdf'

            ssconvert_path = os.path.dirname(self.ssconvert)
            ssconvert_bin = os.path.basename(self.ssconvert)

            logger.info("ssconvert: path={}, bin={}".format(ssconvert_path,
                                                            ssconvert_bin))

            # Create PDF file from CSV file
            fileoutput(ssconvert_path, ssconvert_bin, [filename, pdf_abs_path])

            if os.path.exists(pdf_abs_path):
                # Create thumbnail
                fileoutput('/usr/bin', 'convert',
                           ['-flatten -density 300 -background white',
                            pdf_abs_path + '[0]',  # first page of PDF file
                            thumb_abs_path])
                # Delete PDF file
                os.remove(pdf_abs_path)
            else:
                logger.error("Can't find PDF file {}".format(pdf_abs_path))

            if os.path.exists(thumb_abs_path):
                return self.filter_metadata({
                    'previewImage': thumb_rel_path
                })

        except Exception as e:
            logger.debug(str(e))
            print(traceback.format_exc())

        return None


def make_filter(name='', schema='', tagsToFind=[], tagsToExclude=[]):
    if not name:
        raise ValueError("CsvImageFilter "
                         "requires a name to be specified")
    if not schema:
        raise ValueError("CsvImageFilter "
                         "requires a schema to be specified")
    return CsvImageFilter(name, schema, tagsToFind, tagsToExclude)


make_filter.__doc__ = CsvImageFilter.__doc__
