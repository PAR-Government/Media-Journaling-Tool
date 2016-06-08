import json

def handle_model(o):
    if isinstance(o, set):
        return list(o)
    return o.__dict__

class Modification:
    
   maskFileName = None
   operationName = None
   additionalInfo = ''

   def __init__(self, name, maskFileName):
     self.maskFileName = maskFileName
     self.operationName = name

class Scenario:
    initialFileName = None
    modifiedFileName = None
    modifications = list()

    def __init__(self, initialFileName, modifiedFileName, modifications):
        self.initialFileName = initialFileName
        self.modifiedFileName = modifiedFileName
        self.modifications = modifications

    def toJson(self):
        return json.dumps(self, default=handle_model)

    def fromJson(self, jsonStr):
         d = json.loads(jsonStr)
         if 'initialFileName' in d:
           self.initialFileName = d['initialFileName']
         if 'modifiedFileName' in d:
           self.modifiedFileName = d['modifiedFileName']
         if 'modifications' in d:
            for modDict in d['modifications']:
               mod = Modification(modDict['operationName'], modDict['maskFileName'])
               if 'additionalInfo' in modDict:
                  mod.additionalInfo = modDict['additionalInfo']
               self.modifications.append(mod)

