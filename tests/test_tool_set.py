from maskgen import tool_set
import unittest

class TestToolSet(unittest.TestCase):

   def test_filetype(self):
      self.assertEquals(tool_set.fileType('images/hat.jpg'),'image')
      self.assertEquals(tool_set.fileType('images/sample.json'),'video')

   def test_filetypes(self):
      self.assertTrue(("mov files","*.mov") in tool_set.getFileTypes() )
      self.assertTrue(("zipped masks","*.tgz") in tool_set.getMaskFileTypes() )

if __name__ == '__main__':
    unittest.main()
