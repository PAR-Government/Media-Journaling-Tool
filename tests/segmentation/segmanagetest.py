import unittest
from maskgen import  image_wrap
import numpy
from maskgen.segmentation.segmanage import select_region,segmentation_classification,convert_color
from tests.test_support import TestSupport

class SegManageTestCase(TestSupport):


    def test_select_region(self):
        img = numpy.zeros((500,500,3),dtype='uint8')
        img_wrapper = image_wrap.ImageWrapper(img)
        selector = numpy.zeros((500, 500, 3), dtype='uint8')
        selector[30:40,30:40,:] = [200,200,100]
        selector[130:140, 130:140, :] = [100, 200, 100]
        selector_wrapper = image_wrap.ImageWrapper(selector)
        result,rcolor = select_region(img_wrapper,selector_wrapper,convert_color('[200,200,100]'))
        result = result.to_array()
        self.assertTrue(numpy.all(result[30:40,30:40,3] == 255))
        self.assertTrue(numpy.all(result[130:140, 130:140, 3] == 0))
        self.assertEquals(rcolor,[200,200,100])

    def test_select_region_anycolor(self):
        img = numpy.zeros((500, 500, 3), dtype='uint8')
        img_wrapper = image_wrap.ImageWrapper(img)
        selector = numpy.zeros((500, 500, 3), dtype='uint8')
        selector[30:40, 30:40, :] = [200, 200, 100]
        selector[130:140, 130:140, :] = [100, 200, 100]
        selector_wrapper = image_wrap.ImageWrapper(selector)
        result,color = select_region(img_wrapper, selector_wrapper)
        result = result.to_array()
        self.assertTrue(numpy.all(result[30:40, 30:40, 3] != result[130:140, 130:140, 3]))

    def test_segmentation_classification(self):
        import os
        filelocation = self.locateFile('./tests/data/classifications.csv')
        self.assertEquals(segmentation_classification(os.path.dirname(filelocation),[100,100,200]),'other')
        self.assertEquals(segmentation_classification(os.path.dirname(filelocation), [200,100,200]), 'house')


if __name__ == '__main__':
    unittest.main()
