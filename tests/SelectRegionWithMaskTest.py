import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile


class SelectRegionWithTestCase(unittest.TestCase):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_gray(self):
        img = numpy.random.randint(0, 255, (500, 500), dtype='uint8')
        mask = numpy.zeros((500,500),dtype='uint8')
        mask[30:50,30:50] = 255
        wrapper = image_wrap.ImageWrapper(img)
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(mask)
        mask_wrapper = image_wrap.ImageWrapper(mask)
        filename = tempfile.mktemp(prefix='mstc', suffix='.png', dir='.')
        filename_mask = tempfile.mktemp(prefix='mstcm', suffix='.png', dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename, filename_mask, filename_output])
        img_wrapper.save(filename)
        mask_wrapper.save(filename_mask)
        target_wrapper.save(filename_output)
        args,error = plugins.callPlugin('SelectRegionWithMask',
                           wrapper,
                           filename,
                           filename_output,
                           inputmaskname = filename_mask)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()

        self.assertEqual((500,500,2), output.shape)
        self.assertTrue(numpy.all(output[:,:,1] == mask))
        self.assertTrue(numpy.all(output[:, :, 0] == img))

    def test_color(self):
        img = numpy.random.randint(0, 255, (500, 500,3), dtype='uint8')
        mask = numpy.zeros((500, 500), dtype='uint8')
        mask[30:50, 30:50] = 255
        wrapper = image_wrap.ImageWrapper(img)
        img_wrapper = image_wrap.ImageWrapper(img)
        target_wrapper = image_wrap.ImageWrapper(mask)
        mask_wrapper = image_wrap.ImageWrapper(mask)
        filename = tempfile.mktemp(prefix='mstc', suffix='.png', dir='.')
        filename_mask = tempfile.mktemp(prefix='mstcm', suffix='.png', dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename, filename_mask, filename_output])
        img_wrapper.save(filename)
        mask_wrapper.save(filename_mask)
        target_wrapper.save(filename_output)
        args, error = plugins.callPlugin('SelectRegionWithMask',
                                         wrapper,
                                         filename,
                                         filename_output,
                                         inputmaskname=filename_mask)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()

        self.assertEqual((500, 500, 4), output.shape)
        self.assertTrue(numpy.all(output[:, :, 3] == mask))
        self.assertTrue(numpy.all(output[:, :, 0] == img[:,:,0]))


    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
