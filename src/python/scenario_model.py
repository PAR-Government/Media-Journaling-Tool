from image_graph import ImageGraph
import os
import numpy as np
from PIL import Image, ImageTk
import tool_set


class Modification:
   operationName = None
   additionalInfo = ''

   def __init__(self, name, additionalInfo):
     self.additionalInfo  = additionalInfo
     self.operationName = name

class FileFinder:
    dir = '.'
    
    def __init__(self, dirname):
      self.dir = dirname

    def composeFileName(self, postFix):
        return os.path.abspath(os.path.join(self.dir,postFix))

    def findFiles(self, preFix, filterFunction):
        set= [os.path.abspath(os.path.join(self.dir,filename)) for filename in os.listdir(self.dir) if (filename.startswith(preFix)) and filterFunction(os.path.abspath(os.path.join(self.dir,filename)))]
        set.sort()
        return set

class ProjectModel:
    G = None
    start = None
    end = None
    filefinder = None

    def __init__(self, filefinder, projectName):
      self.filefinder = filefinder
      self.G = ImageGraph(projectName, self.filefinder.dir)

    def addImage(self, pathname):
       nname = self.G.add_node(pathname)
       self.start = nname
       self.end = None
       return nname

    def connect(self,destination,mod=Modification('Donor',''), invert=False):
       if (self.start is None):
          return
       mask = tool_set.createMask(np.array(self.G.get_image(self.start)),np.array(self.G.get_image(destination)), invert)
       maskname=self.start + '_' + destination + '_mask'+'.png'
       nin = self.filefinder.composeFileName(maskname)
       self.end = destination

       return self.G.add_edge(self.start,self.end,mask=mask,maskname=maskname,op=mod.operationName,description=mod.additionalInfo)

    def addNextImageFile(self, pathname, invert=False, mod=Modification('','')):
       if (self.end is not None):
          self.start = self.end
       fname = os.path.split(pathname)[1]
       nname = fname[0:fname.rfind('.')]
       nname = self.G.add_node(pathname, seriesname=self.getSeriesName())
       mask = tool_set.createMask(np.array(self.G.get_image(self.start)),np.array(self.G.get_image(nname)), invert)
       maskname=self.start + '_' + nname + '_mask'+'.png'
       self.end = nname
       return self.G.add_edge(self.start,self.end,mask=mask,maskname=maskname,op=mod.operationName,description=mod.additionalInfo)

    def saveToFile(self,pathname,img):
       fname = os.path.split(pathname)[1]
       nname = fname[0:fname.rfind('.')]
       suffix = fname[fname.rfind('.'):]
       f = None
       while True:
          f = self.filefinder.composeFileName(nname + '_' + str(self.G.nextId()) + suffix)
          if (not os.path.exists (f)):
             break
       img.save(f)
       return f

    def addNextImage(self,file,img,mod=Modification('','')):
       if (self.end is not None):
          self.start = self.end
       pathname = self.saveToFile(file, img)   
       fname = os.path.split(pathname)[1]
       nname = fname[0:fname.rfind('.')]
       nname = self.G.add_node(pathname, seriesname=self.getSeriesName())
       mask = tool_set.createMask(np.array(self.G.get_image(self.start)),np.array(self.G.get_image(nname)), False)
       maskname=self.start + '_' + nname + '_mask'+'.png'
       self.end = nname
       return self.G.add_edge(self.start,self.end,mask=mask,maskname=maskname,op=mod.operationName,description=mod.additionalInfo)

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

    def startNew(self,name):
      self.start = None
      self.end = None
      self.G = ImageGraph(name,self.filefinder.dir)

    def load(self,fname):
       self.G.load(fname)
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

    def saveas(self, path, name):
       self.G.set_name(name)
       self.G.save()

    def save(self):
       self.G.save()

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
       def maskRemover(edge):
          f = self.filefinder.composeFileName(edge['maskname'])
          if (os.path.exists(f)):
             os.remove(f)
       name = self.start if self.end is None else self.end
       p = self.G.predecessors(self.start) if self.end is None else [self.start]
       self.G.remove(name, maskRemover)
       self.start = p[0] if len(p) > 0  else None
       print self.start
       self.end = None

    def getGraph(self):
      return self.G

    def scanNextImage(self):
      if (self.start is None):
         return None,None

      startNode = self.G.get_node(self.start)
      suffix = self.start
      seriesName = self.getSeriesName()
      if seriesName is not None:
         suffix = seriesName

      def filterF (file):
         return not self.G.has_node(os.path.split(file[0:file.rfind('.')])[1]) and not(file.rfind('_mask')>0)
      
      # if the user is writing to the same output file
      # in a lock step process with the changes
      # then nfile remains the same name is changed file
      nfile = self.filefinder.composeFileName(startNode['file'])
      for file in self.filefinder.findFiles(suffix, filterF):
         nfile = file
         break
      with open(nfile) as fp:
         im = Image.open(fp)
         im.load()

      return nfile,im

    def openImage(self,nfile):
      im = None
      if nfile is not None:
         with open(nfile) as fp:
           im = Image.open(fp)
           im.load()
      return nfile,im
