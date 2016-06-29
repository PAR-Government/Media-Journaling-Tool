from os.path import expanduser
import csv
import platform
import os

def getOS():
  return platform.system() + ' ' + platform.release() + ' ' + platform.version()

class Software:
   name = None
   version = None

   def __init__(self, name, version):
     self.name = name
     self.version = version


class SoftwareLoader:

   software = []

   def __init__(self):
     self.software = self.load()

   def load(self):
     res = []
     file = os.path.join(expanduser("~"),".maskgen")
     if os.path.exists(file):
        with open(file,"r") as csvfile:
           spamreader = csv.reader(csvfile, delimiter=',', quotechar='"')
           for row in spamreader:
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
      file = os.path.join(expanduser("~"),".maskgen")
      with open(file,"w") as csvfile:
         spamwriter = csv.writer(csvfile, delimiter=',', quotechar='"',quoting=csv.QUOTE_MINIMAL)
         for s in self.software:
             spamwriter.writerow([s.name, s.version])
