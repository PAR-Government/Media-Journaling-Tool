import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile


class CV2ResizeByPercentTestCase(unittest.TestCase):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_snap(self):
        img = numpy.zeros((500,540),dtype='uint8')
        wrapper = image_wrap.ImageWrapper(img)
        filename  = tempfile.mktemp(prefix='mstc',suffix='.png',dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.append(filename)
        wrapper.save(filename)
        self.filesToKill.append(filename_output)
        image_wrap.ImageWrapper(img).save(filename_output)
        args,error = plugins.callPlugin('CV2ResizeByPercent',
                            wrapper,
                           filename,
                           filename_output,
                           percentage_width = 0.9,
                           percentage_height=0.9,
                            interpolation='other' )
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()

        self.assertEqual((448,480),output.shape)


    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
