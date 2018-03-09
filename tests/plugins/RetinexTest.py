import unittest
from maskgen import plugins, image_wrap
import numpy
import tempfile
from tests import test_support


class RetinexTestCase(test_support.TestSupport):

    def setUp(self):
        plugins.loadPlugins()

    def test_retinex(self):
        inputfile = self.locateFile('tests/images/test_project5.jpg')
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project5.jpg'))
        img = img_wrapper.to_array()
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.jpg', dir='.')
        self.addFileToRemove(filename_output)
        args, error = plugins.callPlugin('Retinex',
                                         img_wrapper,
                                         inputfile,
                                         filename_output)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(output.shape == (322,483,3))
        self.assertTrue(numpy.all(output != input))

if __name__ == '__main__':
    unittest.main()
