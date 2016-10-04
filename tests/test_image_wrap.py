from maskgen import image_wrap
import unittest
import numpy as np
from PIL import Image
import maskgen.tool_set
import os



class TestImageWrap(unittest.TestCase):


    def test_open(self):
        wrapper = image_wrap.openImageFile('images/sample.jpg')
        self.assertTrue(wrapper.to_image() is not None)
        im = Image.open('images/sample.jpg')
        im_array = np.asarray(im)
        self.assertTrue(wrapper.image_array.shape == im_array.shape)

        wrapper = image_wrap.openImageFile('tests/test.png')
        self.assertTrue(wrapper.to_image() is not None)
        im = Image.open('tests/test.png')
        im_array = np.asarray(im)
        self.assertTrue(wrapper.image_array.shape == im_array.shape)
        self.assertEquals(wrapper.size, im.size)

        pilim = maskgen.tool_set.fixTransparency(maskgen.tool_set.imageResizeRelative(wrapper,(250,250),wrapper.size)).toPIL()
        pilFixTransparency  = self.pilFixTransparency(maskgen.tool_set.imageResizeRelative(im,(250,250),im.size))
        self.assertTrue(pilim.size == pilFixTransparency.size)
        r,g,b = pilim.split()
        rt, gt, bt = pilFixTransparency.split()
        r,g,b = np.asarray(r),np.asarray(g),np.asarray(b)
        rt, gt, bt = np.asarray(rt), np.asarray(gt), np.asarray(bt)
        v = sum(sum(r - rt))
        self.assertEquals(v,0)

        self.assertTrue((wrapper.image_array ==np.asarray(wrapper)).all())
        self.assertTrue((wrapper.image_array == np.array(wrapper)).all())

        wrapper = image_wrap.openImageFile('tests/test.tif')
        wrapper.save('tests/test1.tif',**wrapper.info)



    def check_save(self, wrapper,foarmat):
        fname = 'tests/foo.' + ('tif' if foarmat != 'PNG' else 'png')
        wrapper.save(fname, format=foarmat)
        compareWrapper  = image_wrap.openImageFile(fname)
        self.assertTrue((compareWrapper.image_array == wrapper.image_array).all())
        os.remove(fname)

    def test_resize_images(self):
        wrapper = image_wrap.ImageWrapper(np.random.randint(0,64444,(256,300),dtype='uint16'))
        self.assertTrue( wrapper.resize((250,250),Image.ANTIALIAS).size[1] == 250)
        self.check_save(wrapper,'TIFF')

        wrapper = image_wrap.ImageWrapper(np.random.randint(0, 64444, (256, 300,3), dtype='uint16'))
        self.assertTrue(wrapper.resize((250, 250), Image.ANTIALIAS).size[1] == 250)
        self.check_save(wrapper,'TIFF')

        wrapper = image_wrap.ImageWrapper(np.random.randint(0, 255, (256, 300), dtype='uint8'))
        self.assertTrue(wrapper.resize((250, 250), Image.ANTIALIAS).size[1] == 250)
        self.check_save(wrapper,'PNG')


    def test_L_images(self):
        wrapper = image_wrap.ImageWrapper( np.random.randint(0,64444,(32,32),dtype='uint16'))
        self.assertTrue( wrapper.to_image() is not None)
        self.assertEqual(wrapper.mode,'L')

        wrapper = image_wrap.ImageWrapper(np.random.randint(0, 64444, (32, 32,3), dtype='uint16'), to_mask=True)
        self.assertTrue(wrapper.to_image() is not None)
        self.assertEqual(wrapper.mode, 'L')

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32), to_mask=True)
        self.assertTrue(wrapper.to_image() is not None)
        self.assertEqual(wrapper.mode, 'L')

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32,3), to_mask=True)
        self.assertTrue(wrapper.to_image() is not None)
        self.assertEqual(wrapper.mode, 'L')


    def test_convert_images(self):
        wrapper = image_wrap.ImageWrapper(np.random.randint(0, 64444, (32, 32), dtype='uint16'))
        self.assertEqual(wrapper.convert("RGBA").image_array.shape,(32,32,4))

        wrapper = image_wrap.ImageWrapper(np.random.randint(0, 64444, (32, 32, 3), dtype='uint16'), to_mask=False)
        self.assertEqual(wrapper.convert("RGBA").image_array.shape,(32,32,4))

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32), to_mask=False)
        self.assertEqual(wrapper.convert("RGBA").image_array.shape,(32,32,4))

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32, 3), to_mask=False)
        self.assertEqual(wrapper.convert("RGBA").image_array.shape,(32,32,4))


    def test_resize_images(self):
        wrapper = image_wrap.ImageWrapper(np.random.randint(0, 64444, (32, 32), dtype='uint16'))
        self.assertEqual(wrapper.resize((40,40),Image.ANTIALIAS).size,(40,40))

        wrapper = image_wrap.ImageWrapper(np.random.randint(0, 64444, (32, 32, 3), dtype='uint16'), to_mask=False)
        self.assertEqual(wrapper.resize((40, 40), Image.ANTIALIAS).size, (40, 40))

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32), to_mask=False)
        self.assertEqual(wrapper.resize((40, 40), Image.ANTIALIAS).size, (40, 40))

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32, 3), to_mask=False)
        self.assertEqual(wrapper.resize((40, 40), Image.ANTIALIAS).size, (40, 40))


    def test_mask_images(self):
        wrapper = image_wrap.ImageWrapper(np.random.randint(0, 64444, (32, 32), dtype='uint16'))
        self.assertEqual(wrapper.to_mask().mode,'L')

        wrapper = image_wrap.ImageWrapper(np.random.randint(0, 64444, (32, 32, 3), dtype='uint16'), to_mask=False)
        self.assertEqual(wrapper.to_mask().mode, 'L')

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32), to_mask=False)
        self.assertEqual(wrapper.to_mask().mode, 'L')

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32, 3), to_mask=False)
        self.assertEqual(wrapper.to_mask().mode, 'L')

    def test_float_images(self):
        wrapper = image_wrap.ImageWrapper(np.random.rand( 32, 32))
        self.assertTrue(wrapper.to_float().to_array() is not None)

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32, 3), to_mask=True)
        self.assertTrue(wrapper.to_float().to_array() is not None)

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32), to_mask=True)
        self.assertTrue(wrapper.to_float().to_array() is not None)

        wrapper = image_wrap.ImageWrapper(np.random.rand(32, 32, 3), to_mask=True)
        self.assertTrue(wrapper.to_float().to_array() is not None)


    def pilFixTransparency(self,img):
        if img.mode.find('A') < 0:
            return img
        xx = np.asarray(img)
        perc = xx[:, :, 3].astype(float) / float(255)
        xx.flags['WRITEABLE'] = True
        for d in range(3):
            xx[:, :, d] = xx[:, :, d] * perc
        xx[:, :, 3] = np.ones((xx.shape[0], xx.shape[1])) * 255
        return Image.fromarray(xx)

if __name__ == '__main__':
    unittest.main()
