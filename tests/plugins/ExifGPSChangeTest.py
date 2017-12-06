import unittest
import os
from maskgen import plugins, image_wrap,exif
import numpy
import tempfile
from tests.test_support import TestSupport



class ExifGPSChangeTestCase(TestSupport):

    def setUp(self):
        plugins.loadPlugins()

    filesToKill = []
    def test_gray(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project5.jpg'))
        img = img_wrapper.to_array()
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(img)
        filename  = self.locateFile('tests/images/test_project5.jpg')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.jpg', dir='.')
        self.filesToKill.extend([filename_output])
        target_wrapper.save(filename_output,format='JPEG')

        args,error = plugins.callPlugin('ExifGPSChange',
                            img_wrapper,
                           filename,
                           filename_output)
        self.assertEqual(error,None)
        data = exif.getexif(filename)
        data_output = exif.getexif(filename_output)
        self.assertTrue(data['GPS Latitude'] != data_output['GPS Latitude'])
        self.assertTrue(data['GPS Longitude'] != data_output['GPS Longitude'])


    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
