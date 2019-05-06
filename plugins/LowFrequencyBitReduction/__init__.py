# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import numpy as np
from maskgen.algorithms.histogram_changes import packImgBits
from maskgen.image_wrap import ImageWrapper
from maskgen.support import getValue
import maskgen
"""
 When working with images with bit depths greater than 8bpp, some apps like
 photoshop scale the image across the full range of 16 bit values. This can
 introduce unused values in the image histogram. This is an issue when working
 with overherad iamges which may limit the range to 11 to 14 actual bpp.
 This function will compress the value range to fit in the specified number
 of bits.
"""

def transform(im, source, target, **kwargs):
    target_wrapper = ImageWrapper(packImgBits(np.asarray(im),
                                              int(getValue(kwargs,'max bits to shift',8))))
    target_wrapper.save(target)
    return None, None

def operation():
    return {
        'name': 'BitRescale',
        'category': 'AntiForensic',
        'description': 'By shifting bits of every pixel to the left, limit the range of values over the histogram of all intensity values',
        'software': 'PAR',
        'version':  maskgen.__version__,
        'arguments': {
            "max bits to shift": {
                "type":"int[3:8]",
                "description": "Number of bits shift left, compressing the value range"
            }
        },
        'transitions': [
            'image.image'
        ]
    }

def suffix():
    return '.png'
