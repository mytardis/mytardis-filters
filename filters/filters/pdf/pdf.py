import os
import traceback
import logging

from ..helpers import fileFilter, get_thumbnail_paths, fileoutput

logger = logging.getLogger(__name__)


class PdfImageFilter(fileFilter):
    """
    This filter uses ImageMagick's convert to display a preview
    image of a PDF file.
    """

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
        if not filename.lower().endswith('.pdf'):
            return None

        logger.info("Applying PDF filter to {}...".format(filename))

        try:
            thumb_rel_path, thumb_abs_path = get_thumbnail_paths(id, filename,
                                                                 uri)

            if not os.path.exists(os.path.dirname(thumb_abs_path)):
                os.makedirs(os.path.dirname(thumb_abs_path))

            fileoutput('/usr/bin', 'convert',
                       [filename + '[0]',  # first page of PDF file
                        thumb_abs_path])

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
        raise ValueError("PdfImageFilter "
                         "requires a name to be specified")
    if not schema:
        raise ValueError("PdfImageFilter "
                         "requires a schema to be specified")
    return PdfImageFilter(name, schema, tagsToFind, tagsToExclude)


make_filter.__doc__ = PdfImageFilter.__doc__
