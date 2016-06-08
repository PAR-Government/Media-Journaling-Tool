import jsonpickle

class Description:
    
   maskFileName = None
   operationName = None
   additionalInfo = ''

   def __init__(self, name, maskFileName):
     self.maskFileName = maskFileName
     self.operationName = name

class Scenario:
    initialFileName = None
    finalFileName = None
    descriptions = list()

    def __init__(self, initialFileName, finalFileName, descriptions):
        self.initialFileName = initialFileName
        self.finalFileName = finalFileName
        self.descriptions = descriptions

    def toJson(self):
        return jsonpickle.encode(self)
