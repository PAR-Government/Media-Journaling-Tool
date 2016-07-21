from os.path import expanduser
import csv
import platform
import os
from maskgen_loader import MaskGenLoader

softwareset = {}
operations = {}

def getOperations():
  global operations
  return operations

def getSoftwareSet()
  global softwareset
  return softwareset

def loadCSV(filename)
    d={}
    with open(fileName) as f:
        for l in f.readlines():
            columns = l.split(',')
            if (len(columns) > 2):
              category = columns[1].strip()
              if not d.has_key(category):
                  d[category] = []
              d[category].append(columns[0].strip())
   return d

def loadOperations(fileName):
    global operations
    operations = loadCSV(filename)
    return operation

def loadSoftware(fileName):
    global softwareset
    softwareset = loadCSV(filename)
    return softwareset

def getOS():
  return platform.system() + ' ' + platform.release() + ' ' + platform.version()


class Software:
   name = None
   version = None
   internal = False

   def __init__(self, name, version, internal=False):
     self.name = name
     self.version = version
     self.internal=internal

def validateSoftware(self,softwareName,softwareVersion):
     global softwareset
     return softwareName in softwareset and softwareVersion in softwareset[softwareName]

class SoftwareLoader:

   software = {}
   preference = None
   loader = MaskGenLoader()

   def __init__(self):
     self.load(self)

   def load(self):
     global softwareset
     res = {}
     self.preference = self.loader.get_key('software_pref')
     newset = self.loader.get_key('software')
     if newset is not None:
       if type(newset) == list:
         for item in newset:
            if validateSoftware(item[0],item[1])
               res[item[0]] = item[1]
       else 
         for name,version in newset.iteritems():
            if validateSoftware(name,version)
               res[name] = version
     self.software = res

   def get_preferred_version(self):
    if self.preference is not None:
      return self.preference[1]
    if len(self.software) > 0:
      return self.software[self.software.keys()[0]]
    return None

   def get_preferred_name(self)
    if self.preference is not None:
      return self.preference[0]
    if len(self.software) > 0:
      return self.software.keys()[0]
    return None

   def get_names(self):
     global softwareset
     return list(softwareset.keys())

   def get_versions(self,name):
     return softwareset[name] if name in softwareset else []

   def add(self, software):
     isChanged = False
     if validateSoftware(software.name,software.version):
        if not software.name in self.software or self.software[software.name] != software.version:
          self.software[software.name] = software.version
          isChanged = True
        pref = self.preference
        if pref is None or pref[0] != name or pref[1] != version
           self.preference = [software.name,software.version]
           isChanged = True
        
        return True
     return False

   def save(self):
      self.loader.saveall([("software",self.software),("software_pref",self.preference)])
