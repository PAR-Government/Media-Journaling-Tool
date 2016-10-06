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
        self.assertTrue(tool_set.isPastTime((1000,2),(1000,1)))
        self.assertTrue(tool_set.isPastTime((1001, 1), (1000, 2)))
        self.assertFalse(tool_set.isPastTime((1001, 1), (None, 2)))
        self.assertFalse(tool_set.isPastTime((1001, 1), (1001, 2)))
        self.assertFalse(tool_set.isPastTime((1000, 4), (1001, 2)))

    def test_gray_writing(self):
        import os
        writer = tool_set.GrayBlockWriter('test_ts_gw', 12)
        mask_set = list()
        for i in range(255):
            mask = np.random.randint(255, size=(512, 512)).astype('uint8')
            mask_set.append(mask)
            writer.write(mask, 43.293)
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
        self.assertEquals('test_ts_gw_mask_43.293.mp4',tool_set.convertToMP4(fn))
        self.assertTrue(os.path.exists('test_ts_gw_mask_43.293.mp4'))

        self.assertTrue(tool_set.openImage('test_ts_gw_mask_43.293.mp4',tool_set.getMilliSeconds('00:00:01:2')) is not None)
        os.remove('test_ts_gw_mask_43.293.mp4')


if __name__ == '__main__':
    unittest.main()
