import logging
import os
from xml.etree import ElementTree as et

import javabridge  # pylint: disable=import-error
import bioformats  # pylint: disable=import-error

from .previewimage import get_preview_image, save_image

logger = logging.getLogger(__name__)


def get_original_metadata(omexml):
    """ Get the original metadata from structured annotations in OME XML.
    Note: this is currently not used at this stage.

    Parameters
    ----------
    :param omexml: OME XML metadata
    :type omexml: string

    Returns
    -------
    :return: Dict containing key and value pairs for each original
        metadata element
    :rtype: dict

    """
    meta_xml = et.fromstring(omexml.encode('utf-8'))
    sa = '{http://www.openmicroscopy.org/' \
         'Schemas/SA/2013-06}StructuredAnnotations/' \
         '{http://www.openmicroscopy.org/Schemas/SA/2013-06}XMLAnnotation/' \
         '{http://www.openmicroscopy.org/Schemas/SA/2013-06}Value/' \
         '{http://www.openmicroscopy.org/Schemas/SA/2013-06}OriginalMetadata'

    return dict([
        (
            elem.find(
                '{http://www.openmicroscopy.org/Schemas/SA/2013-06}Key').text,
            elem.find(
                '{http://www.openmicroscopy.org/Schemas/SA/2013-06}Value').text
        ) for elem in meta_xml.findall(sa)
    ])


def get_namespaces(meta_xml_root):
    """Extract OME and StructuredAnnotation namespaces from OME-XML file

    Parameters
    ----------
    :param meta_xml_root: Root ElementTree element
    :type meta_xml_root: element

    Returns
    -------
    :return: Dictionary with the OME and SA namespaces
    :rtype: dict

    """
    ome_ns = meta_xml_root.tag[1:].split("}", 1)[0]
    sa_ns = ome_ns.replace("OME", "SA")
    return {'ome': ome_ns, 'sa': sa_ns}


def get_meta(input_file_path, output_path, **kwargs):
    """ Extract specific metadata typically used in bio-image analysis. Also
    outputs a preview image to the output directory.

    Parameters
    ----------
    :param input_file_path: Path to the input file
    :type input_file_path: string
    :param output_path: Path to the output file
    :type output_path: string
    :param kwargs: extra args
    :type kwargs: object

    Returns
    -------
    :return: List of dicts containing with keys and values for specific metadata
    :rtype: dict

    """
    pix_exc = set(["id", "significantbits", "bigendian", "interleaved"])
    channel_exc = set(["color", "id", "color", "contrastmethod", "fluor",
                       "ndfilter", "illuminationtype", "name",
                       "pockelcellsetting", "acquisitionmode"])
    input_fname, ext = os.path.splitext(os.path.basename(input_file_path))
    if ext[1:] not in bioformats.READABLE_FORMATS:
        logger.debug("Unsupported format: %s.%s" % (input_fname, ext))
        return None

    try:
        omexml = bioformats.get_omexml_metadata(input_file_path).encode('utf-8')
    except javabridge.jutil.JavaException:
        logger.error("Unable to read OME Metadata from: %s", input_file_path)
        return None

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
            for k, v in pix_meta.attrib.iteritems():
                if k.lower() not in pix_exc:
                    smeta[k.lower()] = v

            for c, channel_meta in enumerate(
                    pix_meta.findall('ome:Channel', ome_ns)):
                for kc, vc in channel_meta.attrib.iteritems():
                    if kc.lower() in channel_exc:
                        continue
                    if kc.lower() not in smeta:
                        smeta[kc.lower()] = ["Channel %s: %s" % (c, vc)]
                    else:
                        smeta[kc.lower()].append("Channel %s: %s" % (c, vc))

        meta.append(smeta)

    return meta


def get_ome_metadata(input_file_path, output_path, **kwargs):
    """ Extracts metadata from an input file and save it to a file at
    the specified output_path.
    Note: this is currently not used at this stage.

    Parameters
    ----------
    :param input_file_path: Path to the input file
    :type input_file_path: string
    :param output_path: Path to the output file
    :type output_path: string
    :param kwargs: extra args
    :type kwargs: object

    Returns
    -------
    :return: Path to the output file
    :rtype: dict

    :raises Exception: bla

    """
    input_fname, ext = os.path.splitext(os.path.basename(input_file_path))
    if ext[1:] not in bioformats.READABLE_FORMATS:
        raise Exception("Unsupported format: %s.%s" % (input_fname, ext))

    meta_xml = bioformats.get_omexml_metadata(input_file_path)

    output_file_path = os.path.join(output_path, input_fname + ".xml")
    with open(output_file_path, "w") as f:
        f.write(meta_xml.encode('utf-8'))

    return {"ome": output_file_path}
