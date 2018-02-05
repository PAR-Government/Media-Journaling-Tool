import unittest
import os
from maskgen import plugins, image_wrap
import numpy
import tempfile


class CropSelectorTestCase(unittest.TestCase):
    filesToKill = []

    def setUp(self):
        plugins.loadPlugins()

    def test_all(self):
        img = numpy.zeros((500,500),dtype='uint8')
        wrapper = image_wrap.ImageWrapper(img)
        filename  = tempfile.mktemp(prefix='mstc',suffix='.png',dir='.')
        filename_output = tempfile.mktemp(prefix='mstcr', suffix='.png', dir='.')
        self.filesToKill.append(filename)
        wrapper.save(filename)
        self.filesToKill.append(filename_output)
        image_wrap.ImageWrapper(img).save(filename_output)
        self.no_snap_no_division(wrapper, filename, filename_output)
        self.no_snap_division(wrapper, filename, filename_output)
        self.snap_no_division(wrapper, filename, filename_output)
        self.snap_division(wrapper, filename, filename_output)


    def no_snap_no_division(self, wrapper, filename, filename_output):
        args,error = plugins.callPlugin('CropPermutations',
                            wrapper,
                           filename,
                           filename_output,
                           percentage_width = 0.1,
                           percentage_height=0.1)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()

        self.assertEqual(output.shape, wrapper.image_array.shape)
        self.assertTrue('crop_x' in args and args['crop_x'] ['values'] == [8,16,24,32,40,48])
        self.assertTrue('crop_y' in args and args['crop_y']['values'] == [8, 16, 24, 32, 40, 48])
        self.assertTrue('crop_width' in args and args['crop_width'] == 50)
        self.assertTrue('crop_height' in args and args['crop_height']==50)

    def no_snap_division(self, wrapper, filename, filename_output):
        args,error = plugins.callPlugin('CropPermutations',
                            wrapper,
                           filename,
                           filename_output,
                           percentage_width = 0.1,
                           percentage_height=0.1,
                           divisions_width=3,
                          divisions_height=2)
        wrapper = image_wrap.openImageFile(filename_output)
        output = wrapper.to_array()

        self.assertEqual(output.shape, wrapper.image_array.shape)
        self.assertTrue('crop_x' in args and args['crop_x'] ['values'] == [16,32,48])
        self.assertTrue('crop_y' in args and args['crop_y']['values'] == [25])
        self.assertTrue('crop_width' in args and args['crop_width'] == 50)
        self.assertTrue('crop_height' in args and args['crop_height']==50)

    def snap_no_division(self, wrapper, filename, filename_output):
        args,error = plugins.callPlugin('CropPermutations',
                            wrapper,
                           filename,
                           filename_output,
                           percentage_width = 0.1,
                           percentage_height=0.1,
                            eightbit_boundary='yes')
        self.assertTrue('crop_x' in args and args['crop_x']['values'] == [8, 16, 24, 32, 40])
        self.assertTrue('crop_y' in args and args['crop_y']['values'] == [8, 16, 24, 32, 40])
        self.assertTrue('crop_width' in args and args['crop_width'] == 48)
        self.assertTrue('crop_height' in args and args['crop_height']==48)

    def snap_division(self, wrapper, filename, filename_output):
        args,error = plugins.callPlugin('CropPermutations',
                            wrapper,
                           filename,
                           filename_output,
                           percentage_width = 0.1,
                           percentage_height=0.1,
                            eightbit_boundary='yes',
                         divisions_width = 3,
                                       divisions_height = 2)
        self.assertTrue('crop_x' in args and args['crop_x']['values'] == [16,32])
        self.assertTrue('crop_y' in args and args['crop_y']['values'] == [24])
        self.assertTrue('crop_width' in args and args['crop_width'] == 48)
        self.assertTrue('crop_height' in args and args['crop_height']==48)

    def  tearDown(self):
        for f in self.filesToKill:
            if os.path.exists(f):
                os.remove(f)

if __name__ == '__main__':
    unittest.main()
