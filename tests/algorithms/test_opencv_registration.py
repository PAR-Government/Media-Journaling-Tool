import cv2
from maskgen.algorithms.opencv_registration import OpenCVECCRegistration
from tests.test_support import TestSupport


class TestOpenCVRegistration(TestSupport):
    def test_ecc_registration(self):
        if not (int(cv2.__version__[0]) == 3):
            return
        base = self.locateFile('images/algorithms/20180909_110816_001.jpg')
        to_align = self.locateFile('images/algorithms/20180909_110816_002.jpg')
        reg = OpenCVECCRegistration(base)
        transform = reg.align(to_align)
        # Homography not being used yet
        # homography = reg.align(to_align, cv2.MOTION_HOMOGRAPHY)
        self.assertTrue(transform is not None)
        # self.assertTrue(homography is not None)
