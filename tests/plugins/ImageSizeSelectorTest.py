import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile
from tests.test_support import TestSupport


class ImageSizeSelectorTestCase(TestSupport):
    def setUp(self):
        plugins.loadPlugins()

    filesToKill = []

    def test_something(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test.tif'))
        img = img_wrapper.to_array()
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(img)
        filename = self.locateFile('tests/images/test.tif')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename_output])
        target_wrapper.save(filename_output)

        args, error = plugins.callPlugin('ImageSizeSelector',
                                         img_wrapper,
                                         filename,
                                         filename_output,
                                         cameraDataFile=self.locateFile('data/camera_sizes.json'),
                                         pickOne='yes',
                                         )

        self.assertTrue('height' in args and args['height'] == 3264)
        self.assertTrue('width' in args and args['width'] == 4928)

    def tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)


if __name__ == '__main__':
    unittest.main()
