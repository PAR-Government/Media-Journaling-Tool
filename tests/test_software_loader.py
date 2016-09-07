from maskgen import software_loader
import unittest

def hasOp(list, name):
   for op in list:
     if op.name == name:
         return True
   return False

class TestSoftwareLoader(unittest.TestCase):

   def test_load(self):
      software_loader.loadOperations('operations.json')
      ops = software_loader.getOperationsByCategory('image','image')
      self.assertTrue(hasOp(ops['AdditionalEffect'],'AdditionalEffectAddLightSource'))
      self.assertTrue(hasOp(ops['AntiForensicExif'],'AntiForensicExifQuantizationTable'))
      self.assertFalse(hasOp(ops['Filter'],'FilterColorLUT'))
      self.assertFalse(hasOp(ops['Paste'],'PasteImageSpliceToFrames'))
      ops = software_loader.getOperationsByCategory('image','video')
      self.assertTrue(hasOp(ops['Paste'],'PasteImageSpliceToFrames'))

if __name__ == '__main__':
    unittest.main()
