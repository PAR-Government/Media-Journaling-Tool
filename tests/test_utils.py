from maskgen.jpeg import utils

import unittest
from test_support import TestSupport
class TestJpegUtils(TestSupport):

   def test_load(self):
      self.assertEqual(91,utils.estimate_qf(self.locateFile('tests/images/test_project1.jpg')))

if __name__ == '__main__':
    unittest.main()
