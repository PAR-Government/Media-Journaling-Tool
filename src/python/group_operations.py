import plugins

class BaseOperation:
   
   scModel = None
   pairs = []

   def __init__(self, scModel):
      self.scModel = scModel
      self.pairs = self.scModel.getTerminalToBasePairs(suffix=self.suffix())

   def suffix(self):
      return ''
   
class ToJPGGroupOperation(BaseOperation):
   """ 
    A special group operation used to convert back to JPEG including
    EXIF Copy and Recompression with base image QT
   """

   def __init__(self,scModel):
       BaseOperation.__init__(self,scModel)

   def suffix(self):
       return '.jpg'

   def performOp(self):
       """
         Return error message valid link pairs in a tuple
       """
       newPairs = []
       msg = None
       for pair in self.pairs:
         self.scModel.selectImage(pair[0])
         im,filename=self.scModel.getImageAndName(pair[0])
         msg,pairs = self.scModel.imageFromPlugin('CompressAs',im,filename,donor=pair[1])
         if msg is not None:
             break
         newPairs.extend(pairs)
         start = self.scModel.end
         im,filename=self.scModel.getImageAndName(start)
         self.scModel.selectImage(start)
         msg,pairs = self.scModel.imageFromPlugin('ExifMetaCopy',im,filename,donor=pair[1])
         if msg is not None:
             break
         newPairs.extend(pairs)
       return (msg,newPairs)
