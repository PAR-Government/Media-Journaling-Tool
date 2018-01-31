import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile
from tests.test_support import TestSupport
import numpy as np
import cv2

def widthandheight(img):
    a = numpy.where(img != 0)
    bbox = numpy.min(a[0]), numpy.max(a[0]), numpy.min(a[1]), numpy.max(a[1])
    h,w = bbox[1] - bbox[0], bbox[3] - bbox[2]
    return bbox[2],bbox[0],w,h

class SeamCarvingTestCase(TestSupport):

    def setUp(self):
        plugins.loadPlugins()

    def test_seam_carve(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project5.jpg'))
        img = img_wrapper.to_array()
        mask = np.zeros(img.shape).astype('uint8')
        cv2.circle(mask, (img.shape[0]/8,img.shape[1]/8), img.shape[0]/16, (255, 0, 0), -1)
        cv2.circle(mask, (img.shape[0] *5/ 8, img.shape[1] *5/ 8), img.shape[0] / 16, (0, 255, 0), -1)
        mask_wrapper = image_wrap.ImageWrapper(mask)
        mask_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.addFileToRemove(mask_output)
        mask_wrapper.save(mask_output)
        target_wrapper = image_wrap.ImageWrapper(img)
        filename  = self.locateFile('tests/images/test_project5.jpg')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.jpg', dir='.')
        self.addFileToRemove(filename_output)
        target_wrapper.save(filename_output)
        args,error = plugins.callPlugin('SeamCarve',
                            img_wrapper,
                            filename,
                            filename_output,
                            inputmaskname=os.path.abspath(mask_output),
                            percentage_height=0.95,
                            percentage_width=0.95)
        output_files = args['output_files']
        self.assertTrue('column adjuster' in output_files and os.path.exists(output_files['column adjuster']))
        self.assertTrue('row adjuster' in output_files and os.path.exists(output_files['row adjuster']))
        self.assertTrue('plugin mask' in output_files and os.path.exists(output_files['plugin mask']))
        self.assertTrue('neighbor mask' in output_files and os.path.exists(output_files['neighbor mask']))
        for v in output_files.values():
            os.remove(v)



if __name__ == '__main__':
    unittest.main()
