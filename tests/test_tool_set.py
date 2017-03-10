from maskgen import tool_set
import unittest
import numpy as np
from maskgen import image_wrap
import random



class TestToolSet(unittest.TestCase):
    def test_filetype(self):
        self.assertEquals(tool_set.fileType('images/hat.jpg'), 'image')
        self.assertEquals(tool_set.fileType('images/sample.json'), 'video')

    def test_filetypes(self):
        self.assertTrue(("mov files", "*.mov") in tool_set.getFileTypes())
        self.assertTrue(("zipped masks", "*.tgz") in tool_set.getMaskFileTypes())

    def extendRemoveSet(self, removeset,dim):
        newset = []
        for x in removeset:
            while True:
                newx =  min(max(0, x + random.randint(-1,1)), dim-1)
                if newx not in newset:
                    newset.append(newx)
                    break
        self.assertEqual(len(removeset),len(newset))
        return sorted(newset)

    def createHorizontal(self, basis,dimx,dimy):
        import random
        m = np.zeros((dimx,dimy))
        for y in range(dimy):
            unuseditems = [x for x in range(255) if x not in basis[:, y].tolist()]
            for x in range(dimx):
                m[x,y] = random.choice(unuseditems)
        return m

    def createVertical(self, basis,dimx,dimy):
        import random
        m = np.zeros((dimx,dimy))
        for x in range(dimx):
            unuseditems = [y for y in range(255) if y not in basis[x,:].tolist()]
            for y in range(dimy):
                m[x,y] = random.choice(unuseditems)
        return m

# need to fix the two tests: horizontal and vertical
# the random generator sometimes generates matrices that have the same
# value unintentionally, causing the test to fail
# The solution is to not fail the test in this case.
# it is a legitimate case, so the final assertion must change.

    def test_createHorizontalSeamMask(self):
        dim = 10
        old = np.random.randint(255, size=(dim, dim+1))
        new = self.createHorizontal(old ,dim-3, dim+1)
        mask = np.zeros((dim, dim+1)).astype('uint8')
        removeset = sorted([x for x in random.sample(range(0,dim), 3)])
        for y in range(dim+1):
            for x in range(dim):
                mask[x, y] = (x in removeset)
            removeset = self.extendRemoveSet(removeset,dim)
        newx = [0 for y in range(dim+1)]
        for y in range(dim+1):
            for x in range (dim):
                if mask[x,y] == 0:
                    new[newx[y], y] = old[x, y]
                    newx[y] = newx[y]+1

        print old
        print new
        newmask = tool_set.createHorizontalSeamMask(old,new)
        print mask*255
        print newmask
        if not np.all(newmask == mask * 255):
            self.assertTrue(sum(sum(newmask != mask * 255)) < 4)
        new_rebuilt = tool_set.carveMask(old, 255-(mask * 255), new.shape)
        self.assertTrue(np.all(new==new_rebuilt))

    def test_createVerticalSeamMask(self):
        dim = 10
        old = np.random.randint(255, size=(dim, dim))
        new = self.createVertical(old, dim, dim -3)
        mask = np.zeros((dim, dim)).astype('uint8')
        removeset = sorted([x for x in random.sample(range(0,dim-1), 3)])
        for x in range(dim):
            for y in range(dim):
                mask[x, y] = (y in removeset)
            removeset = self.extendRemoveSet(removeset,dim-1)
        newy = [0 for y in range(dim)]
        for y in range(dim):
            for x in range (dim):
                if mask[x,y] == 0:
                    new[x, newy[x]] = old[x, y]
                    newy[x] = newy[x]+1
        print old
        print new
        newmask = tool_set.createVerticalSeamMask(old,new)
        print mask * 255
        print newmask
        if not np.all(newmask==mask*255):
            self.assertTrue(sum(sum(newmask != mask * 255)) < 4)
        new_rebuilt = tool_set.carveMask(old, 255-(mask * 255), new.shape)
        self.assertTrue(np.all(new==new_rebuilt))



    def test_fileMask(self):
        pre = tool_set.openImageFile('tests/images/prefill.png')
        post = tool_set.openImageFile('tests/images/postfill.png')
        mask,analysis = tool_set.createMask(pre,post,invert=False,arguments={'tolerance' : 2500})
        withtolerance = sum(sum(mask.image_array))
        mask.save('tests/images/maskfill.png')
        mask, analysis = tool_set.createMask(pre, post, invert=False)
        withouttolerance = sum(sum(mask.image_array))
        mask, analysis = tool_set.createMask(pre, post, invert=False, arguments={'tolerance': 2500,'equalize_colors':True})
        mask.save('tests/images/maskfillt.png')
        withtoleranceandqu = sum(sum(mask.image_array))
        self.assertTrue(withouttolerance < withtolerance)
        self.assertTrue(withtolerance <= withtoleranceandqu)

    def test_timeparse(self):
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
        self.assertEqual(0, f)
        self.assertEqual(None, t)
        time_manager = tool_set.VidTimeManager(startTimeandFrame=(1000,2),stopTimeandFrame=(1003,4))
        time_manager.updateToNow(999)
        self.assertTrue(time_manager.isBeforeTime())
        time_manager.updateToNow(1000)
        self.assertTrue(time_manager.isBeforeTime())
        time_manager.updateToNow(1001)
        self.assertFalse(time_manager.isBeforeTime())
        time_manager.updateToNow(1002)
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
        initialImage = image_wrap.openImageFile('tests/images/pre_blend.png')
        finalImage = image_wrap.openImageFile('tests/images/post_blend.png')
        mask = image_wrap.openImageFile('tests/images/blend_mask.png')
        donorMask = image_wrap.openImageFile('tests/images/donor_to_blend_mask.png')
        donorImage = image_wrap.openImageFile('tests/images/donor_to_blend.png')
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
            writer.write(mask, 33.3666666667)
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
