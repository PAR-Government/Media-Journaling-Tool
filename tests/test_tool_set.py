from maskgen import tool_set
import unittest
import numpy as np


class TestToolSet(unittest.TestCase):
    def test_filetype(self):
        self.assertEquals(tool_set.fileType('images/hat.jpg'), 'image')
        self.assertEquals(tool_set.fileType('images/sample.json'), 'video')

    def test_filetypes(self):
        self.assertTrue(("mov files", "*.mov") in tool_set.getFileTypes())
        self.assertTrue(("zipped masks", "*.tgz") in tool_set.getMaskFileTypes())

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
        os.remove('test_ts_gw_mask_43.293.mp4')


if __name__ == '__main__':
    unittest.main()
