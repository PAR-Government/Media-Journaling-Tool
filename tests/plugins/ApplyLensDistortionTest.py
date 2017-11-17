import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile


class CropSelectorTestCase(unittest.TestCase):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_all(self):
        filename = "tests/videos/sample1.mov"
        filename_output = "tests/videos/sample1_ds.mov"
        self.filesToKill.append(filename_output)
        args,error = plugins.callPlugin('ApplyLensDistortion',
                        None,
                           filename,
                           filename_output,
                            threshold = 0.8)
        self.assertEqual(None,error)


    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
