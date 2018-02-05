import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile

class MaskSelectorTestCase(unittest.TestCase):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_something(self):
        img = numpy.zeros((500,500),dtype='uint8')
        wrapper = image_wrap.ImageWrapper(img)
        filename  = tempfile.mktemp(prefix='mstc',suffix='.png',dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.append(filename)
        wrapper.save(filename)
        self.filesToKill.append(filename_output)
        wrapper.save(filename_output)
        args,error = plugins.callPlugin('MaskSelector',
                            wrapper,
                           filename,
                           filename_output,
                           percentage_width = 0.1,
                            percentage_height=0.1)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(sum(sum(output))>255)
        self.assertTrue(sum(sum(output)) < numpy.prod(output.shape))
        self.assertEqual(output.shape, img.shape)
        self.assertTrue('paste_x' in args and args['paste_x'] > 0)
        self.assertTrue('paste_y' in args and args['paste_y'] > 0)


    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
