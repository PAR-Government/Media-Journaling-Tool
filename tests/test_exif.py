from maskgen import exif
from test_support import TestSupport
import unittest

class TestJpegUtils(TestSupport):

   def test_load(self):
     exif.getexif(self.locateFile('tests/videos/sample1.mov'))

if __name__ == '__main__':
    unittest.main()
