# -*- coding: utf-8 -*-
#
# Copyright (c) 2010-2011, Monash e-Research Centre
#   (Monash University, Australia)
# Copyright (c) 2010-2011, VeRSI Consortium
#   (Victorian eResearch Strategic Initiative, Australia)
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    *  Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#    *  Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#    *  Neither the name of the VeRSI, the VeRSI Consortium members, nor the
#       names of its contributors may be used to endorse or promote products
#       derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE REGENTS AND CONTRIBUTORS ``AS IS'' AND ANY
# EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE REGENTS AND CONTRIBUTORS BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

"""
diffractionimage.py

.. moduleauthor:: Steve Androulakis <steve.androulakis@gmail.com>
.. moduleauthor:: James Wettenhall <james.wettenhall@monash.edu>

"""
import logging
import os
import subprocess
import shutil
import sys
import tempfile

from ..helpers import fileFilter, get_thumbnail_paths

logger = logging.getLogger(__name__)


class DiffractionImageFilter(fileFilter):
    """This filter runs the CCP4 diffdump binary on a diffraction image
    and collects its output into the trddatafile schema

    param name: the short name of the schema.
    type name: string

    param schema: the name of the schema to load the EXIF data into.
    type schema: string

    return: Extracted metadata
    rtype: dict
    """
    def __init__(self, name, schema, tagsToFind=[], tagsToExclude=[]):
        super().__init__(name, schema, tagsToFind, tagsToExclude)
        self.name = name
        self.schema = schema
        self.diffdump_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../../../bin/ccp4-7.0/diff-image/%s/bin/diffdump" % sys.platform)
        self.diff2jpeg_path = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../../../bin/ccp4-7.0/diff-image/%s/bin/diff2jpeg" % sys.platform)

        # these values map across directly
        self.terms = {
            'Imagetype': "imageType",
            'Collectiondate': "collectionDate",
            'Exposuretime': "exposureTime",
            'DetectorS/N': "detectorSN",
            'Wavelength': "wavelength",
            'Distancetodetector': "detectorDistance",
            'TwoThetavalue': "twoTheta",
        }

        self.values = {
            'Imagetype': self.output_metadata,
            'Collectiondate': self.output_metadata,
            'Exposuretime': self.output_exposuretime,
            'DetectorS/N': self.output_metadata,
            'Wavelength': self.output_wavelength,
            'Beamcenter': self.output_beamcenter,
            'Distancetodetector': self.output_detectordistance,
            'ImageSize': self.output_imagesize,
            'PixelSize': self.output_pixelsize,
            'Oscillation(phi)': self.output_oscillation,
            'TwoThetavalue': self.output_twotheta,
        }

    def __call__(self, df_id, filepath, uri, **kwargs):
        """
        param df_id: Datafile ID
        type df_id: integer

        param filepath: Absolute path to a file for processing
        type filepath: string

        param uri: Dataset URI
        type uri: string

        param kwargs: Extra arguments
        type kwargs: object

        return Extracted metadata
        rtype dict
        """
        if not filepath.lower().endswith('.img') and \
                not filepath.lower().endswith('.osc'):
            return None

        logger.info(
            "Applying Diffraction Image filter to {}...".format(filepath))

        try:
            metadata = self.getDiffractionImageMetadata(filepath)

            thumb_rel_path, thumb_abs_path = \
                get_thumbnail_paths(df_id, filepath, uri, ext='jpg',
                                    replace_ext=True)
            previewImagePath = self.getDiffractionPreviewImage(
                filepath, thumb_abs_path)

            if previewImagePath:
                metadata['previewImage'] = thumb_rel_path

            return self.filter_metadata(metadata)
        except Exception as err:
            logger.exception(err)

    def getDiffractionImageMetadata(self, filepath):
        """Return a dictionary of the metadata.
        """
        ret = {}

        try:
            output = self.run_diffdump(filepath)

            tags = self.parse_output(output)
        except IOError:
            logger.exception()
            return ret

        for tag in tags:
            ret[tag['key']] = tag['value']
        return ret

    def getDiffractionPreviewImage(self, filepath, thumb_abs_path):
        """Generate a preview image and return its path.
        """
        try:
            previewImagePath = self.run_diff2jpeg(filepath, thumb_abs_path)

            return previewImagePath

        except IOError:
            logger.exception('')
            return None

    def parse_term(self, line):
        return line.split(':')[0].replace(' ', '')

    def parse_value(self, line):
        return line.split(':')[1].replace('\n', '').strip()

    def output_metadata(self, term, value):
        return {'key': self.terms[term], 'value': value}

    def output_exposuretime(self, term, value):
        return self.output_metadata(term, value.replace(' s', ''))

    def output_wavelength(self, term, value):
        return self.output_metadata(term, value.replace(' Ang', ''))

    def output_detectordistance(self, term, value):
        return self.output_metadata(term, value.replace(' mm', ''))

    def output_twotheta(self, term, value):
        return self.output_metadata(term, value.replace(' deg', ''))

    def split_output(self, terms, value, strip):
        values = value.split(',')
        split = []
        split.append({'key': terms[0],
                      'value': values[0][1:].replace(strip, '')})
        split.append({'key': terms[1],
                      'value': values[1][:-1].replace(strip, '')})
        return split

    def split_oscillation(self, terms, value):
        values = value.split('->')
        split = []
        split.append({'key': terms[0],
                      'value': values[0]})
        split.append({'key': terms[1],
                      'value': values[1][:-3]})
        return split

    def output_beamcenter(self, term, value):
        return self.split_output(['directBeamXPos', 'directBeamYPos'],
                                 value, 'mm')

    def output_imagesize(self, term, value):
        return self.split_output(['imageSizeX', 'imageSizeY'],
                                 value, 'px')

    def output_pixelsize(self, term, value):
        return self.split_output(['pixelSizeX', 'pixelSizeY'],
                                 value, 'mm')

    def output_oscillation(self, term, value):
        return self.split_oscillation(
            ['oscillationRangeStart', 'oscillationRangeEnd'], value)

    def parse_output(self, output):
        metadata = []
        for line in output.splitlines():
            term = self.parse_term(line)
            value = self.parse_value(line)

            try:
                value_outputs = self.values[term](term, value)

                if isinstance(value_outputs, list):

                    for value_output in value_outputs:

                        metadata.append(value_output)
                else:
                    metadata.append(value_outputs)

            except KeyError:
                logger.debug('no ' + term + ' found')

        return metadata

    def run_diffdump(self, file_path):
        split_diffdump_path = self.diffdump_path.rsplit('/', 1)
        cd = split_diffdump_path[0]
        diffdump_exec = split_diffdump_path[1]

        cmd = "cd '" + cd + "'; LD_LIBRARY_PATH=.:$LD_LIBRARY_PATH ./'" + \
            diffdump_exec + "' '" + file_path + "'"
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
        output, _ = proc.communicate()
        return output.decode()

    def run_diff2jpeg(self, filepath, thumb_abs_path):
        split_diff2jpeg_path = self.diff2jpeg_path.rsplit('/', 1)
        cd = split_diff2jpeg_path[0]
        diff2jpeg_exec = split_diff2jpeg_path[1]

        with tempfile.TemporaryDirectory() as tmpdir:
            shutil.copy(filepath, tmpdir)
            basename = os.path.basename(filepath)
            filepath = os.path.join(tmpdir, basename)
            cmd = "cd '" + cd + "'; LD_LIBRARY_PATH=.:$LD_LIBRARY_PATH ./'" + \
                diff2jpeg_exec + "' '" + filepath + "' "

            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                shell=True)

            result_str, _ = proc.communicate()
            if result_str.startswith(b'Exception'):
                return result_str

            diff2jpeg_result = "%s.jpg" % os.path.splitext(filepath)[0]
            target_dir = os.path.dirname(thumb_abs_path)
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            shutil.copyfile(diff2jpeg_result, thumb_abs_path)

            return thumb_abs_path


def make_filter(name='', schema='', tagsToFind=[], tagsToExclude=[]):
    if not name:
        raise ValueError("DiffractionImageFilter "
                         "requires a name to be specified")
    if not schema:
        raise ValueError("DiffractionImageFilter "
                         "requires a schema to be specified")
    return DiffractionImageFilter(name, schema, tagsToFind, tagsToExclude)


make_filter.__doc__ = DiffractionImageFilter.__doc__
