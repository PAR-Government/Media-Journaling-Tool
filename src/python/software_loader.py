from os.path import expanduser
import csv
import platform
import os
from maskgen_loader import MaskGenLoader

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


class SoftwareLoader:

   software = []
   loader = MaskGenLoader()

   def __init__(self):
     self.software = self.load()

   def load(self):
     res = []
     #backward compatibility
     file = os.path.join(expanduser("~"),".maskgen")
     if os.path.exists(file):
        with open(file,"r") as csvfile:
           spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
           for row in spamreader:
             res.append(Software(row[0],row[1]))
     newset = self.loader.get_key('software')
     if newset is not None:
       for row in newset:
         res.append(Software(row[0],row[1]))
     return res

   def get_names(self):
     return list(set([s.name for s in self.software]))

   def get_versions(self):
     return list(set([s.version for s in self.software]))

   def add(self, software):
     f = False
     for s in self.software:
       if software.name == s.name and software.version == s.version:
         f= True
     if not f and software.name is not None and software.version is not None:
       self.software.append(software)
       return True
     return False

   def save(self):
      image = []
      for s in self.software:
        image.append([s.name, s.version])
      self.loader.save("software",image)
