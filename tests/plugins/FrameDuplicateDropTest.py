import unittest
import os
from maskgen import plugins, video_tools
from tests.test_support import TestSupport

class TestDuplicateDrop(TestSupport):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_plugin(self):
        filename= self.locateFile('tests/videos/sample1.mov')
        filename_output = os.path.join(os.path.dirname(os.path.abspath(filename)), 'sample_out1a.avi')

        self.filesToKill.append(filename_output)
        args, error = plugins.callPlugin('FrameDuplicateDrop',None,filename,filename_output,Threshold=3)
        capin = video_tools.cv2api_delegate.videoCapture(filename)
        capout = video_tools.cv2api_delegate.videoCapture(filename_output)
        self.assertEqual(None, error)
        lenin = capin.get(video_tools.cv2api_delegate.prop_frame_count)
        lenout = capout.get(video_tools.cv2api_delegate.prop_frame_count)
        self.assertGreater(lenin,lenout)

    def tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)