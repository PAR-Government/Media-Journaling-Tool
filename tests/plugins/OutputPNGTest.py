import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile


class OutputPNGTestCase(unittest.TestCase):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_something(self):
        img = numpy.random.randint(0, 255, (500, 500, 3), dtype='uint8')
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(numpy.zeros((500,500,3), dtype=numpy.uint8))
        filename = tempfile.mktemp(prefix='cstc', suffix='.png', dir='.')
        filename_output = tempfile.mktemp(prefix='cstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename, filename_output])
        img_wrapper.save(filename)
        target_wrapper.save(filename_output)
        op = plugins.getOperation('OutputPNG::Foo')
        self.assertEqual('OutputPng::Foo',op['name'])
        args, error = plugins.callPlugin('OutputPNG::Foo',
                                         img_wrapper,
                                         filename,
                                         filename_output)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(numpy.all(img == output))



    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
