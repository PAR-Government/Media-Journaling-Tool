from maskgen import tool_set
import unittest

class TestToolSet(unittest.TestCase):

   def test_filetype(self):
      self.assertEquals(tool_set.fileType('images/hat.jpg'),'image')
      self.assertEquals(tool_set.fileType('images/sample.json'),'video')

if __name__ == '__main__':
    unittest.main()
