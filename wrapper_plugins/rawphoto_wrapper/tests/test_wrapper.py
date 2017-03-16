import unittest

from rawphoto_wrapper import opener


class TestToolSet(unittest.TestCase):
    def test_aproject(self):
        ar, mode = opener.openRawFile('6fd98aa4f7fb69bdda4f187b27e03fec.cr2')
        self.assertEquals((ar.shape[0],ar.shape[1]), (3476, 5208))
        self.assertEquals(mode,'RGB')


if __name__ == '__main__':
    unittest.main()
