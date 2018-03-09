# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from __future__ import division
from maskgen.image_wrap import ImageWrapper,openImageFile
import subprocess
import platform
import os
import logging

"""
Convert donor to png and resize to fit source dimensions
using Liquid Rescale plugin of GIMP.
"""
gimpfile = os.getenv('MASKGEN_GIMP')
if gimpfile is None:
    if "Darwin" in platform.platform():
        gimpfile = "DYLD_LIBRARY_PATH=/Applications/GIMP.app/Contents/Resources/lib:$DYLD_LIBRARY_PATH /Applications/GIMP.app/Contents/MacOS/GIMP"
    else:
        gimpfile = "gimp-2.8"

lqr_command = "batch-gimp-lqr"

def resizeUsingLQR(fpn, sizeNew):
    # Compose command line string that calls GIMP plugin Liquid Rescale
    lqrCommandLine = [gimpfile,
                           "-i",
                           "-f",
                           "-b",
                           "\"({} \\\"{}\\\" {} {})\"".format(lqr_command, fpn.replace("\\","\\\\"), str(sizeNew[0]),str(sizeNew[1])),
                           "-b",
                           "\"(gimp-quit -0)\""]
    pcommand= subprocess.Popen(" ".join(lqrCommandLine), shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    stdout, stderr = pcommand.communicate()
    if stderr is not None and 'Error' in stderr:
        logging.getLogger('maskgen').error(stderr)
        raise IOError('Failed to execute plugin')



def valtestExcludeSameSize(sizSource=(0, 0), sizDonor=(0, 0)):
    if sizSource == sizDonor:
        raise ValueError('LQR images are the same size')

def valtestExcludeSizeNotWithinPercent(sizSource=(0, 0), sizDonor=(0, 0), nPercent=20):
    if abs((sizSource[0] - sizDonor[0]) / sizSource[0]) > nPercent / 100.0:
        raise ValueError('LQR image sizes are too different')
    if abs((sizSource[1] - sizDonor[1]) / sizSource[1]) > nPercent / 100.0:
        raise ValueError('LQR image sizes are too different')


def validateImageSizes(sizSource=(0, 0), sizDonor=(0, 0), nPercent=20):
    valtestExcludeSameSize(sizSource, sizDonor)
    valtestExcludeSizeNotWithinPercent(sizSource, sizDonor, 20)

def transform(img, source, target, **kwargs):
    donor = kwargs['donor']
    sizSource = img.size
    sizDonor = openImageFile(donor).size
    validateImageSizes(sizSource, sizDonor)
    # Use Liquid Rescale to resize donor image
    # to size of source image.
    resizeUsingLQR(target, sizDonor)
    return None, None


def operation():
    return {'name': 'TransformSeamCarving',
            'category': 'Transform',
            'description': 'Resize donor to size of Input using LQR. Requires GIMP.  Set environment variable MASKGEN_GIMP to the gimp binary',
            'software': 'GIMP',
            'version': '2.8.20',
            'arguments': {
                'donor': {
                    'type': 'donor',
                    'defaultvalue': None,
                    'description': 'png that contributes size info'
                },
                'percentage bounds': {
                    'type': 'int',
                    'defaultvalue': 20,
                    'description': 'Proximity '
                }
            },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return '.png'
