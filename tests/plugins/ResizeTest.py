import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile


class ResizeTestCase(unittest.TestCase):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_something(self):
        img = numpy.random.randint(0, 255, (500, 400, 3), dtype='uint8')
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(img)
        filename = tempfile.mktemp(prefix='cstc', suffix='.png', dir='.')
        filename_output = tempfile.mktemp(prefix='cstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename, filename_output])
        img_wrapper.save(filename)
        target_wrapper.save(filename_output)

        args, error = plugins.callPlugin('CV2Resize',
                                         img_wrapper,
                                         filename,
                                         filename_output,
                                         width=550,
                                         height=450,
                                         interpolation='cubic')
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(output.shape == (450,550,3))



    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
