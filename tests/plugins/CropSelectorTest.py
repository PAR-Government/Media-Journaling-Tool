import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile


class CropSelectorTestCase(unittest.TestCase):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_boundary(self):
        img = numpy.zeros((500, 540), dtype='uint8')
        wrapper = image_wrap.ImageWrapper(img)
        filename = tempfile.mktemp(prefix='mstc', suffix='.png', dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.append(filename)
        wrapper.save(filename)
        self.filesToKill.append(filename_output)
        image_wrap.ImageWrapper(img).save(filename_output)
        args, error = plugins.callPlugin('CropSelector',
                                         wrapper,
                                         filename,
                                         filename_output,
                                         percentage_width=0.001,
                                         percentage_height=0.0001,
                                         eightbit_boundary='yes')
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()

        img = numpy.zeros((500, 540), dtype='uint8')
        wrapper = image_wrap.ImageWrapper(img)
        filename = tempfile.mktemp(prefix='mstc', suffix='.png', dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.append(filename)
        wrapper.save(filename)
        self.filesToKill.append(filename_output)
        image_wrap.ImageWrapper(img).save(filename_output)
        args, error = plugins.callPlugin('CropSelector',
                                         wrapper,
                                         filename,
                                         filename_output,
                                         percentage_width=1,
                                         percentage_height=0.0001,
                                         eightbit_boundary='yes')
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()

    def test_nonsnap(self):
        img = numpy.zeros((500,540),dtype='uint8')
        wrapper = image_wrap.ImageWrapper(img)
        filename  = tempfile.mktemp(prefix='mstc',suffix='.png',dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.append(filename)
        wrapper.save(filename)
        self.filesToKill.append(filename_output)
        image_wrap.ImageWrapper(img).save(filename_output)
        args,error = plugins.callPlugin('CropSelector',
                            wrapper,
                           filename,
                           filename_output,
                           percentage_width = 0.1,
                           percentage_height=0.1)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()

        self.assertEqual(output.shape, img.shape)
        self.assertTrue('crop_x' in args and args['crop_x'] <= 50)
        self.assertTrue('crop_y' in args and args['crop_y'] <= 50)
        self.assertTrue('crop_width' in args and args['crop_width'] == 54)
        self.assertTrue('crop_height' in args and args['crop_height']==50)
        self.assertTrue(output[args['crop_y']+1,args['crop_x']+1] == 255)
        self.assertTrue(output[args['crop_y']-1, args['crop_x']-1] == 0)
        self.assertTrue(output[-(args['crop_height']-args['crop_y']+1), -(args['crop_width']-args['crop_x']+1)] == 255)
        self.assertTrue(output[-(args['crop_height']-args['crop_y']-1), -(args['crop_width']-args['crop_x']-1)] == 0)

    def test_snap(self):
        img = numpy.zeros((500,500),dtype='uint8')
        wrapper = image_wrap.ImageWrapper(img)
        filename  = tempfile.mktemp(prefix='mstc',suffix='.png',dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.append(filename)
        wrapper.save(filename)
        self.filesToKill.append(filename_output)
        image_wrap.ImageWrapper(img).save(filename_output)
        args,error = plugins.callPlugin('CropSelector',
                            wrapper,
                           filename,
                           filename_output,
                           percentage_width = 0.1,
                           percentage_height=0.1,
                            eightbit_boundary='yes')
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()

        self.assertEqual(output.shape, img.shape)
        self.assertTrue('crop_x' in args and args['crop_x'] <= 56)
        self.assertTrue('crop_y' in args and args['crop_y'] <= 56)
        self.assertTrue('crop_width' in args and args['crop_width'] == 56)
        self.assertTrue('crop_height' in args and args['crop_height']==56)
        self.assertTrue(args['crop_y']%8==0)
        self.assertTrue(args['crop_x'] % 8 == 0)
        self.assertTrue(output[-(args['crop_height']-args['crop_y']+1), -(args['crop_width']-args['crop_x']+1)] == 255)
        self.assertTrue(output[-(args['crop_height']-args['crop_y']-1), -(args['crop_width']-args['crop_x']-1)] == 0)


    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
