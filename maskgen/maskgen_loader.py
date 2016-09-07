from os.path import expanduser
import csv
import platform
import os
import json

globalImage = {}
imageLoaded = False

class MaskGenLoader:

   def __init__(self):
     self.load()

   def load(self):
     global globalImage
     global imageLoaded
     if imageLoaded:
       return
     file = os.path.join(expanduser("~"),".maskgen2")
     if os.path.exists(file):
        with open(file,"r") as jsonfile:
          globalImage = json.load(jsonfile)
     imageLoaded = True

   def get_key(self,id):
     global globalImage
     return globalImage[id] if id in globalImage else None

   def save(self,id,data):
     global globalImage
     globalImage[id] = data
     file = os.path.join(expanduser("~"),".maskgen2")
     with open(file, 'w') as f:
       json.dump(globalImage,f,indent=2)

   def saveall(self,idanddata):
     global globalImage
     for id,data in idanddata:
       globalImage[id] = data
     file = os.path.join(expanduser("~"),".maskgen2")
     with open(file, 'w') as f:
       json.dump(globalImage,f,indent=2)
