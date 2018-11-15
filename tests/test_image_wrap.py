from maskgen import image_wrap
import unittest
import numpy as np
from PIL import Image
import maskgen.tool_set
import os
from test_support import TestSupport


class TestImageWrap(TestSupport):

    def test_pdf(self):
        self.assertTrue(image_wrap.pdf2_image_extractor(self.locateFile('tests/images/c0abb79c6607109f5e85494bda92b986-recapture.pdf')) is not None)

    def test_open(self):
        wrapper = image_wrap.openImageFile(self.locateFile('images/sample.jpg'))
        self.assertTrue(wrapper.to_image() is not None)
        im = Image.open(self.locateFile('images/sample.jpg'))
        im_array = np.asarray(im)
        self.assertTrue(wrapper.image_array.shape == im_array.shape)

        wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test.png'))
        self.assertTrue(wrapper.to_image() is not None)
        im = Image.open(self.locateFile('images/test.png'))
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

        wrapper = image_wrap.openImageFile(self.locateFile('tests/images/test.tif'))
        self.addFileToRemove('test1.tif')
        wrapper.save('test1.tif',**wrapper.info)
        wrapper.to_float()
        wrapper.to_rgb()

    def test_two_channel(self):
        wrapper = image_wrap.openImageFile(self.locateFile('tests/images/two_channel.jpg'))
        wrapper.to_mask()
        wrapper.apply_transparency()
        wrapper.convert('L')
        wrapper.convert('RGBA')
        wrapper.to_float()
        wrapper.to_rgb()


    def check_save(self, wrapper,foarmat):
        dir = os.path.dirname( self.locateFile('tests/images/postfill.png'))
        fname = os.path.join(dir,'foo.' + ('tif' if foarmat != 'PNG' else 'png'))
        self.addFileToRemove(fname)
        wrapper.save(fname, format=foarmat)
        compareWrapper  = image_wrap.openImageFile(fname)
        self.assertTrue((compareWrapper.image_array == wrapper.image_array).all())

    def test_resize_images_with_save(self):
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


    # raw file not checked in
    def xtest_check_raw(self):
        args = {'Bits per Channel':'16'}
        res = image_wrap.openRaw(
            self.locateFile('tests/images/e957166e3eb7fd535567fc478dc506d4.arw'),
            args=args)
        if os.path.exists('test_16.png'):
            os.remove('test_16.png')
        self.addFileToRemove('test_16.png')
        res.save('test_16.png',format='PNG')
        self.assertTrue(os.path.exists('test_16.png'))
        image_wrap.deleteImage('test_16.png')
        res1 = image_wrap.openImageFile('test_16.png')
        self.assertTrue(res.image_array.shape == res1.image_array.shape)
        self.assertTrue(np.all(res.image_array == res1.image_array))

if __name__ == '__main__':
    unittest.main()
