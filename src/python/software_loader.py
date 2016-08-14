from os.path import expanduser
import csv
import platform
import os
from maskgen_loader import MaskGenLoader
from json import JSONEncoder
import json

class OperationEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__ 

softwareset = {}
operations = {}
operationsByCategory = {}


class Operation:
   name = None
   category = None
   includeInMask = False
   description = None
   optionalparameters = []
   mandatoryparameters = []
   rules = []

   def __init__(self, name='', category='', includeInMask=False, rules=[],optionalparameters=[],mandatoryparameters=[],description=None):
     self.name = name
     self.category = category
     self.includeInMask = includeInMask
     self.rules = rules
     self.mandatoryparameters = mandatoryparameters
     self.optionalparameters = optionalparameters
     self.description = description

    
   def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)

def getOperation(name):
   global operations
   return operations[name] if name in operations else None

def getOperations():
  global operations
  return operations

def getOperationsByCategory():
  global operationsByCategory
  return operationsByCategory

def getSoftwareSet():
  global softwareset
  return softwareset

def saveJSON(filename):
    global operations
    opnamelist = list(operations.keys())
    opnamelist.sort()
    oplist = [operations[op] for op in opnamelist]
    with open(filename,'w') as f:
      json.dump({'operations' : oplist},f,indent=2,cls=OperationEncoder)

def loadJSON(fileName):
    res = {}
    with open(fileName,'r') as f:
      ops = json.load(f)
      for op in ops['operations']:
        res[op['name']]= Operation(name=op['name'],category=op['category'],includeInMask=op['includeInMask'], rules=op['rules'],optionalparameters=op['optionalparameters'],mandatoryparameters=op['mandatoryparameters'],description=op['description'] if 'description' in op else None)
    return res

def loadOperations(fileName):
    global operations
    global operationsByCategory
    operations = loadJSON(fileName)
    operationsByCategory = {}
    for op,data in operations.iteritems():
      category =  data.category
      if category not in operationsByCategory:
        operationsByCategory[category] = []
      operationsByCategory[category].append(op)
    return operations

def toSoftware(columns):
   return [x.strip() for x in columns[1:] if len(x)>0]

def loadSoftware(fileName):
    global softwareset
    softwareset = loadCSV(fileName,toSoftware)
    return softwareset

def getOS():
  return platform.system() + ' ' + platform.release() + ' ' + platform.version()

def validateSoftware(softwareName,softwareVersion):
     global softwareset
     return softwareName in softwareset and softwareVersion in softwareset[softwareName]

class Software:
   name = None
   version = None
   internal = False

   def __init__(self, name, version, internal=False):
     self.name = name
     self.version = version
     self.internal=internal

class SoftwareLoader:

   software = {}
   preference = None
   loader = MaskGenLoader()

   def __init__(self):
     self.load()

   def load(self):
     global softwareset
     res = {}
     self.preference = self.loader.get_key('software_pref')
     newset = self.loader.get_key('software')
     if newset is not None:
       if type(newset) == list:
         for item in newset:
            if validateSoftware(item[0],item[1]):
               res[item[0]] = item[1]
       else:
         for name,version in newset.iteritems():
            if validateSoftware(name,version):
               res[name] = version
     self.software = res

   def get_preferred_version(self,name=None):
    if self.preference is not None and (name is None or name == self.preference[0]):
      return self.preference[1]
    if len(self.software) > 0:
      if name in self.software:
        return self.software[name]
      elif name is None:
        return self.software[self.software.keys()[0]]
    return None

   def get_preferred_name(self):
    if self.preference is not None:
      return self.preference[0]
    if len(self.software) > 0:
      return self.software.keys()[0]
    return None

   def get_names(self):
     global softwareset
     return list(softwareset.keys())

   def get_versions(self,name,version=None):
     global softwareset
     versions = softwareset[name] if name in softwareset else []
     if version is not None and version not in versions:
       print version + ' not in approved set for software ' + name
       versions = list(versions)
       versions.append(version)
     return versions

   def add(self, software):
     isChanged = False
     if validateSoftware(software.name,software.version):
        if not software.name in self.software or self.software[software.name] != software.version:
          self.software[software.name] = software.version
          isChanged = True
        pref = self.preference
        if pref is None or pref[0] != software.name or pref[1] != software.version:
           self.preference = [software.name,software.version]
           isChanged = True
     return isChanged

   def save(self):
      self.loader.saveall([("software",self.software),("software_pref",self.preference)])
