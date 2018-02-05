from maskgen import software_loader
import unittest

class TestSoftwareLoader(unittest.TestCase):

   def test_load(self):
      ops = software_loader.getOperationsByCategory('image','image')
      self.assertTrue('Mosaic' in ops['AdditionalEffect'])
      self.assertTrue('AntiForensicExifQuantizationTable' in ops['AntiForensic'])
      self.assertFalse('FilterColorLUT' in ops['Filter'])
      self.assertFalse('PasteImageSpliceToFrames' in ops['Paste'])
      ops = software_loader.getOperationsByCategory('video','video')
      self.assertTrue('PasteImageSpliceToFrames' in ops['Paste'])

if __name__ == '__main__':
    unittest.main()
