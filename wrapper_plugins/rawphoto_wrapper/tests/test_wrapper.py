import unittest

from rawphoto_wrapper import opener


class TestToolSet(unittest.TestCase):
    def test_acr2(self):
        ar, mode = opener.openRawFile('6fd98aa4f7fb69bdda4f187b27e03fec.cr2')
        self.assertEquals((ar.shape[0],ar.shape[1]), (5208,3476))
        self.assertEquals(mode,'RGB')

    def test_ref(self):
        ar, mode = opener.openRawFile('fujifilm_x_t1_20.raf')
        self.assertEquals((ar.shape[0], ar.shape[1]), (4936, 3296))
        self.assertEquals(mode, 'RGB')



if __name__ == '__main__':
    unittest.main()
