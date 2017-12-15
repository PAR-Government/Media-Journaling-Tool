import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile
from tests import test_support


class MedianBlurTestCase(test_support.TestSupport):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_something(self):
        filename = self.locateFile('tests/images/test_project1.jpg')
        wrapper = image_wrap.openImageFile(filename)
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        #self.filesToKill.append(filename_output)
        img = numpy.asarray(wrapper)
        image_wrap.ImageWrapper(img).save(filename_output)
        args, error = plugins.callPlugin('WienerFilter',
                                         wrapper,
                                         filename,
                                         filename_output,
                                         percentageChange=0.5)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertEqual(output.shape, img.shape)
        diff = abs(output - img)
        #finaldiff = numpy.zeros((500, 500))
        #for i in range(3):
        #    finaldiff = finaldiff + diff[:, :, i]
        #finaldiff[finaldiff > 0] = 1
        # self.assertTrue(abs(sum(sum(finaldiff))-62500) < 100)

    def tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)


if __name__ == '__main__':
    unittest.main()
