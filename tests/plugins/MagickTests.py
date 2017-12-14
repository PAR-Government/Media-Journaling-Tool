import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile
from tests import test_support


class MagickTestCase(test_support.TestSupport):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_gamma(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project1.jpg'))
        filename_output = tempfile.mktemp(prefix='cstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename_output])
        img_wrapper.save(filename_output)

        args, error = plugins.callPlugin('ManualGammaCorrection',
                                         img_wrapper,
                                         self.locateFile('tests/images/test_project1.jpg'),
                                         filename_output,
                                         gamma=2.0)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(output.shape == img_wrapper.to_array().shape)
        # self.assertFalse(numpy.all(output==img_wrapper.to_array(),axis=0))

    def test_modulate(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project1.jpg'))
        filename_output = tempfile.mktemp(prefix='cstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename_output])
        img_wrapper.save(filename_output)

        args, error = plugins.callPlugin('MagickModulate',
                                         img_wrapper,
                                         self.locateFile('tests/images/test_project1.jpg'),
                                         filename_output,
                                         saturation=130,
                                         brightness=130)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(output.shape == img_wrapper.to_array().shape)
        # self.assertFalse(numpy.all(output == img_wrapper.to_array(), axis=0))

    def test_noise(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project1.jpg'))
        filename_output = tempfile.mktemp(prefix='cstcr', suffix='.png', dir='.')
        self.filesToKill.extend([filename_output])
        img_wrapper.save(filename_output)

        args, error = plugins.callPlugin('MagickAddNoise',
                                         img_wrapper,
                                         self.locateFile('tests/images/test_project1.jpg'),
                                         filename_output,
                                         **{"Noise Type":"salt-pepper"})
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(output.shape == img_wrapper.to_array().shape)
        # self.assertFalse(numpy.all(output == img_wrapper.to_array(), axis=0))

    def test_contrast(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project1.jpg'))
        filename_output = tempfile.mktemp(prefix='cstcr', suffix='_c.png', dir='.')
        self.filesToKill.extend([filename_output])
        img_wrapper.save(filename_output)

        args, error = plugins.callPlugin('Constrast',
                                         img_wrapper,
                                         self.locateFile('tests/images/test_project1.jpg'),
                                         filename_output,
                                         direction="increase")
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(output.shape == img_wrapper.to_array().shape)
        # self.assertFalse(numpy.all(output == img_wrapper.to_array(), axis=0))

    def test_levels(self):
        img_wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test_project1.jpg'))
        filename_output = tempfile.mktemp(prefix='cstcr', suffix='_l.png', dir='.')
        #self.filesToKill.extend([filename_output])
        img_wrapper.save(filename_output)

        args, error = plugins.callPlugin('LevelCorrectionNoMask',
                                         img_wrapper,
                                         self.locateFile('tests/images/test_project1.jpg'),
                                         filename_output,
                                         blackpoint=25,
                                         whitepoint=75,
                                         gamma=1.5)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()
        self.assertTrue(output.shape == img_wrapper.to_array().shape)

    def tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)


if __name__ == '__main__':
    unittest.main()
