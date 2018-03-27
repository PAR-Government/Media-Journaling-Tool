# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import numpy as np
from maskgen.algorithms.optical_flow import OpticalFlow, FrameAnalyzer
from maskgen.image_wrap import openImageFile
from tests.test_support import TestSupport


class TestOpticalFlow(TestSupport):
    def test_mask_withsame_size(self):
        analyzer = FrameAnalyzer(199.87494824016565, 233.18743961352658, 33.31249137336093)
        f1 = openImageFile(self.locateFile('tests/algorithms/f1.png')).image_array
        f2 = openImageFile(self.locateFile('tests/algorithms/f2.png')).image_array
        analyzer.updateFlow(f1, f2, 'forward')
        flow_manager = OpticalFlow(f1, f2, analyzer.back_flow, analyzer.jump_flow)
        frame = flow_manager.setTime(0.0)
        self.assertEqual(0, np.sum(abs(frame - f1)))
        frame = flow_manager.setTime(0.1)
        self.assertTrue( np.sum(abs(frame - f1)) < np.sum(abs(frame - f2)))
        print np.sum(abs(frame - f2))
        frame = flow_manager.setTime(0.9)
        self.assertTrue(np.sum(abs(frame - f1)) > np.sum(abs(frame - f2)))
        frame = flow_manager.setTime(1.0)
        self.assertEqual(0, np.sum(abs(frame - f2)))
