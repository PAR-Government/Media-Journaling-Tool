from maskgen import tool_set
import unittest
import numpy as np
from maskgen import image_wrap
from test_support import TestSupport



class TestToolSet(TestSupport):
    def test_filetype(self):
        self.assertEquals(tool_set.fileType(self.locateFile('images/hat.jpg')), 'image')
        self.assertEquals(tool_set.fileType(self.locateFile('images/sample.json')), 'text')
        self.assertEquals(tool_set.fileType(self.locateFile('tests/videos/sample1.mov')), 'video')



    def test_filetypes(self):
        self.assertTrue(("mov files", "*.mov") in tool_set.getFileTypes())
        self.assertTrue(("zipped masks", "*.tgz") in tool_set.getMaskFileTypes())

    def test_zip(self):
        img = tool_set.openImage(self.locateFile('tests/zips/raw.zip'),tool_set.getMilliSecondsAndFrameCount('2'),preserveSnapshot=True)
        self.assertEqual((5796, 3870),img.size)
        tool_set.condenseZip(self.locateFile('tests/zips/raw.zip'),keep=1)



    def test_rotate(self):
        import cv2
        from maskgen import cv2api
        img1 = np.zeros((100,100),dtype=np.uint8)
        img1[20:50,40:50] = 1
        mask = np.ones((100,100),dtype=np.uint8)*255
        img1[20:50,40] = 2
        img = tool_set.applyRotateToCompositeImage(img1, 90, (50,50))
        self.assertTrue(sum(sum(img1-img))>40)
        img = tool_set.applyRotateToCompositeImage(img,-90,(50,50))
        self.assertTrue(sum(sum(img1-img)) <2)
        img = tool_set.applyRotateToComposite(-90, img1,  np.zeros((100,100),dtype=np.uint8), img1.shape, local=True)
        self.assertTrue(sum(img[40,:]) == sum(img1[:,40]))
        self.assertTrue(sum(img[40, :]) == 60)
        M = cv2.getRotationMatrix2D((35,45), -90, 1.0)
        img = cv2.warpAffine(img1, M, (img.shape[1], img.shape[0]),
                                     flags=cv2api.cv2api_delegate.inter_linear)

        mask[abs(img - img1) > 0] = 0
        #image_wrap.ImageWrapper(mask * 100).save('mask.png')
        #image_wrap.ImageWrapper(img*100).save('foo.png')
        img[10:15,10:15]=3
        img3 = tool_set.applyRotateToComposite(90, img, mask, img1.shape, local=True)
        self.assertTrue(np.all(img3[10:15,10:15]==3))
        img3[10:15, 10:15] = 0
        #self.assertTrue((sum(img1[20:50,40]) - sum(img3[24:54,44]))==0)
        #image_wrap.ImageWrapper(img3 * 100).save('foo2.png')


    def test_fileMask(self):
        pre = tool_set.openImageFile(self.locateFile('tests/images/prefill.png'))
        post = tool_set.openImageFile(self.locateFile('tests/images/postfill.png'))
        mask,analysis,error = tool_set.createMask(pre,post,invert=False,arguments={'tolerance' : 2500})
        withtolerance = sum(sum(mask.image_array))
        mask.save(self.locateFile('tests/images/maskfill.png'))
        mask, analysis,error = tool_set.createMask(pre, post, invert=False)
        withouttolerance = sum(sum(mask.image_array))
        mask, analysis ,error= tool_set.createMask(pre, post, invert=False, arguments={'tolerance': 2500,'equalize_colors':True})
        mask.save(self.locateFile('tests/images/maskfillt.png'))
        withtoleranceandqu = sum(sum(mask.image_array))
        self.assertTrue(withouttolerance < withtolerance)
        self.assertTrue(withtolerance <= withtoleranceandqu)

    def test_map(self):
            img1 = np.random.randint(0,255,size=(100,120)).astype('uint8')
            mask = np.ones((100,120))
            src_pts = [(x, y) for x in xrange(20, 30, 1) for y in xrange(50, 60, 1)]
            dst_pts = [(x, y) for x in xrange(55, 65, 1) for y in xrange(15, 25, 1)]
            result =tool_set._remap(img1,mask,src_pts,dst_pts)
            self.assertTrue(np.all(result[55:65,15:25] == img1[20:30,50:60]))

    def test_timeparse(self):
        t, f = tool_set.getMilliSecondsAndFrameCount('00:00:00')
        self.assertEqual(1, f)
        self.assertEqual(0, t)
        t, f = tool_set.getMilliSecondsAndFrameCount('1')
        self.assertEqual(1, f)
        self.assertEqual(0, t)
        self.assertTrue(tool_set.validateTimeString('03:10:10.434'))
        t,f = tool_set.getMilliSecondsAndFrameCount('03:10:10.434')
        self.assertEqual(0, f)
        self.assertEqual(1690434, t)
        t, f = tool_set.getMilliSecondsAndFrameCount('03:10:10.434:23')
        self.assertTrue(tool_set.validateTimeString('03:10:10.434:23'))
        self.assertEqual(23, f)
        self.assertEqual(1690434, t)
        t, f = tool_set.getMilliSecondsAndFrameCount('03:10:10:23')
        self.assertTrue(tool_set.validateTimeString('03:10:10:23'))
        self.assertEqual(23,f)
        self.assertEqual(1690000, t)
        t, f = tool_set.getMilliSecondsAndFrameCount('03:10:10:A')
        self.assertFalse(tool_set.validateTimeString('03:10:10:A'))
        self.assertEqual(0, 0)
        self.assertEqual(None, t)
        time_manager = tool_set.VidTimeManager(startTimeandFrame=(1000,2),stopTimeandFrame=(1003,4))
        time_manager.updateToNow(999)
        self.assertTrue(time_manager.isBeforeTime())
        time_manager.updateToNow(1000)
        self.assertTrue(time_manager.isBeforeTime())
        time_manager.updateToNow(1001)
        self.assertTrue(time_manager.isBeforeTime())
        time_manager.updateToNow(1002)
        self.assertFalse(time_manager.isBeforeTime())
        self.assertFalse(time_manager.isPastTime())
        time_manager.updateToNow(1003)
        self.assertFalse(time_manager.isPastTime())
        time_manager.updateToNow(1004)
        self.assertFalse(time_manager.isPastTime())
        time_manager.updateToNow(1005)
        self.assertFalse(time_manager.isPastTime())
        time_manager.updateToNow(1006)
        self.assertTrue(time_manager.isPastTime())
        time_manager.updateToNow(1007)
        self.assertTrue(time_manager.isPastTime())
        time_manager.updateToNow(1008)
        self.assertTrue(time_manager.isPastTime())
        self.assertEqual(8,time_manager.getEndFrame() )
        self.assertEqual(3, time_manager.getStartFrame())

        time_manager = tool_set.VidTimeManager(startTimeandFrame=(1000, 2), stopTimeandFrame=None)
        time_manager.updateToNow(999)
        self.assertTrue(time_manager.isBeforeTime())
        time_manager.updateToNow(1000)
        self.assertTrue(time_manager.isBeforeTime())
        time_manager.updateToNow(1001)
        self.assertFalse(time_manager.isBeforeTime())
        self.assertEqual(3, time_manager.getEndFrame())
        self.assertEqual(3, time_manager.getStartFrame())

    def test_opacity_analysis(self):
        # need to redo with generated data.
        initialImage = image_wrap.openImageFile(self.locateFile('tests/images/pre_blend.png'))
        finalImage = image_wrap.openImageFile(self.locateFile('tests/images/post_blend.png'))
        mask = image_wrap.openImageFile(self.locateFile('tests/images/blend_mask.png'))
        donorMask = image_wrap.openImageFile(self.locateFile('tests/images/donor_to_blend_mask.png'))
        donorImage = image_wrap.openImageFile(self.locateFile('tests/images/donor_to_blend.png'))
        result = tool_set.generateOpacityImage(initialImage.to_array(), donorImage.to_array(), finalImage.to_array(), mask.to_array(),
                                               donorMask.to_array(),None)
        min = np.min(result)
        max = np.max(result)
        result = (result - min)/(max-min) * 255.0
        print np.mean(result)

    def test_gray_writing(self):
        import os
        import sys
        writer = tool_set.GrayBlockWriter('test_ts_gw', 29.97002997)
        mask_set = list()
        for i in range(255):
            mask = np.random.randint(255, size=(1090, 1920)).astype('uint8')
            mask_set.append(mask)
            writer.write(mask, 33.3666666667,i+1)
        writer.close()
        fn = writer.get_file_name()
        reader = tool_set.GrayBlockReader(fn)
        pos = 0
        while True:
            mask = reader.read()
            if mask is None:
                break
            compare = mask == mask_set[pos]
            self.assertEqual(mask.size,sum(sum(compare)))
            pos += 1
        reader.close()
        self.assertEqual(255, pos)
        suffix = 'm4v'
        if sys.platform.startswith('win'):
            suffix = 'avi'
        self.assertEquals('test_ts_gw_mask_33.3666666667.' + suffix,tool_set.convertToVideo(fn))
        self.assertTrue(os.path.exists('test_ts_gw_mask_33.3666666667.' + suffix))

        size = tool_set.openImage('test_ts_gw_mask_33.3666666667.' + suffix, tool_set.getMilliSecondsAndFrameCount('00:00:01:2')).size
        print size
        self.assertTrue(size == (1920,1090))
        os.remove('test_ts_gw_mask_33.3666666667.'+suffix)
        os.remove('test_ts_gw_mask_33.3666666667.hdf5')


if __name__ == '__main__':
    unittest.main()
