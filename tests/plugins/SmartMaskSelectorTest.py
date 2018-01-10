import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile
from tests import test_support


def widthandheight(img):
    a = numpy.where(img != 0)
    bbox = numpy.min(a[0]), numpy.max(a[0]), numpy.min(a[1]), numpy.max(a[1])
    h,w = bbox[1] - bbox[0], bbox[3] - bbox[2]
    return bbox[2],bbox[0],w,h

class SmartMaskSelectorTestCase(test_support.TestSupport):

    def setUp(self):
        plugins.loadPlugins()

    filesToKill = []
    def test_typical(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test.png'))
        img = img_wrapper.to_array()
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(img)
        filename  = self.locateFile('tests/images/test.png')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename_output])
        target_wrapper.save(filename_output)

        args,error = plugins.callPlugin('SmartMaskSelector',
                            img_wrapper,
                           filename,
                           filename_output,
                                        smallw=100,
                                        smallh=100,
                                        mediumw=150,
                                        mediumh=150,
                                        largew=200,
                                        largeh=200,
                                        size=2,
                                        op=2
                                        )
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue (img_wrapper.size[1] == wrapper.size[1])
        self.assertTrue(img_wrapper.size[0] == wrapper.size[0])
        self.assertTrue(len(output.shape) == 2)
        totalsize = sum(sum(output / 255))
        print totalsize
        self.assertTrue(totalsize <= (2 * 22500))
        self.assertTrue(totalsize >= 22500)
        self.assertTrue('paste_x' in args and args['paste_x'] > 0)
        self.assertTrue('paste_y' in args and args['paste_y'] > 0)

    def test_rgb(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test.png'))
        img = img_wrapper.to_array()
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(img)
        filename  = self.locateFile('tests/images/test.png')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename_output])
        target_wrapper.save(filename_output)

        args,error = plugins.callPlugin('SmartMaskSelector',
                            img_wrapper,
                           filename,
                           filename_output,
                                        smallw=100,
                                        smallh=100,
                                        mediumw=150,
                                        mediumh=150,
                                        largew=200,
                                        largeh=200,
                                        size=2,
                                        op=2,
                                        savecolor='0,255,0',
                                        region=0.8
                                        )
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue (img_wrapper.size[1] == wrapper.size[1])
        self.assertTrue(img_wrapper.size[0] == wrapper.size[0])
        self.assertTrue(len(output.shape) == 3)
        totalsize = sum(sum(output[:,:,1] / 255))
        print totalsize
        self.assertTrue(totalsize <= (2 * 22500))
        #self.assertTrue(totalsize >= 22500)
        self.assertTrue('paste_x' in args and args['paste_x'] > 0)
        self.assertTrue('paste_y' in args and args['paste_y'] > 0)



    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
