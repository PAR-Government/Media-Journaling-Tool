from os.path import expanduser
import csv
import platform
import os
from maskgen_loader import MaskGenLoader

softwareset = {}
operations = {}
operationsByCategory = {}

def getOperations():
  global operations
  return operations

def getOperationsByCategory():
  global operationsByCategory
  return operationsByCategory

def getSoftwareSet():
  global softwareset
  return softwareset

def loadCSV(fileName):
   d={}
   with open(fileName) as f:
     for l in f.readlines():
         columns = l.split(',')
         if (len(columns) > 2):
           category = columns[0].strip()
         if not d.has_key(category):
           d[category] = []
           for x in columns[1:]:
             d[category].append(x.strip())
   return d

def loadOperations(fileName):
    global operations
    global operationsByCategory
    operations = loadCSV(fileName)
    for op,data in operations.iteritems():
      cat = data[0]
      if cat not in operationsByCategory:
        operationsByCategory[cat] = []
      operationsByCategory[cat].append(op)
    return operations

def loadSoftware(fileName):
    global softwareset
    softwareset = loadCSV(fileName)
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

   def get_versions(self,name):
     global softwareset
     return softwareset[name] if name in softwareset else []

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
