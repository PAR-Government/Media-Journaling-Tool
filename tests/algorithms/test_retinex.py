import unittest
from maskgen.algorithms.retinex import *
from tests.test_support import TestSupport
import os
from maskgen.image_wrap import ImageWrapper, openImageFile
import numpy as np
import colorcorrect.algorithm

from maskgen.image_wrap import ImageWrapper


class TestRetinex(TestSupport):
    def xtest_retinex_cv2(self):
        filename = self.locateFile('/Users/ericrobertson/Downloads/18383430354_eb02337422_o.jpg')
        img = openImageFile(filename)
        o = simplestColorBalance(img.to_array(), 0.001, 0.999)
       # ret = colorcorrect.algorithm.retinex_with_adjust(img.to_array())
        ImageWrapper(o.astype('uint8')).save('parvo.png')


    def test_retinex(self):
        name = 'bird'
        ret = openImageFile('/Users/ericrobertson/Downloads/MSR_original/bird_gray.png')
        filename = self.locateFile('/Users/ericrobertson/Downloads/{}.png'.format(name))
        img = openImageFile(filename)
        for f in [MultiScaleResinex([15,80,125],
            G=30,
            b=-6,
            alpha=125.0,
            beta=1.0,
            colorBalance=(0.01,0.99)),
                  MultiScaleResinexLab([15,80,125],
            G=30,
            b=-6,
            alpha=125.0,
            beta=1.0,
            colorBalance=(0.01, 0.99)),
                  MultiScaleResinexChromaPerservation([15,80,125],
            G=30,
            b=-6,
            alpha=125.0,
            beta=1.0,
            colorBalance=(0.01, 0.99))
                  ]:
                res = f(img.to_array())
                ImageWrapper(res).save('cr_{}_ret.png'.format(f.__class__.__name__))


if __name__ == '__main__':
    unittest.main()
