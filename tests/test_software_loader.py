from maskgen import software_loader
import unittest

class TestSoftwareLoader(unittest.TestCase):

   def test_load(self):
      software_loader.loadOperations('operations.json')
      ops = software_loader.getOperationsByCategory('image','image')
      self.assertTrue('AdditionalEffectAddLightSource' in ops['AdditionalEffect'])
      self.assertTrue('AntiForensicExifQuantizationTable' in ops['AntiForensicExif'])
      self.assertFalse('FilterColorLUT' in ops['Filter'])
      self.assertFalse('PasteImageSpliceToFrames' in ops['Paste'])
      ops = software_loader.getOperationsByCategory('image','video')
      self.assertTrue('PasteImageSpliceToFrames' in ops['Paste'])

if __name__ == '__main__':
    unittest.main()
