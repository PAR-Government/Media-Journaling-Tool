import unittest

import numpy as np

class TestToolSet(unittest.TestCase):
    def test_all(self):
        from jpeg2000_wrapper import opener
        img = np.random.randint(0, high=255, size=(2000, 4000, 6), dtype=np.uint8)
        opener.writeJPeg2000File('foo.jp2',img)
        newimg = opener.openJPeg2000File('foo.jp2')
        self.assertTrue(np.all(img == newimg[0]))


if __name__ == '__main__':
    unittest.main()
