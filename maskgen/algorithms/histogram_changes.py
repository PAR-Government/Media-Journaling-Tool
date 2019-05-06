# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
import numpy as np
from math import log

def packImgBits(img, max_bits=5):
    """
    :param img:
    :param bits:
    :return:
    @type img: numpy.ndarray
    @type bits: int
    """
    hist, bin_edges = np.histogram(img, bins=range(np.max(img) + 2), )

    # shift the image histogram to th left to remove unused bins
    # find the second histogram bin that has more than 10 values
    # and subtract it from every pixel value
    adjustment_amount = np.argwhere(hist > 10)[1][0]
    bits = int(max(0,min(log(adjustment_amount)/log(2) + 1,max_bits)))
    img = img - adjustment_amount
    # drop the <bits> number of LSBs
    img = np.right_shift(img, bits)
    return img
