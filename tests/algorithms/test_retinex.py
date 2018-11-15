import unittest
from maskgen.algorithms.retinex import *
from tests.test_support import TestSupport
import os
from maskgen.image_wrap import ImageWrapper, openImageFile
import numpy as np
#import colorcorrect.algorithm


from maskgen.image_wrap import ImageWrapper


class TestRetinex(TestSupport):

    def test_retinex(self):
        img = openImageFile(self.locateFile('tests/images/test_project4.jpg'))
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
                self.assertTrue(np.mean(res) > np.mean(img.to_array()))
                #ImageWrapper(res).save('cr_{}_ret.png'.format(f.__class__.__name__))


if __name__ == '__main__':
    unittest.main()
