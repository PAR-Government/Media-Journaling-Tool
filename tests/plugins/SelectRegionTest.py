import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile

from tests.test_support import TestSupport

def widthandheight(img):
    a = numpy.where(img != 0)
    bbox = numpy.min(a[0]), numpy.max(a[0]), numpy.min(a[1]), numpy.max(a[1])
    h,w = bbox[1] - bbox[0], bbox[3] - bbox[2]
    return bbox[2],bbox[0],w,h

class SegmentedMaskSelectorTestCase(TestSupport):

    def setUp(self):
        plugins.loadPlugins()

    filesToKill = []
    def test_gray(self):
        filename = self.locateFile('tests/images/test_project5.jpg')
        img_wrapper = image_wrap.openImageFile(filename)
        img = img_wrapper.to_array()
        target_wrapper = image_wrap.ImageWrapper(img)
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename_output])
        target_wrapper.save(filename_output)

        args,error = plugins.callPlugin('SelectRegion',
                            img_wrapper,
                           filename,
                           filename_output)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()[:,:,3]
        self.assertTrue(sum(sum(output)) > 255)
        x,y,w,h = widthandheight (output)
        if x>1:
            self.assertTrue(sum(sum(output[:,0:x-1])) == 0)
        if y>1:
            self.assertTrue(sum(sum(output[0:y-1,])) == 0)
        self.assertTrue(sum(sum(output[y+h+1:,x+w+1:])) == 0)
        self.assertEqual(output.shape[0], img.shape[0])
        self.assertEqual(output.shape[1], img.shape[1])
        self.assertTrue('paste_x' in args and args['paste_x'] >= 0)
        self.assertTrue('paste_y' in args and args['paste_y'] >= 0)

    def test_rgb(self):
        filename = self.locateFile('tests/images/test_project5.jpg')
        img_wrapper = image_wrap.openImageFile(filename)
        img = img_wrapper.to_array()
        target_wrapper = image_wrap.ImageWrapper(img)
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename_output])
        target_wrapper.save(filename_output)

        args, error = plugins.callPlugin('SelectRegion',
                                         img_wrapper,
                                         filename,
                                         filename_output,
                                         alpha='yes')
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(sum(sum(output[:, :, 3])) > 255)
        x, y, w, h = widthandheight(output[:, :, 3])
        if x > 1:
            self.assertTrue(sum(sum(output[:, 0:x - 1, 3])) == 0)
        if y > 1:
            self.assertTrue(sum(sum(output[0:y - 1, :, 3])) == 0)
        self.assertTrue(sum(sum(output[y + h + 1:, x + w + 1:, 3])) == 0)
        self.assertEqual(output.shape[0], img.shape[0])
        self.assertEqual(output.shape[1], img.shape[1])
        self.assertTrue('paste_x' in args and args['paste_x'] > 0)
        self.assertTrue('paste_y' in args and args['paste_y'] > 0)

    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
