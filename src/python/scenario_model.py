from image_graph import ImageGraph
import os
import numpy as np
from PIL import Image, ImageTk
import tool_set


def findProject(dir):
    if (dir.endswith(".json")):
       return os.path.abspath(dir)
    p = [filename for filename in os.listdir(dir) if filename.endswith(".json")]
    return  os.path.join(dir,p[0] if len(p)>0 else 'Untitled')

class Modification:
   operationName = None
   additionalInfo = ''
   category = None

   def __init__(self, name, additionalInfo, category=None):
     self.additionalInfo  = additionalInfo
     self.operationName = name
     self.category = category

class ProjectModel:
    G = None
    start = None
    end = None

    def __init__(self, projectFileName, notify=None):
      self.G = ImageGraph(projectFileName)
      self._setup()
      self.notify = notify

    def get_dir(self):
       return self.G.dir

    def addImage(self, pathname):
       nname = self.G.add_node(pathname)
       self.start = nname
       self.end = None
       return nname

    def update_edge(self,mod):
        self.G.update_edge(self.start, self.end, mod.operationName, mod.additionalInfo)

    def connect(self,destination,mod=Modification('Donor',''), invert=False):
       if (self.start is None):
          return
       mask = tool_set.createMask(np.array(self.G.get_image(self.start)),np.array(self.G.get_image(destination)), invert)
       maskname=self.start + '_' + destination + '_mask'+'.png'
       self.end = destination
       im = self.G.add_edge(self.start,self.end,mask=mask,maskname=maskname,op=mod.operationName,description=mod.additionalInfo)
       if (self.notify is not None):
          self.notify(mod)
       return im

    def addNextImage(self, pathname, img, invert=False, mod=Modification('','')):
       if (self.end is not None):
          self.start = self.end
       nname = self.G.add_node(pathname, seriesname=self.getSeriesName(), image=img)
       mask = tool_set.createMask(np.array(self.G.get_image(self.start)),np.array(self.G.get_image(nname)), invert)
       maskname=self.start + '_' + nname + '_mask'+'.png'
       self.end = nname
       im= self.G.add_edge(self.start,self.end,mask=mask,maskname=maskname,op=mod.operationName,description=mod.additionalInfo)
       if (self.notify is not None):
          self.notify(mod)
       return im

    def getSeriesName(self):
       if (self.start is None):
          None
       startNode = self.G.get_node(self.start)
       suffix = None
       if (startNode.has_key('seriesname')):
         suffix = startNode['seriesname']
       if (self.end is not None):
          endNode = self.G.get_node(self.end)
          if (endNode.has_key('seriesname')):
            suffix = startNode['seriesname']
       return suffix

    def getName(self):
     return self.G.get_name()

    def startImageName(self):
      return self.start if self.start is not None else ""
    
    def nextImageName(self):
      return self.end if self.end is not None else ""

    def undo(self):
       self.start = None
       self.end = None
       self.G.undo()

    def select(self,edge):
      self.start= edge[0]
      self.end = edge[1]

    def startNew(self,pathname):
      self.G = ImageGraph(pathname)
      self.start = None
      self.end = None

    def load(self,pathname):
       self.G.load(pathname)
       self._setup()

    def _setup(self):
       n = self.G.get_nodes()
       if (len(n) > 0):
           self.start = n[0]
           s = self.G.successors(n[0])
           if (len(s) > 0):
              self.end = s[0]
           else:
              p = self.G.predecessors(n[0])
              if (len(p)>0):
                 self.start = p[0]
                 self.end = n[0]

    def saveas(self,pathname):
       self.G.saveas(pathname)

    def save(self):
       self.G.save()

    def getDescription(self):
       if (self.start is None or self.end is None):
          return None
       edge = self.G.get_edge(self.start, self.end)
       if edge is not None:
          return Modification(edge['op'],edge['description'])
       return None

    def startImage(self):
       if (self.start is None):
           return Image.fromarray(np.zeros((500,500,3)).astype('uint8'));
       return self.G.get_image(self.start)

    def nextImage(self):
       if (self.end is None):
           return Image.fromarray(np.zeros((500,500,3)).astype('uint8'));
       return self.G.get_image(self.end)

    def maskImage(self):
       if (self.end is None):
           return Image.fromarray(np.zeros((500,500,3)).astype('uint8'));
       return self.G.get_edge_mask(self.start,self.end)

    def currentImage(self):
       file = None
       im = None
       if self.end is not None:
          file=self.G.get_node(self.end)['file']
          im=self.nextImage()
       elif self.start is not None:
          file=self.G.get_node(self.start)['file']
          im=self.startImage()
       return file,im

    def selectImage(self,name):
      self.start = name
      self.end = None

    def selectPair(self, start, end):
      self.start = start
      self.end = end

    def remove(self):
       name = self.start if self.end is None else self.end
       p = self.G.predecessors(self.start) if self.end is None else [self.start]
       self.G.remove(name, None)
       self.start = p[0] if len(p) > 0  else None
       print self.start
       self.end = None

    def getGraph(self):
      return self.G

    def scanNextImage(self):
      if (self.start is None):
         return None,None

      suffix = self.start
      seriesName = self.getSeriesName()
      if seriesName is not None:
         suffix = seriesName

      def filterFunction (file):
         return not self.G.has_node(os.path.split(file[0:file.rfind('.')])[1]) and not(file.rfind('_mask')>0)

      def findFiles(dir, preFix, filterFunction):
         set= [os.path.abspath(os.path.join(dir,filename)) for filename in os.listdir(dir) if (filename.startswith(preFix)) and filterFunction(os.path.abspath(os.path.join(dir,filename)))]
         set.sort()
         return set
      
      # if the user is writing to the same output file
      # in a lock step process with the changes
      # then nfile remains the same name is changed file
      nfile = self.G.get_pathname(self.start)
      for file in findFiles(self.G.dir,suffix, filterFunction):
         nfile = file
         break
      with open(nfile,"rb") as fp:
         im = Image.open(fp)
         im.load()

      return nfile,im

    def openImage(self,nfile):
      im = None
      if nfile is not None:
         with open(nfile,"rb") as fp:
           im = Image.open(fp)
           im.load()
      return nfile,im



