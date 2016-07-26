from image_graph import ImageGraph
import shutil
import exif
import os
import numpy as np
from PIL import Image, ImageTk
import tool_set 
from software_loader import Software
import tempfile
import plugins
import graph_rules

def findProject(dir):
    if (dir.endswith(".json")):
       return os.path.abspath(dir)
    p = [filename for filename in os.listdir(dir) if filename.endswith(".json")]
    return  os.path.join(dir,p[0] if len(p)>0 else 'Untitled')

class Modification:
   operationName = None
   additionalInfo = ''
   category = None
   inputmaskpathname=None
   arguments = {}

   def __init__(self, name, additionalInfo, category=None,inputmaskpathname=None,arguments={}):
     self.additionalInfo  = additionalInfo
     self.operationName = name
     self.category = category
     self.inputmaskpathname = inputmaskpathname
     self.arguments = arguments

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

    def update_edge(self,mod,software=None):
        self.G.update_edge(self.start, self.end, \
            inputmaskpathname=mod.inputmaskpathname, \
            op=mod.operationName, \
            description=mod.additionalInfo, \
            softwareName=('' if software is None else software.name), \
            softwareVersion=('' if software is None else software.version))

    def compare(self, destination,seamAnalysis=True):
       im1 = self.getImage(self.start)
       im2 = self.getImage(destination)
       mask, analysis = tool_set.createMask(np.array(im1),np.array(im2), invert=False, seamAnalysis=seamAnalysis)
       return im1,im2,Image.fromarray(mask),analysis

    def getExifDiff(self):
      e = self.G.get_edge(self.start, self.end)
      if e is None:
          return None
      return e['exifdiff'] if 'exifdiff' in e else None

    def _compareImages(self,start,destination, invert=False):
       startIm,startFileName = self.getImageAndName(start)
       destIm,destFileName = self.getImageAndName(destination)
       mask,analysis = tool_set.createMask(np.array(startIm),np.array(destIm), invert=invert)
       maskname=start + '_' + destination + '_mask'+'.png'
       exifDiff = exif.compareexif(startFileName,destFileName)
       analysis = analysis if analysis is not None else {}
       analysis['exifdiff'] = exifDiff
       return maskname,mask, analysis

    def getNodeNames(self):
      return self.G.get_nodes()
      
    def getSoftware(self):
      e = self.G.get_edge(self.start, self.end)
      if e is None:
          return None
      return Software(e['softwareName'],e['softwareVersion'],'editable' in e and e['editable'] == 'no')

    def isEditableEdge(self,start,end):
      e = self.G.get_edge(start,end)
      return 'editable' not in e or e['editable'] == 'yes'

    def connect(self,destination,mod=Modification('Donor',''), software=None,invert=False, sendNotifications=True):
       if (self.start is None):
          return
       try:
         maskname, mask, analysis = self._compareImages(self.start,destination,invert=invert)
         if len(mod.arguments)>0:
            analysis['arguments'] = mod.arguments
         self.end = destination
         im = self.G.add_edge(self.start,self.end,mask=mask,maskname=maskname, \
              inputmaskpathname=mod.inputmaskpathname, \
              op=mod.operationName,description=mod.additionalInfo, \
              editable='yes', \
              softwareName=('' if software is None else software.name), \
              softwareVersion=('' if software is None else software.version), \
              **analysis)
         if (self.notify is not None and sendNotifications):
            self.notify(mod)
         return None
       except ValueError, msg:
         return msg

    def addNextImage(self, pathname, img, invert=False, mod=Modification('',''), software=None, sendNotifications=True):
       if (self.end is not None):
          self.start = self.end
       destination = self.G.add_node(pathname, seriesname=self.getSeriesName(), image=img)
       try:
         maskname, mask, analysis = self._compareImages(self.start,destination,invert=invert)
         if len(mod.arguments)>0:
            analysis['arguments'] = mod.arguments
         self.end = destination
         im= self.G.add_edge(self.start,self.end,mask=mask,maskname=maskname, \
              inputmaskpathname=mod.inputmaskpathname, \
              op=mod.operationName,description=mod.additionalInfo, \
              editable='no' if software.internal else 'yes', \
              softwareName=('' if software is None else software.name), \
              softwareVersion=('' if software is None else software.version), \
              **analysis)
         if (self.notify is not None and sendNotifications):
            self.notify(mod)
         return None
       except ValueError, msg:
         return msg

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
       self.start = None
       self.end = None
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
          return Modification(edge['op'],edge['description'], \
            inputmaskpathname=self.G.get_inputmaskpathname(self.start,self.end), \
            arguments = edge['arguments'] if 'arguments' in edge else {})
       return None

    def getImage(self,name):
       if name is None or name=='':
           return Image.fromarray(np.zeros((250,250,4)).astype('uint8'));
       return self.G.get_image(name)[0]

    def getImageAndName(self,name):
       if name is None or name=='':
           return Image.fromarray(np.zeros((250,250,4)).astype('uint8'));
       return self.G.get_image(name)

    def startImage(self):
       return self.getImage(self.start)

    def nextImage(self):
       return self.getImage(self.end)

    def maskImage(self):
       if (self.end is None):
           dim = (250,250,3) if self.start is None else self.getImage(self.start).size
           return Image.fromarray(np.zeros(dim).astype('uint8'));
       return self.G.get_edge_mask(self.start,self.end)

    def maskStats(self):
       if self.end is None:
          return ''
       edge = self.G.get_edge(self.start,self.end)
       if edge is None:
         return ''
       stat_names = ['ssim','psnr','username','shape change']
       return '  '.join([ key + ': ' + str(value) for key,value in edge.items() if key in stat_names ])

    def currentImage(self):
       if self.end is not None:
          return self.getImageAndName(self.end)
       elif self.start is not None:
          return self.getImageAndName(self.start)
       return None,None

    def selectImage(self,name):
      self.start = name
      self.end = None

    def selectPair(self, start, end):
      self.start = start
      self.end = end

    def remove(self):
       if (self.start is not None and self.end is not None):
           self.G.remove_edge(self.start, self.end)
           self.end = None
       else:
         name = self.start if self.end is None else self.end
         p = self.G.predecessors(self.start) if self.end is None else [self.start]
         self.G.remove(name, None)
         self.start = p[0] if len(p) > 0  else None
         self.end = None

    def getProjectData(self, item):
        return self.G.getDataItem(item)

    def setProjectData(self,item, value):
        self.G.setDataItem(item,value)

    def getVersion(self):
      return self.G.getVersion()

    def getGraph(self):
      return self.G

    def validate(self):
       total_errors = []
       for frm,to in self.G.get_edges():
          edge = self.G.get_edge(frm,to)
          op = edge['op'] 
          errors = graph_rules.run_rules(op,self.G,frm,to)
          if len(errors) > 0:
              total_errors.extend( [(frm,to,frm + ' => ' + to + ': ' + err) for err in errors])
       return total_errors

    def imageFromPlugin(self,filter,im, filename, **kwargs):
      op = plugins.getOperation(filter)
      suffix = filename[filename.rfind('.'):]
      preferred = plugins.getPreferredSuffix(filter)
      if preferred is not None:
          suffix = preferred
      target = os.path.join(tempfile.gettempdir(),self.G.new_name(os.path.split(filename)[1]))
      shutil.copy2(filename, target)
      copyExif = plugins.callPlugin(filter,im,target,**kwargs)
      msg = None
      if copyExif:
        msg = exif.copyexif(filename,target)
      description = Modification(op[0],filter + ':' + op[2],op[1])
      if 'inputmaskpathname' in kwargs:
         description.inputmaskpathname = kwargs['inputmaskpathname']
      sendNotifications = kwargs['sendNotifications'] if 'sendNotifications' in kwargs else True
      software = Software(op[3],op[4],internal=True)
      description.arguments = {k:v for k,v in kwargs.iteritems() if k != 'donor' and k != 'sendNotifications' and k != 'inputmaskpathname'}
      msg2 = self.addNextImage(target,None,mod=description,software=software,sendNotifications=sendNotifications)
      if msg2 is not None:
          if msg is None:
             msg = msg2
          else:
             msg = msg + "\n" + msg2
      os.remove(target)
      return msg

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
      im = tool_set.openImage(nfile)
      return im,nfile

    def openImage(self,nfile):
      im = None
      if nfile is not None and nfile != '':
          im = tool_set.openImage(nfile)
      return nfile,im

    def export(self, location):
      self.G.create_archive(location)

    def exporttos3(self, location):
      import boto3
      path = self.G.create_archive(tempfile.gettempdir())
      s3 = boto3.client('s3','us-east-1')
      BUCKET = location.split('/')[0].strip()
      DIR= location.split('/')[1].strip()
      print 'Upload to s3://' + BUCKET + '/' + DIR + '/' + os.path.split(path)[1] 
      s3.upload_file(path, BUCKET, DIR + '/' + os.path.split(path)[1])
      os.remove(path)

    def export_path(self, location):
      if self.end is None and self.start is not None:
         self.G.create_path_archive(location,self.start)
      elif self.end is not None:
         self.G.create_path_archive(location,self.end)

