from maskgen import tool_set
import unittest
import numpy as np
from maskgen import image_wrap



class TestToolSet(unittest.TestCase):
    def test_filetype(self):
        self.assertEquals(tool_set.fileType('images/hat.jpg'), 'image')
        self.assertEquals(tool_set.fileType('images/sample.json'), 'video')

    def test_filetypes(self):
        self.assertTrue(("mov files", "*.mov") in tool_set.getFileTypes())
        self.assertTrue(("zipped masks", "*.tgz") in tool_set.getMaskFileTypes())


    def test_fileMask(self):
        pre = tool_set.openImageFile('tests/prefill.png')
        post = tool_set.openImageFile('tests/postfill.png')
        mask,analysis = tool_set.createMask(pre,post,invert=False,arguments={'tolerance' : 25})
        withtolerance = sum(sum(mask.image_array))
        mask.save('tests/maskfill.png')
        mask, analysis = tool_set.createMask(pre, post, invert=False)
        withouttolerance = sum(sum(mask.image_array))
        mask, analysis = tool_set.createMask(pre, post, invert=False, arguments={'tolerance': 25,'equalize_colors':True})
        mask.save('tests/maskfillt.png')
        withtoleranceandqu = sum(sum(mask.image_array))
        self.assertTrue(withouttolerance < withtolerance)
        self.assertTrue(withtolerance < withtoleranceandqu)

    def test_timeparse(self):
        self.assertTrue(tool_set.validateTimeString('03:10:10.434'))
        t,f = tool_set.getMilliSeconds('03:10:10.434')
        self.assertEqual(0, f)
        self.assertEqual(1690434, t)
        t, f = tool_set.getMilliSeconds('03:10:10.434:23')
        self.assertTrue(tool_set.validateTimeString('03:10:10.434:23'))
        self.assertEqual(23, f)
        self.assertEqual(1690434, t)
        t, f = tool_set.getMilliSeconds('03:10:10:23')
        self.assertTrue(tool_set.validateTimeString('03:10:10:23'))
        self.assertEqual(23,f)
        self.assertEqual(1690000, t)
        t, f = tool_set.getMilliSeconds('03:10:10:A')
        self.assertFalse(tool_set.validateTimeString('03:10:10:A'))
        self.assertEqual(0, f)
        self.assertEqual(None, t)
        time_manager = tool_set.VidTimeManager(startTimeandFrame=(1000,2),stopTimeandFrame=(1003,4))
        self.assertTrue(time_manager.isBeforeTime(999))
        self.assertTrue(time_manager.isBeforeTime(1000))
        self.assertFalse(time_manager.isBeforeTime(1001))
        self.assertFalse(time_manager.isPastTime(1002))
        self.assertFalse(time_manager.isPastTime(1003))
        self.assertFalse(time_manager.isPastTime(1004))
        self.assertFalse(time_manager.isPastTime(1005))
        self.assertTrue(time_manager.isPastTime(1005))


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

        size = tool_set.openImage('test_ts_gw_mask_33.3666666667.' + suffix,tool_set.getMilliSeconds('00:00:01:2')).size
        print size
        self.assertTrue(size == (1920,1090))
        os.remove('test_ts_gw_mask_33.3666666667.'+suffix)
        os.remove('test_ts_gw_mask_33.3666666667.hdf5')


if __name__ == '__main__':
    unittest.main()
