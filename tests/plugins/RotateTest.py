import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile
from tests import test_support

class ResizeTestCase(test_support.TestSupport):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_something(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project1.jpg'))
        filename_output = tempfile.mktemp(prefix='cstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename_output])
        img_wrapper.save(filename_output)

        args, error = plugins.callPlugin('CV2Rotation',
                                         img_wrapper,
                                         self.locateFile('tests/images/test_project1.jpg'),
                                         filename_output,
                                         rotation=5)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(output.shape == img_wrapper.to_array().shape)



    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
