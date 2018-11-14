import unittest
import os
import sys
from maskgen import plugins
from maskgen.video_tools import get_shape_of_video
from maskgen import tool_set
from maskgen.cv2api import cv2api_delegate
from tests.test_support import TestSupport


class TestDroneShake(TestSupport):
    filesToKill = []

    def test_plugin(self):
        plugins.loadPlugins()
        filename = self.locateFile("tests/videos/sample1.mov")
        filename_output = os.path.join(os.path.split(filename)[0], "sample1_out.avi")
        self.filesToKill.append(filename_output)
        file = os.path.join(os.path.split(filename)[0], "sample1.csv")
        self.filesToKill.append(file)

        args, errors = plugins.callPlugin('DroneShake',
                                          None,  #image would go here for image manipulations
                                          filename,
                                          filename_output,
                                          fps=13.53,
                                          height=360,
                                          width=480)
        #  checking to make sure there are no errors
        self.assertEqual(errors, None)

        #  Get the output video to compare the height and width
        video = cv2api_delegate.videoCapture(filename_output)
        width = int(video.get(cv2api_delegate.prop_frame_width))
        height = int(video.get(cv2api_delegate.prop_frame_height))
        self.assertTrue(int(width) == 480)
        self.assertTrue(int(height) == 360)

    def tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)


if __name__ == '__main__':
    unittest.main()