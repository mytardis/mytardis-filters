import os
import traceback
import logging

from xml.etree import ElementTree as et
import numpy as np
from scipy.ndimage import zoom

import javabridge
import bioformats
from bioformats import log4j

from django.conf import settings

from ..helpers import fileFilter, get_thumbnail_paths

logger = logging.getLogger(__name__)

mtbf_jvm_started = False  # Global to check whether JVM started on a thread


def check_and_start_jvm():
    """
    Checks global to see whether a JVM is running and if not starts
    a new one. If JVM starts successfully the global variable mtbf_jvm_started
    is updated to ensure that another JVM is not started.
    """
    global mtbf_jvm_started
    if not mtbf_jvm_started:
        logger.debug('Starting a new JVM')
        try:
            mh_size = getattr(settings, 'MTBF_MAX_HEAP_SIZE', '4G')
            javabridge.start_vm(class_path=bioformats.JARS,
                                max_heap_size=mh_size,
                                run_headless=True)
            mtbf_jvm_started = True
        except javabridge.JVMNotFoundError as e:
            logger.debug(e)


def get_namespaces(meta_xml_root):
    """
    Extract OME and StructuredAnnotation namespaces from OME-XML file

    param meta_xml_root: Root ElementTree element
    type meta_xml_root: element

    return: Dictionary with the OME and SA namespaces
    rtype: dict
    """
    ome_ns = meta_xml_root.tag[1:].split("}", 1)[0]
    sa_ns = ome_ns.replace("OME", "SA")
    return {'ome': ome_ns, 'sa': sa_ns}


def get_meta(input_file_path, output_path, **kwargs):
    """
    Extract specific metadata typically used in bio-image analysis. Also
    outputs a preview image to the output directory.

    param input_file_path: Path to the input file
    type input_file_path: string

    param output_path: Path to the output file
    type output_path: string

    param kwargs: extra args
    type kwargs: object

    return: List of dicts containing with keys and values for specific metadata
    rtype: dict

    """
    pix_exc = set(["id", "significantbits", "bigendian", "interleaved"])
    channel_exc = set(["color", "id", "color", "contrastmethod", "fluor",
                       "ndfilter", "illuminationtype", "name",
                       "pockelcellsetting", "acquisitionmode"])

    try:
        omexml = bioformats.get_omexml_metadata(input_file_path).encode('utf-8')
    except javabridge.jutil.JavaException:
        logger.error("Unable to read OME Metadata from: %s", input_file_path)
        return None

    input_fname, _ = os.path.splitext(os.path.basename(input_file_path))

    meta_xml = et.fromstring(omexml)
    ome_ns = get_namespaces(meta_xml)
    meta = list()
    for i, img_meta in enumerate(meta_xml.findall('ome:Image', ome_ns)):
        smeta = dict()
        output_file_path = os.path.join(output_path,
                                        input_fname + "_s%s.png" % i)
        logger.debug("Generating series %s preview from image: %s",
                     i, input_file_path)
        img = get_preview_image(input_file_path, omexml, series=i)
        logger.debug("Saving series %s preview from image: %s",
                     i, input_file_path)
        save_image(img, output_file_path, overwrite=True)
        logger.debug("Extracting metadata for series %s preview from image: %s",
                     i, input_file_path)
        smeta['id'] = img_meta.attrib['ID']
        smeta['name'] = img_meta.attrib['Name']
        smeta['previewImage'] = output_file_path
        for pix_meta in img_meta.findall('ome:Pixels', ome_ns):
            for k, v in pix_meta.attrib.items():
                if k.lower() not in pix_exc:
                    smeta[k.lower()] = v

            for c, channel_meta in enumerate(
                    pix_meta.findall('ome:Channel', ome_ns)):
                for kc, vc in channel_meta.attrib.items():
                    if kc.lower() in channel_exc:
                        continue
                    if kc.lower() not in smeta:
                        smeta[kc.lower()] = ["Channel %s: %s" % (c, vc)]
                    else:
                        smeta[kc.lower()].append("Channel %s: %s" % (c, vc))

        meta.append(smeta)

    return meta


def stretch_contrast(img):
    """Simple linear contrast stretch

    Parameters
    ----------
    :param img: N x M array of grayscale image intensities
    :type img: numpy.ndarray

    Returns
    -------
    :return: Output image with contrast stretch over the 8-bit range.
    :rtype: numpy.ndarray (dtype = np.int8)

    """

    s = np.subtract(img, np.min(img))
    p = 255.0 / (np.max(img) - np.min(img))
    out = np.round(np.multiply(s, p)).astype(np.uint8)

    return out


def get_preview_image(fname, meta_xml=None, maxwh=256, series=0):
    """ Generate a thumbnail of an image at the specified path. Gets the
    middle Z plane of channel=0 and timepoint=0 of the specified series.

    Parameters
    ----------
    :param fname: Path to image file.
    :type fname: string
    :param meta_xml: OME XML metadata.
    :type meta_xml: string
    :param maxwh: Maximum width or height of the output thumbnail. If the
        extracted image is larger in either x or y, the image will will be
        downsized to fit.
    :type maxwh: int
    :param series: Series for multi-stack formats (default=0)
    :type series: int

    Returns
    -------
    :return: N x M array of grayscale pixel intentsities.
    :rtype: numpy.ndarray

    :raises Exception: bla

    """
    name, ext = os.path.splitext(os.path.basename(fname))

    if ext[1:] not in bioformats.READABLE_FORMATS:
        raise Exception("Format not supported: %s" % ext[1:])

    if not meta_xml:
        meta_xml = bioformats.get_omexml_metadata(fname)

    ome = bioformats.OMEXML(meta_xml.decode('utf-8'))

    if series > ome.get_image_count():
        raise Exception("Specified series number %s exceeds number of series "
                        "in the image file: %s" % (series, fname))

    # Get metadata for first series
    meta = ome.image(0).Pixels

    # Determine resize factor
    sizex = meta.SizeX
    sizey = meta.SizeY
    if sizex > maxwh or sizey > maxwh:
        f = min(float(maxwh) / float(sizex), float(maxwh) / float(sizey))
    else:
        f = max(float(maxwh) / float(sizex), float(maxwh) / float(sizey))

    # Determine which Z slice
    z = 0

    # Determine middle Z plane
    # Note: SizeZ doesn't seem to be reliable. Might need to check BF.
    # Stick with first slice for now.
    # if meta.SizeZ > 1:
    #     z = int(math.floor(float(meta.SizeZ)/2))

    # Load image plane
    if meta.channel_count == 1 and meta.SizeC == 4:
        # RGB Image
        img = bioformats.load_image(fname, t=0, z=z, series=series,
                                    rescale=False)
        return zoom(img, (f, f, 1))

    # Grayscale, grab channel 0 only
    img = bioformats.load_image(fname, c=0, t=0, z=z, series=series,
                                rescale=False)
    # if img.dtype in (np.uint16, np.uint32, np.int16, np.int32):
    img = stretch_contrast(img)
    return zoom(img, f)


def save_image(img, output_path, overwrite=False):
    """
    Extract and save a preview image for an input image

    param img: N x M array of grayscale pixel intentsities.
    type img: ndarray

    param output_path: Path to which the output file is to be saved.
    type output_path: string

    param overwrite: Specifies whether or not to overwrite an existing file if
        a file already exist at the output path.
    type overwrite: bool

    raises Exception: bla
    """
    if os.path.exists(output_path):
        if not overwrite:
            raise Exception("Ouput file %s already exists and parameter"
                            "overwrite=False" % output_path)
        os.remove(output_path)

    bioformats.write_image(output_path, img, bioformats.PT_UINT8)


class BioformatsFilter(fileFilter):
    """
    MyTardis filter for extracting metadata from micrscopy image
    formats using the Bioformats library.
    """

    def __call__(self, id, filename, uri, **kwargs):
        """
        Extract metadata from a Datafile using the get_meta function and save
        the outputs as DatafileParameters. This function differs from
        process_meta in that it generates an output directory in the metadata
        store and passes it to the metadata processing func so that outputs
        e.g., preview images or metadata files) can be saved.

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

        _, extension = os.path.splitext(filename)
        if extension[1:] not in bioformats.READABLE_FORMATS:
            return None

        logger.info("Applying Bioformats filter to {}...".format(filename))

        # Need to start a JVM in each thread
        check_and_start_jvm()

        try:
            javabridge.attach()
            log4j.basic_config()

            thumb_rel_path, thumb_abs_path = get_thumbnail_paths(id, filename,
                                                                 uri)

            if not os.path.exists(os.path.dirname(thumb_abs_path)):
                os.makedirs(os.path.dirname(thumb_abs_path))

            rsp = get_meta(filename, os.path.dirname(thumb_abs_path), **kwargs)
            if rsp is not None:
                metadata = []
                for i in rsp:
                    metadata.append(self.filter_metadata(i))
                return metadata[0]

        except Exception as e:
            logger.error(str(e))
            logger.debug(traceback.format_exc())
        finally:
            javabridge.detach()
            javabridge.kill_vm()

        return None


def make_filter(name='', schema='',
                tagsToFind=[], tagsToExclude=[]):
    if not name:
        raise ValueError("BioformatsFilter "
                         "requires a name to be specified")
    if not schema:
        raise ValueError("BioformatsFilter "
                         "requires a schema to be specified")
    return BioformatsFilter(name, schema,
                            tagsToFind, tagsToExclude)


make_filter.__doc__ = BioformatsFilter.__doc__
