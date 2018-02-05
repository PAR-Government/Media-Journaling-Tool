import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile


class MaskSelectorTestCase(unittest.TestCase):

    def setUp(self):
        plugins.loadPlugins()

    filesToKill = []
    def test_something(self):
        img = numpy.random.randint(0,255,(500,500,3),dtype='uint8')
        mask = numpy.zeros((500,500),dtype='uint8')
        mask[30:50,30:50] = 255
        self.assertTrue(sum(sum(sum(img[30:50,30:50]-img[400:420,300:320])))>0)
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(mask)
        mask_wrapper = image_wrap.ImageWrapper(mask)
        filename  = tempfile.mktemp(prefix='mstc',suffix='.png',dir='.')
        filename_mask= tempfile.mktemp(prefix='mstcm', suffix='.png', dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename,filename_mask,filename_output])
        img_wrapper.save(filename)
        mask_wrapper.save(filename_mask)
        target_wrapper.save(filename_output)

        args,error = plugins.callPlugin('DesignPasteClone',
                            img_wrapper,
                           filename,
                           filename_output,
                            inputmaskname=filename_mask,
                           paste_x = 300,
                           paste_y = 400)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(sum(sum(sum(img[30:50, 30:50] - output[400:420, 300:320])))== 0)


    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
