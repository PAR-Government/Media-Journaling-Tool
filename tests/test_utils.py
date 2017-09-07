from maskgen.jpeg import utils

import unittest

class TestJpegUtils(unittest.TestCase):

   def test_load(self):
      self.assertEqual(91,utils.estimate_qf('./tests/images/test_project1.jpg'))
      self.assertEqual(100,utils.estimate_qf('./tests/images/test_project2.png'))

if __name__ == '__main__':
    unittest.main()
