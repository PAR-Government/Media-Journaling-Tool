from image_graph import ImageGraph,VideoGraph
import shutil
import exif
import os
import numpy as np
from PIL import Image, ImageTk
import tool_set 
import video_tools
from software_loader import Software,Operation,getOperation
import tempfile
import plugins
import graph_rules

def toIntTuple(tupleString):
   import re
   if tupleString is not None and tupleString.find(',') > 0:
     return tuple([int(re.sub('[()]','',x)) for x in tupleString.split(',')])
   return (0,0)

def imageProjectModelFactory(name,**kwargs):
    return ImageProjectModel(name,**kwargs)

def videoProjectModelFactory(name,**kwargs):
    return VideoProjectModel(name,**kwargs)

def createProject(dir,notify=None,base=None,suffixes = [],projectModelFactory=imageProjectModelFactory,organization=None):
    """ This utility function creates a ProjectModel given a directory.
        If the directory contains a JSON file, then that file is used as the project file.
        Otherwise, the directory is inspected for images.
        All images found in the directory are imported into the project.
        If the 'base' parameter is provided, the project is named based on that image name.
        If the 'base' parameter is not provided, the project name is set based on finding the
        first image in the list of found images, sorted in lexicographic order, starting with JPG, then PNG and then TIFF.
        Returns an error message upon error, otherwise None
    """

    if (dir.endswith(".json")):
       return projectModelFactory(os.path.abspath(dir),notify=notify),False
    selectionSet = [filename for filename in os.listdir(dir) if filename.endswith(".json")]
    if len(selectionSet) != 0 and base is not None:
        print 'Cannot add base image/video to an existing project'
        return None
    if len(selectionSet) == 0 and base is None:
       print 'No project found and base image/video not provided; Searching for a base image/video'
       suffixPos = 0
       while len(selectionSet) == 0 and suffixPos < len(suffixes):
          suffix = suffixes[suffixPos]
          selectionSet = [filename for filename in os.listdir(dir) if filename.lower().endswith(suffix)]
          selectionSet.sort()
          suffixPos+=1
       projectFile = selectionSet[0] if len(selectionSet) > 0 else None
       if projectFile is None:
         print 'Could not find a base image/video'
         return None
    # add base is not None
    elif len(selectionSet) == 0: 
       projectFile = os.path.split(base)[1]
    else:
       projectFile = selectionSet[0]
    projectFile = os.path.abspath(os.path.join(dir,projectFile))
    if not os.path.exists(projectFile):
      print 'Base project file ' + projectFile + ' not found'
      return None
    image = None
    existingProject = projectFile.endswith(".json")
    if  not existingProject:
        image = projectFile
        projectFile = projectFile[0:projectFile.rfind(".")] + ".json"
    model=  projectModelFactory(projectFile,notify=notify)
    if organization is not None:
      model.setProjectData('organization',organization)
    if  image is not None:
       model.addImagesFromDir(dir,baseImageFileName=os.path.split(image)[1],suffixes=suffixes, \
                           sortalg=lambda f: os.stat(os.path.join(dir, f)).st_mtime)
    return model,not existingProject

class MetaDiff:
   diffData = None

   def __init__(self,diffData):
      self.diffData = diffData

   def getMetaType(self):
     return 'EXIF'
 
   def getSections(self):
      return None

   def getColumnNames(self,section):
     return ['Operation','Old','New']

   def toColumns(self,section):
     d = {}
     for k,v in self.diffData.iteritems(): 
        old = v[1] if v[0].lower()=='change' or v[0].lower()=='delete' else ''
        new = v[2] if v[0].lower()=='change' else (v[1] if v[0].lower()=='add' else '')
        old = old.encode('ascii', 'xmlcharrefreplace')
        new = new.encode('ascii', 'xmlcharrefreplace')
        d[k] = {'Operation':v[0],'Old':old,'New':new}
     return d

class VideoMetaDiff:
   """
    Video Meta-data changes are represented by section. 
    A special section called Global represents meta-data for the entire video.
    Other sections are in the individual streams (e.g. video and audio) of frames.
    A table of columns is produced per section.  The columns are Id, Operation, Old and New.
    Operations are add, delete and change.
    For streams, each row is identified by a time and meta-data name. 
    When frames are added, the New column contains the number of frames added followed by the end time in seconds: 30:=434.4343434
    When frames are deleted, the Old column contains the number of frames removed followed by the end time in seconds: 30:=434.4343434
   """
   diffData = None

   def __init__(self,diffData):
      self.diffData = diffData

   def getMetaType(self):
     return 'FRAME'
 
   def getSections(self):
      return ['Global'] + self.diffData[1].keys()

   def getColumnNames(self,section):
     return ['Operation','Old','New']

   def toColumns(self,section):
     d = {}
     if section is None:
        section = 'Global'
     if section == 'Global':
        self._sectionChanges(d,self.diffData[0])
     else:
       itemTuple = self.diffData[1][section]
       if itemTuple[0] == 'add':
          d['add'] = {'Operation':'','Old':'','New':''}
       elif itemTuple[0] == 'delete':
          d['delete'] = {'Operation':'','Old':'','New':''}
       else:
          for changeTuple in itemTuple[1]:
            if changeTuple[0] == 'add':
               d[str(changeTuple[1])] = {'Operation':'add','Old':'','New':str(changeTuple[3]) + ':=>' + str(changeTuple[2]) }
            elif changeTuple[0] == 'delete':
               d[str(changeTuple[1])] = {'Operation':'delete','Old':str(changeTuple[3]) + ':=>' + str(changeTuple[2]),'New':''}
            else:
               self._sectionChanges(d,changeTuple[4],prefix=str(changeTuple[3]))
     return d

   def _sectionChanges(self,d,sectionData,prefix= ''):
     for k,v in sectionData.iteritems(): 
        dictKey = k if prefix == '' else prefix + ': ' + str(k)
        old = v[1] if v[0].lower()=='change' or v[0].lower()=='delete' else ''
        new = v[2] if v[0].lower()=='change' else (v[1] if v[0].lower()=='add' else '')
        old = old.encode('ascii', 'xmlcharrefreplace')
        new = new.encode('ascii', 'xmlcharrefreplace')
        d[dictKey] = {'Operation':v[0],'Old':old,'New':new}


class Modification:
   """
   Represents a single manipulation to a source node, resulting in the target node
   """
   operationName = None
   additionalInfo = ''
   # for backward compatibility and ease of access, input mask name is both arguments and 
   # an instance variable 
   inputMaskName=None
   #set of masks used for videos
   maskSet = None
   # Record the link in the composite.  Uses 'no' and 'yes' to mirror JSON read-ability
   recordMaskInComposite = 'no'
   # arguments used by the operation
   arguments = {}
   # represents the composite selection mask, if different from the link mask
   selectMaskName = None
   # instance of Software
   software = None
   #automated
   automated = 'no'
   #errors
   errors = []

   def __init__(self, operationName, additionalInfo, arguments={}, \
        recordMaskInComposite=None, \
        changeMaskName=None, \
        selectMaskName=None, \
        inputMaskName=None,
        software=None, \
        maskSet=None, \
        automated=None, \
        errors = []):
     self.additionalInfo  = additionalInfo
     self.maskSet = maskSet
     self.automated = automated if automated else 'no'
     self.errors = errors if errors else []
     self.setOperationName(operationName)
     self.setArguments(arguments)
     if inputMaskName is not None:
       self.setInputMaskName(inputMaskName)
     self.changeMaskName = changeMaskName
     self.selectMaskName = selectMaskName
     self.software = software
     if recordMaskInComposite is not None:
        self.recordMaskInComposite = recordMaskInComposite
 
   def setErrors(self, val):
      self.errors = val if val else []

   def setAutomated(self, val):
      self.automated = 'yes' if val == 'yes' else 'no'

   def setMaskSet(self,maskset):
      self.maskSet = maskset

   def getSoftwareName(self):
      return self.software.name if self.software is not None and self.software.name is not None else ''

   def getSoftwareVersion(self):
      return self.software.version if self.software is not None and self.software.version is not None else ''

   def setSoftware(self,software):
      self.software = software

   def usesInputMaskForSelectMask(self):
      return self.inputMaskName == self.selectMaskName

   def setArguments(self,args):
      self.arguments = {}
      for k,v in args.iteritems():
         self.arguments[k]= v
         if k == 'inputmaskname':
           self.setInputMaskName(v)

   def setSelectMaskName(self,selectMaskName):
     self.selectMaskName = selectMaskName

   def setInputMaskName(self,inputMaskName):
     self.inputMaskName = inputMaskName
     if 'inputmaskname' not in self.arguments or self.arguments['inputmaskname'] != inputMaskName:
        self.arguments['inputmaskname'] = inputMaskName

   def setAdditionalInfo(self,info):
     self.additionalInfo  =  info
  
   def setRecordMaskInComposite(self,recordMaskInComposite):
      self.recordMaskInComposite = recordMaskInComposite

   def setOperationName(self,name):
     self.operationName = name
     if name is None:
        return
     op = getOperation(self.operationName)
     self.category = op.category if op is not None else None
     self.recordMaskInComposite='yes' if op is not None and op.includeInMask else 'no'


class ImageProjectModel:
    """
       A ProjectModel manages a project.  A project is made up of a directed graph of Image nodes and links.
       Each link is associated with a manipulation between the source image to the target image.  
       A link contains a mask(black and white) image file describing the changes.
       A mask's X&Y dimensions match the source image.
       A link contains a description of the manipulation operation, software used to perfrom the manipulation,
       analytic results comparing source to target images, and an input mask path name.  The input mask path name
       describes a mask used by the manipulation software as a parameter describing the manipulation.
       Links may be 'read-only' indicating that they are created through an automated plugin.

       A ProjectModel can be reused to open new projects.   It is designed to represent a view model (MVC).
       A ProjectModel has two state paremeters, 'start' and 'end', containing the name of image nodes in the graph.
       When both set, a link is selected.  When 'start' is set and 'end' is None, only a single image node is selected.
       Several methods on the ProjectModel depend on the state of these parameters.  For example, adding a new link
       to a image node, chooses the source node referenced by 'end' if set, otherwise it chooses the node referenced by 'start'
    """
  
    G = None
    start = None
    end = None

    def __init__(self, projectFileName, importImage=False, notify=None):
      self._setup(projectFileName)
      self.notify = notify

    def getTypeName(self):
       return 'Image'

    def get_dir(self):
       return self.G.dir

    def addImagesFromDir(self,dir,baseImageFileName=None,xpos=100,ypos=30,suffixes=[],sortalg=lambda s: s.lower()):
       """
         Bulk add all images from a given directory into the project.
         Position the images in a grid, separated by 50 vertically with a maximum height of 520.
         Images are imported in lexicographic order, first importing JPG, then PNG and finally TIFF.
         If baseImageFileName, the name of an image node, is provided, then that node is selected
         upong completion of the operation.  Otherwise, the last not imported is selected"
       """
       initialYpos = ypos
       totalSet = []
       for suffix in suffixes:
         totalSet.extend( [filename for filename in os.listdir(dir) if filename.lower().endswith(suffix) and not filename.endswith('_mask' + suffix)])
       totalSet = sorted(totalSet,key= sortalg)
       for filename in totalSet:
           pathname = os.path.abspath(os.path.join(dir,filename))
           nname = self.G.add_node(pathname,xpos=xpos,ypos=ypos,nodetype='base')
           ypos+=50
           if ypos == 450:
              ypos=initialYpos
              xpos+=50
           if filename==baseImageFileName:
             self.start = nname
             self.end = None

    def addImage(self, pathname):
       nname = self.G.add_node(pathname,nodetype='base')
       self.start = nname
       self.end = None
       return nname

    def update_edge(self,mod):
        self.G.update_edge(self.start, self.end, \
            op=mod.operationName, \
            description=mod.additionalInfo, \
            arguments={k:v for k,v in mod.arguments.iteritems() if k != 'inputmaskname'}, \
            recordMaskInComposite=mod.recordMaskInComposite,  \
            editable='no' if (mod.software is not None and mod.software.internal) or mod.operationName == 'Donor' else 'yes', \
            softwareName=('' if mod.software is None else mod.software.name), \
            softwareVersion=('' if mod.software is None else mod.software.version), \
            inputmaskname=mod.inputMaskName, \
            selectmaskname=mod.selectMaskName)

    def compare(self, destination, arguments={}):
       """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
           Return both images, the mask and the analysis results (a dictionary)
       """
       im1 = self.getImage(self.start)
       im2 = self.getImage(destination)
       mask, analysis = tool_set.createMask(im1,im2, invert=False, arguments=arguments)
       return im1,im2,mask,analysis

    def getMetaDiff(self):
      """ Return the EXIF differences between nodes referenced by 'start' and 'end' 
      """
      e = self.G.get_edge(self.start, self.end)
      if e is None:
          return None
      return MetaDiff(e['exifdiff']) if 'exifdiff' in e and len(e['exifdiff']) > 0 else None

    def getTerminalAndBaseNodeTuples(self):
       """
         Return a tuple (lead node, base node) for each valid (non-donor) path through the graph
       """
       terminalNodes = [node for node in self.G.get_nodes() if len(self.G.successors(node)) == 0 and len(self.G.predecessors(node)) > 0]
       return [(node,self._findBaseNodes(node)) for node in terminalNodes]

    def _addAnalysis(self,startIm,destIm,op,analysis,mask,arguments={}):
       import importlib
       opData = getOperation(op)
       if opData is None:
          return
       for analysisOp in opData.analysisOperations:
         mod_name, func_name = analysisOp.rsplit('.',1)
         mod = importlib.import_module(mod_name)
         func = getattr(mod, func_name)
         try:
           func(analysis,startIm,destIm,mask=tool_set.invertMask(mask),arguments=arguments)          
         except:
	   print 'Failed analysis'

    def _compareImages(self,start,destination, op, invert=False, arguments={},skipDonorAnalysis=False):
       startIm,startFileName = self.getImageAndName(start)
       destIm,destFileName = self.getImageAndName(destination)
       errors = []
       maskname=start + '_' + destination + '_mask'+'.png'
       if op == 'Donor':
          predecessors = self.G.predecessors(destination)
          mask = None
          if not skipDonorAnalysis:
            errors = ["Could not compute SIFT Matrix"]
            for pred in predecessors:
              edge = self.G.get_edge(pred,destination) 
              if edge['op']!='Donor':
                 mask,analysis = tool_set.interpolateMask(self.G.get_edge_image(pred,destination,'maskname')[0],startIm,destIm,arguments=arguments,invert=invert)
                 if mask is not None:
                   errors = []
                   mask = Image.fromarray(mask)
                   break
          if mask is None:
            mask = tool_set.convertToMask(self.G.get_image(self.start)[0])
            analysis = {}
       else:
          mask,analysis = tool_set.createMask(startIm,destIm, invert=invert,arguments=arguments)
          exifDiff = exif.compareexif(startFileName,destFileName)
          analysis = analysis if analysis is not None else {}
          analysis['exifdiff'] = exifDiff
          self._addAnalysis(startIm,destIm,op,analysis,mask,arguments=arguments)
       return maskname,mask, analysis,errors

    def getNodeNames(self):
      return self.G.get_nodes()
      
    def isEditableEdge(self,start,end):
      e = self.G.get_edge(start,end)
      return 'editable' not in e or e['editable'] == 'yes'

    def findChild(self,parent, child):
       for suc in self.G.successors(parent):
          if suc == child or self.findChild(suc,child):
             return True
       return False
       
    def connect(self,destination,mod=Modification('Donor',''), invert=False, sendNotifications=True,skipDonorAnalysis=False):
       """ Given a image node name, connect the new node to the end of the currently selected node.
            Create the mask, inverting the mask if requested.
            Send a notification to the register caller if requested.
            Return an error message on failure, otherwise return None
       """
       if self.start is None:
          return "Node node selected",False
       if self.findChild(destination,self.start):
          return "Cannot connect to ancestor node",False
       return self._connectNextImage(destination,mod,invert=invert,sendNotifications=sendNotifications,skipDonorAnalysis=skipDonorAnalysis)

    def getComposite(self):
      """
       Get the composite image for the selected node.
       If the composite does not exist AND the node is a leaf node, then create the composite
       Return None if the node is not a leaf node
      """
      nodeName = self.start if self.end is None else self.end
      mask,filename = self.G.get_composite_mask(nodeName)
      if mask is None:
          # verify the node is a leaf node
          endPointTuples = self.getTerminalAndBaseNodeTuples()
          if nodeName in [x[0] for x in endPointTuples]:
            self.constructComposites()
          mask,filename = self.G.get_composite_mask(nodeName)
      return mask
         
    def _constructComposites(self,nodeAndMasks,stopAtNode=None):
      """
        Walks up down the tree from base nodes, assemblying composite masks"
      """
      result = []
      for nodeAndMask in nodeAndMasks:
         if nodeAndMask[1] == stopAtNode:
            return [nodeAndMask]
         for suc in self.G.successors(nodeAndMask[1]):
            edge = self.G.get_edge(nodeAndMask[1],suc)
            if edge['op'] == 'Donor':
               continue
            compositeMask = self._extendComposite(nodeAndMask[2],edge,nodeAndMask[1],suc)
            result.append((nodeAndMask[0],suc,compositeMask))
      if len(result) == 0:
         return nodeAndMasks
      return self._constructComposites(result,stopAtNode=stopAtNode)

    def constructComposite(self):
       """
        Construct the composite mask for the selected node.
        Does not save the composite in the node.
        Returns the composite mask if successful, otherwise None
       """
       selectedNode = self.end if self.end is not None else self.start
       baseNodes = self._findBaseNodes(selectedNode)
       if len(baseNodes) > 0:
          baseNode = baseNodes[0]
          composites = self._constructComposites([(baseNode,baseNode,None)],stopAtNode=selectedNode)
          for composite in composites:
             if composite[1] == selectedNode and composite[2] is not None:
                return Image.fromarray(composite[2])
       return None

    def constructComposites(self):
      """
        Remove all prior constructed composites.
        Find all valid base node, leaf node tuples.
        Construct the composite make along the paths from base to lead node.
        Save the composite in the associated leaf nodes.
      """
      composites = []
      endPointTuples = self.getTerminalAndBaseNodeTuples()
      for endPointTuple in endPointTuples:
         for baseNode in endPointTuple[1]:
             composites.extend(self._constructComposites([(baseNode,baseNode,None)]))
      for composite in composites:
         self.G.addCompositeToNode((composite[0],composite[1], Image.fromarray(composite[2])))
      return composites

    def addNextImage(self, pathname, invert=False, mod=Modification('',''), sendNotifications=True, position=(50,50),skipRules=False):
       """ Given a image file name and  PIL Image, add the image to the project, copying into the project directory if necessary.
            Connect the new image node to the end of the currently selected edge.  A node is selected, not an edge, then connect
            to the currently selected node.  Create the mask, inverting the mask if requested.
            Send a notification to the register caller if requested.
            Return an error message on failure, otherwise return None
       """
       if (self.end is not None):
          self.start = self.end
       destination = self.G.add_node(pathname, seriesname=self.getSeriesName(),xpos=position[0],ypos=position[1],nodetype='base')
       msg,status = self._connectNextImage(destination,mod,invert=invert,sendNotifications=sendNotifications,skipRules=skipRules)
       return msg,status

       
    def _connectNextImage(self,destination,mod,invert=False,sendNotifications=True,skipRules=False,skipDonorAnalysis=False):
       try:
         maskname, mask, analysis,errors = self._compareImages(self.start,destination,mod.operationName,invert=invert,arguments=mod.arguments,skipDonorAnalysis=skipDonorAnalysis)
         self.end = destination
         if errors:
           mod.errors = errors
         im = self.__addEdge(self.start,self.end,mask,maskname,mod,analysis)
         edgeErrors = graph_rules.run_rules(mod.operationName,self.G,self.start,destination)
         msgFromRules = os.linesep.join(edgeErrors) if len(edgeErrors) > 0 and not skipRules else ''
         if (self.notify is not None and sendNotifications):
            self.notify((self.start,destination),'connect')
         msgFromErrors = "Comparison errors occured" if errors and len(errors)>0 else ''
         msg = os.linesep.join([msgFromRules,msgFromErrors]).strip()
         msg = msg if len(msg) > 0 else None
         self.labelNodes(self.start)
         self.labelNodes(destination)
         return msg, True
       except ValueError as e:
         return 'Exception (' + str(e) + ')' ,False

    def __addEdge(self,start,end,mask,maskname,mod,additionalParameters):
       if len(mod.arguments)>0:
          additionalParameters['arguments'] = {k:v for k,v in mod.arguments.iteritems() if k != 'inputmaskname'}
       im= self.G.add_edge(start,end,mask=mask,maskname=maskname, \
            op=mod.operationName,description=mod.additionalInfo, \
            recordMaskInComposite=mod.recordMaskInComposite, \
            editable='no' if (mod.software is not None and mod.software.internal) or mod.operationName == 'Donor' else 'yes', \
            softwareName=('' if mod.software is None else mod.software.name), \
            softwareVersion=('' if mod.software is None else mod.software.version), \
            inputmaskname=mod.inputMaskName, \
            selectmaskname=mod.selectMaskName, \
            automated=mod.automated, \
            errors=mod.errors, \
            **additionalParameters)

    def getSeriesName(self):
       """ A Series is the prefix of the first image node """
       if self.start is None:
          return None
       startNode = self.G.get_node(self.start)
       prefix = None
       if (startNode.has_key('seriesname')):
         prefix = startNode['seriesname']
       if (self.end is not None):
          endNode = self.G.get_node(self.end)
          if (endNode.has_key('seriesname')):
            prefix = startNode['seriesname']
       return prefix

    def getName(self):
     return self.G.get_name()

    def operationImageName(self):
      return self.end if self.end is not None else self.start 

    def startImageName(self):
      return self.G.get_node(self.start)['file'] if self.start is not None else ""
    
    def nextImageName(self):
      return self.G.get_node(self.end)['file'] if self.end is not None else ""

    def nextId(self):
      return self.end

    def undo(self):
       """ Undo the last graph edit """
       self.start = None
       self.end = None
       self.G.undo()

    def select(self,edge):
      self.start= edge[0]
      self.end = edge[1]

    def startNew(self,imgpathname,suffixes=[],organization=None):
       """ Inititalize the ProjectModel with a new project given the pathname to a base image file in a project directory """
       projectFile = imgpathname[0:imgpathname.rfind(".")] + ".json"
       self.G = self._openProject(projectFile)
       if organization is not None:
         self.G.setDataItem('organization',organization)
       self.start = None
       self.end = None
       self.addImagesFromDir(os.path.split(imgpathname)[0],baseImageFileName=os.path.split(imgpathname)[1],suffixes=suffixes, \
                           sortalg=lambda f: os.stat(os.path.join(os.path.split(imgpathname)[0], f)).st_mtime)

    def load(self,pathname):
       """ Load the ProjectModel with a new project/graph given the pathname to a JSON file in a project directory """ 
       self._setup(pathname)

    def _openProject(self,projectFileName):
      return ImageGraph(projectFileName)

    def _setup(self,projectFileName):
       self.G  = self._openProject(projectFileName)
       self.start = None
       self.end = None
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

    def getDescriptionForPredecessor(self,node):
       for pred in self.G.predecessors(node):
          edge = self.G.get_edge(pred,node)
          if edge['op'] != 'Donor':
             return self._getModificationForEdge(edge)
       return None

    def getDescription(self):
       if self.start is None or self.end is None:
          return None
       edge = self.G.get_edge(self.start, self.end)
       if edge is not None:
         return self._getModificationForEdge(edge)
       return None

    def getImage(self,name):
       if name is None or name=='':
           return Image.fromarray(np.zeros((250,250,4)).astype('uint8'))
       return self.G.get_image(name)[0]

    def getImageAndName(self,name):
       if name is None or name=='':
           return Image.fromarray(np.zeros((250,250,4)).astype('uint8'))
       return self.G.get_image(name)

    def getStartImageFile(self):
       return os.path.join(self.G.dir, self.G.get_node(self.start)['file'])

    def getNextImageFile(self):
       return os.path.join(self.G.dir, self.G.get_node(self.end)['file'])

    def startImage(self):
       return self.getImage(self.start)

    def nextImage(self):
       if self.end is None:
         dim = (250,250) if self.start is None else self.getImage(self.start).size
         return Image.fromarray(np.zeros((dim[1],dim[0])).astype('uint8'))
       return self.getImage(self.end)

    def getSelectMask(self):
       """
       A selectMask is a mask the is used in composite mask production, overriding the default link mask
       """
       if self.end is None:
          return None,None
       mask = self.G.get_edge_image(self.start,self.end,'maskname')
       selectMask = self.G.get_edge_image(self.start,self.end,'selectmaskname')
       if selectMask[0] != None:
          return selectMask
       return mask

    def maskImage(self):
       if self.end is None:
           dim = (250,250) if self.start is None else self.getImage(self.start).size
           return Image.fromarray(np.zeros((dim[1],dim[0])).astype('uint8'))
       return self.G.get_edge_image(self.start,self.end,'maskname')[0]

    def maskStats(self):
       if self.end is None:
          return ''
       edge = self.G.get_edge(self.start,self.end)
       if edge is None:
         return ''
       stat_names = ['ssim','psnr','username','shape change','masks count']
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

    def selectEdge(self, start, end):
      self.start = start
      self.end = end

    def remove(self):
       """ Remove the selected node or edge """
       if (self.start is not None and self.end is not None):
           self.G.remove_edge(self.start, self.end)
           self.labelNodes(self.start)
           self.labelNodes(self.end)
           self.end = None
       else:
         name = self.start if self.end is None else self.end
         p = self.G.predecessors(self.start) if self.end is None else [self.start]
         self.G.remove(name, None)
         self.start = p[0] if len(p) > 0  else None
         self.end = None
         for node in p:
           self.labelNodes(node)

    def getProjectData(self, item):
        return self.G.getDataItem(item)

    def setProjectData(self,item, value):
        self.G.setDataItem(item,value)

    def getVersion(self):
      """ Return the graph/software versio n"""
      return self.G.getVersion()

    def getGraph(self):
      return self.G

    def validate(self):
       """ Return the list of errors from all validation rules on the graph. """
           
       total_errors = []

       if len(self.G.get_nodes()) == 0:
          return total_errors

       for node in self.G.get_nodes():
         if not self.G.has_neighbors(node):
             total_errors.append((str(node),str(node),str(node) + ' is not connected to other nodes'))
         predecessors = self.G.predecessors(node)
         if len(predecessors) == 1 and self.G.get_edge(predecessors[0],node)['op'] == 'Donor':
             total_errors.append((str(predecessors[0]), str(node), str(node) +
                                ' donor links must coincide with another link to the same destintion node'))

       nodeSet = set(self.G.get_nodes())
       for found in self.G.findRelationsToNode(nodeSet.pop()):
          if found in nodeSet:
             nodeSet.remove(found)

       for node in nodeSet:
          total_errors.append((str(node),str(node),str(node) + ' is part of an unconnected subgraph'))

       total_errors.extend(self.G.file_check())

       cycleNode= self.G.getCycleNode()
       if cycleNode is not None:
         total_errors.append((str(node),str(node),"Graph has a cycle"))

       for frm,to in self.G.get_edges():
          edge = self.G.get_edge(frm,to)
          op = edge['op'] 
          errors = graph_rules.run_rules(op,self.G,frm,to)
          if len(errors) > 0:
              total_errors.extend( [(str(frm),str(to),str(frm) + ' => ' + str(to) + ': ' + err) for err in errors])
       return total_errors

    def __assignLabel(self,node, label):
       prior = self.G.get_node(node)['nodetype'] if 'nodetype' in self.G.get_node(node) else None
       if prior != label:
          self.G.update_node(node,nodetype=label)
          if self.notify is not None:
            self.notify(node,'label')


    def labelNodes(self,destination):
       baseNodes = []
       candidateBaseDonorNodes = []
       for terminal in self._findTerminalNodes(destination):
         baseNodes.extend( self._findBaseNodes(terminal))
         candidateBaseDonorNodes.extend(self._findBaseNodes(terminal,excludeDonor=False))
       baseDonorNodes = [node for node in candidateBaseDonorNodes if node not in baseNodes]
       for node in baseDonorNodes:
          self.__assignLabel(node,'donor')
       for node in baseNodes:
          self.__assignLabel(node,'base')
       if len(self.G.successors(destination)) == 0:
          if len(self.G.predecessors(destination)) == 0:
            self.__assignLabel(destination,'base')
          else:
            self.__assignLabel(destination,'final')
       elif len(self.G.predecessors(destination)) > 0: 
          self.__assignLabel(destination,'interim')
       elif 'nodetype' not in self.G.get_node(destination):
          self.__assignLabel(destination,'base')

    def _findTerminalNodes(self,node):
       succs = self.G.successors(node)
       res = [node] if len(succs) == 0 else []
       for succ in succs:
          res.extend(self._findTerminalNodes(succ))
       return res

    def _findTerminalNodes(self,node):
       return self._findTerminalNodesWithCycleDetection(node,visitSet=[])

    def _findTerminalNodesWithCycleDetection(self,node,visitSet=[]):
       succs = self.G.successors(node)
       res = [node] if len(succs) == 0 else []
       for succ in succs:
          if succ in visitSet:
             continue
          visitSet.append(succ)
          res.extend(self._findTerminalNodesWithCycleDetection(succ,visitSet=visitSet))
       return res

    def _findBaseNodes(self,node,excludeDonor = True):
       return self._findBaseNodesWithCycleDetection(node,excludeDonor=excludeDonor,visitSet=[])

    def _findBaseNodesWithCycleDetection(self,node,excludeDonor = True,visitSet=[]):
       preds = self.G.predecessors(node)
       res = [node] if len(preds) == 0 else []
       for pred in preds:
          if pred in visitSet:
             continue
          isNotDonor = (self.G.get_edge(pred,node)['op'] != 'Donor' or not excludeDonor)
          if isNotDonor:
            visitSet.append(pred)
          res.extend(self._findBaseNodesWithCycleDetection(pred,excludeDonor=excludeDonor,visitSet=visitSet) if isNotDonor else [])
       return res

    def isDonorEdge(self,start,end):
        edge = self.G.get_edge(start,end)            
        if edge is not None:
           return edge['op'] == 'Donor'
        return False

    def getTerminalToBasePairs(self, suffix='.jpg'):
        """
         find all pairs of leaf nodes to matching base nodes
        """
        endPointTuples = self.getTerminalAndBaseNodeTuples()
        pairs = []
        for endPointTuple in endPointTuples:
           matchBaseNodes = [baseNode for baseNode in endPointTuple[1] if suffix is None or self.G.get_pathname(baseNode).lower().endswith(suffix)] 
           if len(matchBaseNodes) > 0:
              # if more than one base node, use the one that matches the name of the project
              projectNodeIndex = matchBaseNodes.index(self.G.get_name()) if self.G.get_name() in matchBaseNodes else 0
              baseNode = matchBaseNodes[projectNodeIndex]
              startNode = endPointTuple[0]
              # perfect match
              #if baseNode == self.G.get_name():
              #    return [(startNode,baseNode)]
              pairs.append((startNode,baseNode))
        return pairs
                  
    def imageFromPlugin(self,filter,im, filename, **kwargs):
      """
        Create a new image from a plugin filter.  
        This method is given the plugin name, PIL Image, the full pathname of the image and any additional parameters
        required by the plugin (name/value pairs).
        The name of the resulting image contains the prefix of the input image file name plus an additional numeric index.
        If requested by the plugin (return True), the Exif is copied from the input image to the resulting image.
        The method resolves the donor parameter's name to the donor's image file name.
        If a donor is used, the method creates a Donor link from the donor image to the resulting image node.
        If an input mask file is used, the input mask file is moved into the project directory.
        Prior to calling the plugin, the output file is created and populated with the contents of the input file for convenience.
        The filter plugin must update or overwrite the contents.
        The method returns tuple with an error message and a list of pairs (links) added.  The error message may be none if no error occurred.
      """
      op = plugins.getOperation(filter)
      suffixPos = filename.rfind('.')
      suffix = filename[suffixPos:].lower()
      preferred = plugins.getPreferredSuffix(filter)
      if preferred is not None:
          suffix = preferred
      target = os.path.join(tempfile.gettempdir(),self.G.new_name(os.path.split(filename)[1],suffix=suffix))
      shutil.copy2(filename, target)
      msg = None
      try:
         copyExif = plugins.callPlugin(filter,im,filename,target,**self._resolvePluginValues(kwargs))
      except Exception as e:
         msg = str(e)
         copyExif = False
      if msg is not None:
          return self._pluginError(filter,msg),[]
      if copyExif:
        msg = exif.copyexif(filename,target)
      description = Modification(op[0],filter + ':' + op[2])
      sendNotifications = kwargs['sendNotifications'] if 'sendNotifications' in kwargs else True
      skipRules = kwargs['skipRules'] if 'skipRules' in kwargs else False
      software = Software(op[3],op[4],internal=True)
      description.setArguments({k:v for k,v in kwargs.iteritems() if k != 'donor' and k != 'sendNotifications' and k != 'skipRules'})
      description.setSoftware(software)
      description.setAutomated('yes')

      msg2,status = self.addNextImage(target,mod=description,sendNotifications=sendNotifications,skipRules=skipRules,position=self._getCurrentPosition((75, 60 if 'donor' in kwargs else 0)))
      pairs = []
      if msg2 is not None:
          if msg is None:
             msg = msg2
          else:
             msg = msg + "\n" + msg2
      if status:
          pairs.append((self.start, self.end))
          if 'donor' in kwargs:
             _end = self.end
             _start = self.start
             self.selectImage(kwargs['donor'])
             self.connect(_end,skipDonorAnalysis=True)
             pairs.append((kwargs['donor'],_end))
             self.select((_start, _end))
      os.remove(target)
      return self._pluginError(filter,msg),pairs

    def _resolvePluginValues(self,args):
      result = {}
      for k,v in args.iteritems():
       if k == 'donor':
          result[k] = self.getImageAndName(v)
       else:
          result[k] = v
      return result

    def _pluginError(self,filter, msg):
         if msg is not None and len(msg) > 0:
            return 'Plugin ' + filter + ' Error:\n' + msg
         return None

    def scanNextImageUnConnectedImage(self):
       """Scan for an image node with the same prefix as the currently select image node. 
          Scan in lexicographic order.
          Exlude images that have neighbors.
          Return None if a image nodee is not found.
       """
       selectionSet = [node for node in self.G.get_nodes() if not self.G.has_neighbors(node) and node != self.start]
       selectionSet.sort()
       if (len(selectionSet) > 0):
           seriesname = self.getSeriesName()
           seriesname = seriesname if seriesname is not None else self.start
           matchNameSet = [name for name in selectionSet if name.startswith(self.start)]
           selectionSet = matchNameSet if len(matchNameSet) > 0 else selectionSet
       return selectionSet[0] if len(selectionSet) > 0 else None

    def scanNextImage(self):
      """
         Scan for a file with the same prefix as the currently select image node. 
         Scan in lexicographic order.
         Exlude image files with names ending in _mask or image files that are already imported.
         Return None if a file is not found.
      """

      if self.start is None:
         return None,None

      suffix = self.start
      seriesName = self.getSeriesName()
      if seriesName is not None:
         prefix = seriesName

      def filterFunction (file):
         return not self.G.has_node(os.path.split(file[0:file.rfind('.')])[1]) and not(file.rfind('_mask')>0)

      def findFiles(dir, preFix, filterFunction):
         set= [os.path.abspath(os.path.join(dir,filename)) for filename in os.listdir(dir) if (filename.startswith(preFix)) and filterFunction(os.path.abspath(os.path.join(dir,filename)))]
         set.sort()
         return set
      
      nfile = None
      for file in findFiles(self.G.dir,prefix, filterFunction):
         nfile = file
         break
      return self.G.openImage(nfile) if nfile is not None else None,nfile

    def openImage(self,nfile):
      im = None
      if nfile is not None and nfile != '':
          im = self.G.openImage(nfile)
      return nfile,im

    def export(self, location):
      path,errors = self.G.create_archive(location)
      return errors

    def exporttos3(self, location):
      import boto3
      path,errors = self.G.create_archive(tempfile.gettempdir())
      if len(errors) == 0:
        s3= boto3.client('s3','us-east-1')
        BUCKET= location.split('/')[0].strip()
        DIR= location[location.find('/')+1:].strip()
        print 'Upload to s3://' + BUCKET + '/' + DIR + '/' + os.path.split(path)[1] 
        s3.upload_file(path, BUCKET, DIR + '/' + os.path.split(path)[1])
        os.remove(path)
      return errors

    def export_path(self, location):
      if self.end is None and self.start is not None:
         self.G.create_path_archive(location,self.start)
      elif self.end is not None:
         self.G.create_path_archive(location,self.end)

    def _getCurrentPosition(self,augment):
      if self.start is None:
          return (50,50)
      startNode = self.G.get_node(self.start)
      return ((startNode['xpos'] if startNode.has_key('xpos') else 50)+augment[0],(startNode['ypos'] if startNode.has_key('ypos') else 50)+augment[1])

    def _extendComposite(self,compositeMask,edge,source,target):
      if compositeMask is None:
          imarray = np.asarray(self.G.get_image(source)[0])
          compositeMask = np.ones((imarray.shape[0],imarray.shape[1]))*255
      # merge masks first, the mask is the same size as the input image
      # consider a cropped image.  The mask of the crop will have the change high-lighted in the border
      # consider a rotate, the mask is either ignored or has NO change unless interpolation is used.
      edgeMask = self.G.get_edge_image(source,target,'maskname')[0]
      selectMask = self.G.get_edge_image(source,target,'selectmaskname')[0]
      edgeMask = np.asarray(selectMask if selectMask is not None else edgeMask)
      if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'yes':
        compositeMask = tool_set.mergeMask(compositeMask,edgeMask)
      # change the mask to reflect the output image
      # considering the crop again, the high-lighted change is not dropped
      # considering a rotation, the mask is now rotated
      sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0,0)
      location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0,0)
      rotation = float(edge['rotation'] if 'rotation' in edge and edge['rotation'] is not None else 0.0)
      args = edge['arguments'] if 'arguments' in edge else {}
      rotation = float(args['rotation'] if 'rotation' in args and args['rotation'] is not None else rotation)
      interpolation = args['interpolation'] if 'interpolation' in args and len(args['interpolation']) > 0 else 'nearest'
      tm= edge['transform matrix'] if 'transform matrix' in edge  else None
      tm = tm if 'apply transform' not in edge or edge['apply transform'] == 'yes' else None
      compositeMask = tool_set.alterMask(compositeMask,edgeMask,rotation=rotation,\
                  sizeChange=sizeChange,interpolation=interpolation,location=location,transformMatrix=tm)
      return compositeMask

    def _getModificationForEdge(self,edge):
      return Modification(edge['op'], \
          edge['description'], \
          arguments = edge['arguments'] if 'arguments' in edge else {}, \
          inputMaskName=edge['inputmaskname'] if 'inputmaskname' in edge and edge['inputmaskname'] and len(edge['inputmaskname']) > 0 else None, \
          selectMaskName = edge['selectmaskname'] if 'selectmaskname' in edge and edge['selectmaskname'] and len(edge['selectmaskname'])>0 else None, \
          changeMaskName=  edge['maskname'] if 'maskname' in edge else None, \
          software=Software(edge['softwareName'] if 'softwareName' in edge else None, \
                            edge['softwareVersion'] if 'softwareVersion' in edge else None, \
                            'editable' in edge and edge['editable'] == 'no'), \
          recordMaskInComposite = edge['recordMaskInComposite'] if 'recordMaskInComposite' in edge else 'no', \
          automated = edge['automated'] if 'automated' in edge else 'no', \
          errors = edge['errors'] if 'errors' in edge else [])

class VideoProjectModel(ImageProjectModel):

    def __init__(self, projectFileName, importImage=False, notify=None):
       ImageProjectModel.__init__(self,projectFileName,notify=notify)

    def _openProject(self,projectFileName):
       return VideoGraph(projectFileName)

    def getTerminalToBasePairs(self, suffix='.mp4'):
       return ImageProjectModel.getTerminalToBasePairs(self,suffix=suffix)

    def getMetaDiff(self):
      """ Return the Frame meta-data differences between nodes referenced by 'start' and 'end'                                                                                            
      """
      e = self.G.get_edge(self.start, self.end)
      if e is None:
          return None
      return VideoMetaDiff(e['metadatadiff']) if 'metadatadiff' in e else None

    def compare(self, destination,arguments={}):
       """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
           Return both images, the mask set and the meta-data diff results
       """
       startIm,startFileName = self.getImageAndName(self.start)
       destIm,destFileName = self.getImageAndName(destination)
       maskname, mask, analysis,errors = self._compareImages(self.start,destination,'noOp')
       analysis['metadatadiff'] = VideoMetaDiff(analysis['metadatadiff'])
       analysis['videomasks'] = VideoMaskSetInfo(analysis['videomasks'])
       analysis['errors'] = VideoMaskSetInfo(analysis['errors'])
       return  startIm, destIm, mask,analysis

    def _compareImages(self,start,destination,op, invert=False,arguments={},skipDonorAnalysis=False):
       if op == 'Donor':
          return self._constructDonorMask(start,destination,arguments=arguments)
       startIm,startFileName = self.getImageAndName(start)
       destIm,destFileName = self.getImageAndName(destination)
       mask,analysis = Image.new("RGB", (250, 250), "black"),{}
       maskname=start + '_' + destination + '_mask'+'.png'
       maskSet,errors = video_tools.formMaskDiff(startFileName, destFileName, \
          startSegment = arguments['Start Time'] if 'Start Time' in arguments else None, \
          endSegment = arguments['End Time'] if 'End Time' in arguments else None, \
          applyConstraintsToOutput = op != 'SelectCutFrames')
# for now, just save the first mask
       if len(maskSet) > 0:
          mask = Image.fromarray(maskSet[0]['mask'])
          for item in maskSet:
             item.pop('mask')
       analysis['masks count']=len(maskSet)
       analysis['videomasks'] = maskSet
       metaDataDiff = video_tools.formMetaDataDiff(startFileName,destFileName)
       analysis = analysis if analysis is not None else {}
       analysis['metadatadiff'] = metaDataDiff
       self._addAnalysis(startIm,destIm,op,analysis,mask,arguments=arguments)
       return maskname,mask, analysis,errors

    def getTypeName(self):
       return 'Video'

    def _constructDonorMask(self,start,destination,invert=False,arguments=None):
       """
         Used for Donor video or images, the mask recording a 'donation' is the inversion of the difference
         of the Donor image and its parent, it exists.
         Otherwise, the donor image mask is the donor image (minus alpha channels):
       """
       
       startFileName = startNode['file']
       suffix = startFileName[startFileName.rfind('.'):]
       predecessors = self.G.predecessors(destination)
       analysis = {}
       for pred in predecessors:
          edge = self.G.get_edge(pred,destination)
          if edge['op']!='Donor':
             if 'masks count' in edge:
                analysis['masks count'] = edge['masks count']
             analysis['videomasks'] = video_tools.invertVideoMasks(self.G.dir,edge['videomasks'],self.start,destination)
             return maskname,tool_set.invertMask(self.G.get_edge_image(pred,self.start,'maskname')[0]),analysis,errors
       return maskname,tool_set.convertToMask(self.G.get_image(self.start)[0]),analysis,errors
    
    def _getModificationForEdge(self,edge):
       mod = ImageProjectModel._getModificationForEdge(self,edge)
       if 'videomasks' in edge and len(edge['videomasks'])> 0:
          mod.setMaskSet( VideoMaskSetInfo(edge['videomasks']))
       return mod

class VideoMaskSetInfo:
    """
    Set of change masks video clips
    """
    columnNames = ['Start','End','Frames','File']
    columnValues = {}

    def __init__(self,maskset):
      self.columnValues = {}
      for i in range(len(maskset)):
        self.columnValues['{:=02d}'.format(i)] = self._convert(maskset[i])
      
    def _convert(self,item):
       return {'Start':item['starttime'],'End':item['endtime'],'Frames':item['frames'],'File':item['videosegment']}

