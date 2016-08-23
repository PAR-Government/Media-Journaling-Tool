from PIL import Image, ImageTk
import networkx as nx
from networkx.readwrite import json_graph
from copy import copy
import json
import os
import shutil
import cv2
import getpass
from datetime import datetime
from software_loader import Software, SoftwareLoader, getOS
import tarfile
from tool_set import *

igversion='0.1'

def getPathValues(d,path):
      """
      Given a nest structure, 
      return all the values reference by the given path.
      Always returns a list.
      If the value is not found, the list is empty
      """
      if type(d) is list:
         result = []
         for item in d:
           result.extend(getPathValues(item,path))
         return result
      pos = path.find('.')
      if pos < 0:
         return [d[path]] if path in d and d[path] else []
      else:
         nextpath = path[0:pos]
         return getPathValues(d[nextpath],path[pos+1:]) if nextpath in d else []

def getPathPartAndValue(path,data):
    if path in data:
        return path,data[path]
    pos = path.rfind('.')
    if pos <0:
       return None,None
    return getPathPartAndValue(path[0:pos],data)

def get_pre_name(file):
  pos = file.rfind('.')
  return file[0:pos] if (pos > 0) else file

def get_suffix(file):
  pos = file.rfind('.')
  return file[pos:] if (pos > 0) else '.json'

def queue_nodes(g,nodes,node,func):
  for s in g.successors(node):
    func(node,s,g.edge[node][s])
    if len(g.predecessors(s)) > 1:
        continue
    queue_nodes(g,nodes,s,func)
    nodes.append(s)
  return nodes

def remove_edges(g,nodes,node,func):
  for s in g.successors(node):
    func(node,s,g.edge[node][s])
  return nodes

class ImageGraph:
  G = nx.DiGraph(name="Empty")
  U = []
  idc = 0
  dir = os.path.abspath('.')
  filesToRemove = set()
  # Will likely change this to be externally managed, except 'ownership'
  # ownership indicates that ownership of the image must be checked prior to deletion,
  # otherwise the image graph is assumed to be the owner
  # ownership occurs if the image file is copied into the project directory
  # These paths are all the paths associated with image or video files for a link (edge).
  edgeFilePaths = { 'inputmaskname':'inputmaskownership', \
                    'arguments.XMP File Name':'xmpfileownership', \
                    'maskname':None, \
                    'compositemaskname': None, \
                    'selectmaskname':'selectmaskownership', \
                    'videomasks.videosegment':None}

  def getUIGraph(self):
    return self.G

  def get_name(self):
    return self.G.name

  def __init__(self, pathname,projecttype='image'):
    fname = os.path.split(pathname)[1]
    name = get_pre_name(fname)
    self.dir = os.path.abspath(os.path.split(pathname)[0])
    self.G = nx.DiGraph(name=name)
    if (os.path.exists(pathname)):
      self.load(pathname)
    else:
      self.G.graph['username']=get_username()
      self.G.graph['projecttype']=projecttype


  def openImage(self,fileName,mask=False):
    return openImage(fileName)

  def get_nodes(self):
    return self.G.nodes()

  def edges_iter(self, node):
    return self.G.edges_iter(node)

  def get_pathname(self, name):
     return os.path.join(self.dir, self.G.node[name]['file'])

  def get_edges(self):
    return self.G.edges()

  def new_name(self, fname,suffix=None):
    if suffix is None:
     suffix = get_suffix(fname)
    nname = get_pre_name(fname)
    while (self.G.has_node(nname)):
      posUS = nname.rfind('_')
      if posUS > 0 and nname[posUS+1:].isdigit():
         nname = '{}_{:=02d}'.format(nname[:posUS], self.nextId())
      else:
         nname = '{}_{:=02d}'.format(nname, self.nextId())
      fname = nname + suffix
    return fname

  def _saveImage(self,pathname,image):
    image.save(newpathname,exif=image.info['exif'])

  def add_node(self,pathname, seriesname=None, image=None, **kwargs):
    fname = os.path.split(pathname)[1]
    origname = nname = get_pre_name(fname)
    suffix = get_suffix(fname)
    while (self.G.has_node(nname)):
      nname = '{}_{:=02d}'.format(nname, self.nextId())
      fname = nname + suffix
    newpathname = os.path.join(self.dir,fname)
    includePathInUndo = (newpathname in self.filesToRemove)
    if (not os.path.exists(newpathname)):
      includePathInUndo = True
      if (os.path.exists(pathname)):
        shutil.copy2(pathname, newpathname)
      elif image is not None:
        self._saveImage(newpathname,image)
    self.G.add_node(nname, seriesname=(origname if seriesname is None else seriesname), file=fname, ownership=('yes' if includePathInUndo else 'no'), ctime=datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'), **kwargs)
    self.U = []
    self.U.append(dict(name=nname, action='addNode', **self.G.node[nname]))
    # adding back a file that was targeted for removal
    if newpathname in self.filesToRemove:
      self.filesToRemove.remove(newpathname)
    return nname
    
  def undo(self):
    for d in list(self.U):
      action = d.pop('action')
      if action == 'removeNode':
         k = os.path.join(self.dir,d['file'])
         if k in self.filesToRemove:
           self.filesToRemove.remove(k)
         name = d.pop('name')
         self.G.add_node(name,**d)
      elif action == 'removeEdge':
         for path,ownership in self.edgeFilePaths.iteritems():
           for value in getPathValues(d,path):
              filePath = os.path.join(self.dir,value)
              if filePath in self.filesToRemove:
                 self.filesToRemove.remove(filePath)
         start = d.pop('start')
         end = d.pop('end')
         self.G.add_edge(start,end,**d)
      elif action == 'addNode':
         if (d['ownership'] == 'yes'):
             os.remove(os.path.join(self.dir,d['file']))
         self.G.remove_node(d['name'])
      elif action == 'addEdge':
         self.remove_edge(d['start'],d['end'])
    self.U = []

  def removeCompositeFromNode(self,nodeName):
    """
      Remove a composite image associated with a node
    """
    if self.G.has_node(nodeName):
        fname = nodeName + '_composite_mask.png'
        if 'compositemaskname' in self.G.node[nodeName]:
          self.G.node[nodeName]['compositemaskname']=''
          self.G.node[nodeName]['compositebase']=''
          os.remove(os.path.abspath(os.path.join(self.dir,fname)))

  def addCompositeToNode(self,compositeTuple):
    """
    Add mask to leaf node and save mask to disk
    Input is a tuple (leaf node name, base node name, Image mask)
    """
    if self.G.has_node(compositeTuple[0]):
        fname = compositeTuple[0] + '_composite_mask.png'
        self.G.node[compositeTuple[0]]['compositemaskname']=fname
        self.G.node[compositeTuple[0]]['compositebase']=compositeTuple[1]
        compositeTuple[2].save(os.path.abspath(os.path.join(self.dir,fname)))
   
  def get_edge_image(self,start,end,path):
     edge = self.get_edge(start,end)
     values  = getPathValues(edge,path)
     if len(values) > 0:
       value = values[0]
       im = self.openImage(os.path.abspath(os.path.join(self.dir,value)),mask=True)
       return im,value
     return None,None

  def update_edge(self, start, end,**kwargs):
    if start is None or end is None:
      return
    if not self.G.has_node(start) or not self.G.has_node(end):
      return
    unsetkeys = []
    for k,v in kwargs.iteritems():
      if v is not None:
        self._updateEdgePathValue(start,end,k,v)
      else:
        unsetkeys.append(k)
    for k in unsetkeys:
       if k in self.G[start][end]:
         self.G[start][end].pop(k) 

  def _handle_inputfile(self,inputfile):
    """
     Input files may need to be copied to the working project directory
    """
    includePathInUndo = False
    if inputfile is None or len(inputfile) == 0:
      return '','no'
    filename=os.path.split(inputfile)[1]
    newpathname = os.path.join(self.dir,filename)
    # already slated for removal
    includePathInUndo = (newpathname in self.filesToRemove)
    if not os.path.exists(newpathname):
       includePathInUndo = True
       if os.path.exists(inputfile):
          shutil.copy2(inputfile, newpathname)
       if newpathname in self.filesToRemove:
        self.filesToRemove.remove(newpathname)
    return filename, 'yes' if includePathInUndo else 'no'

  def add_edge(self,start, end,maskname=None,mask=None,op='Change',description='',**kwargs):
    newmaskpathname = os.path.join(self.dir,maskname)
    mask.save(newmaskpathname)
    for path,ownership in self.edgeFilePaths.iteritems():
      vals = getPathValues(kwargs,path)
      if ownership and len(vals) > 0:
        pathvalue,ownershipvalue= self._handle_inputfile(vals[0])
        if vals[0]:
          kwargs[path] = pathvalue
          kwargs[ownership] = ownershipvalue
    # do not remove old version of mask if not saved previously
    if newmaskpathname in self.filesToRemove:
       self.filesToRemove.remove(newmaskpathname)
    self.G.add_edge(start,end, maskname=maskname,op=op, \
         description=description, username=get_username(), opsys=getOS(), \
         **kwargs)
    self.U = []
    self.U.append(dict(action='addEdge', start=start,end=end, **self.G.edge[start][end]))
    return mask

  def get_composite_mask(self,name):
    if name in self.G.nodes and 'compositemaskname' in self.G.node[name]:
      filename= os.path.abspath(os.path.join(self.dir,self.G.node[name]['compositemaskname']))
      im = self.openImage(filename,mask=True)
      return im,filename
    return None,None

  def get_image(self,name):
    filename= os.path.abspath(os.path.join(self.dir,self.G.node[name]['file']))
    im = self.openImage(filename)
    return im,filename

  def get_edge(self,start,end):
    return self.G[start][end] if (self.G.has_edge(start,end)) else None

  def _edgeFileRemover(self,actionList, edgeFunc, start,end,edge):
    """
      Remove an edge and all owned files
    """
    if edgeFunc is not None:
       edgeFunc(edge)
    for path,ownership in self.edgeFilePaths.iteritems():
       for pathvalue in getPathValues(edge,path):
          if pathvalue and len(pathvalue)> 0 and (ownership not in edge or edge[ownership] == 'yes'):
            f = os.path.abspath(os.path.join(self.dir,pathvalue))
            if (os.path.exists(f)):
               self.filesToRemove.add(f)
    actionList.append(dict(start=start,end=end,action='removeEdge',**self.G.edge[start][end]))

  def remove(self,node,edgeFunc=None,children=False):
    self.U = []
    self.E = []
    def fileRemover(start,end,edge):
       self._edgeFileRemover(self.E,edgeFunc,start,end,edge)
    #remove predecessor edges
    for p in self.G.predecessors(node):
      fileRemover(p,node,self.G.edge[p][node])
    # remove edges or deep dive removal
    nodes_to_remove = queue_nodes(self.G,[node],node,fileRemover) if children else \
    remove_edges(self.G,[node], node, fileRemover)
    for n in nodes_to_remove:
      if (self.G.has_node(n)):
        f = os.path.abspath(os.path.join(self.dir,self.G.node[n]['file']))
        if (self.G.node[n]['ownership']=='yes' and os.path.exists(f)):
          self.filesToRemove.add(f)
        self.U.append(dict(name=n,action='removeNode',**self.G.node[n]))
        self.G.remove_node(n)
    # edges always added after nodes to the undo list
    for e in self.E:
       self.U.append(e)
    self.E=[]

  def remove_edge(self,start,end,edgeFunc=None):
    self.U = []
    edge = self.G.edge[start][end]
    self._edgeFileRemover(self.U,edgeFunc,start,end,edge)
    self.G.remove_edge(start,end)

  def has_neighbors(self,node):
     return len(self.G.predecessors(node)) + len(self.G.successors(node))  > 0

  def predecessors(self,node):
     return self.G.predecessors(node)

  def successors(self,node):
     return self.G.successors(node)

  def has_node(self, name):
     return self.G.has_node(name)

  def getDataItem(self,item):
    return self.G.graph[item] if item in self.G.graph else None
     
  def setDataItem(self,item,value):
    self.G.graph[item] = value

  def get_node(self,name):
    if self.G.has_node(name):
      return self.G.node[name]
    else:
      return None

  def getVersion(self):
    return igversion

  def load(self,pathname):
    global igversion
    with open(pathname,"r") as f:
      try:
         self.G = json_graph.node_link_graph(json.load(f,encoding='cp1252'),multigraph=False,directed=True)
      except  ValueError:
         self.G = json_graph.node_link_graph(json.load(f),multigraph=False,directed=True)
      if 'igversion' in self.G.graph:
        if self.G.graph['igversion'] != igversion:
          raise ValueError('Mismatched version. Graph needs to be upgraded to ' + igversion)
      self.G.graph['igversion'] = igversion
      if 'idcount' in self.G.graph:
        self.idc = self.G.graph['idcount']
      elif self.G.has_node('idcount'):
        self.idc = self.G.node['idcount']['count']
        self.G.graph['idcount']=self.idc
        self.G.remove_node('idcount')
    self.dir = os.path.abspath(os.path.split(pathname)[0])
     
  def saveas(self, pathname):
     currentdir = self.dir
     fname = os.path.split(pathname)[1]
     name = get_pre_name(fname)
     self.dir = os.path.abspath(os.path.split(pathname)[0])
     self.G.name = name
     filename=os.path.abspath(os.path.join(self.dir,self.G.name + '.json'))
     self._copy_contents(currentdir)
     with open(filename, 'w') as f:
        jg = json.dump(json_graph.node_link_data(self.G),f,indent=2,encoding='cp1252')
     self.filesToRemove.clear()

  def save(self):
     filename=os.path.abspath(os.path.join(self.dir,self.G.name + '.json'))
     with open(filename, 'w') as f:
        jg = json.dump(json_graph.node_link_data(self.G),f,indent=2,encoding='cp1252')
     for f in self.filesToRemove:
       os.remove(f)
     self.filesToRemove.clear()

  def nextId(self):
    self.idc+=1
    self.G.graph['idcount']=self.idc
    return self.idc

  def _copy_contents(self, currentdir):
    def moveFile(newdir, currentdir, name):
      oldpathname = os.path.join(currentdir,name)
      newpathname = os.path.join(newdir,name)
      if (not os.path.exists(newpathname)):
         shutil.copy2(oldpathname, newpathname)

    for nname in self.G.nodes():
      node = self.G.node[nname]
      moveFile(self.dir,currentdir,node['file'])

    for edgename in self.G.edges():
      edge= self.G[edgename[0]][edgename[1]]
      for path,ownership in self.edgeFilePaths.iteritems():
        for pathvalue in getPathValues(edge,path):
           if not pathvalue or len(pathvalue) == 0:
               continue
           if ownership:
              edge[ownership] = 'yes'
           moveFile(self.dir,currentdir,pathvalue)

  def file_check(self):
    missing = []
    for nname in self.G.nodes():
      node = self.G.node[nname]
      if not os.path.exists(os.path.join(self.dir,node['file'])):
         missing.append((str(nname),str(nname),str(nname) + ' is missing image file in project'))
    for edgename in self.G.edges():
      edge= self.G[edgename[0]][edgename[1]]
      for path,ownership in self.edgeFilePaths.iteritems():
        for pathvalue in getPathValues(edge,path):
          if not pathvalue or len(pathvalue) == 0:
             continue
          newpathname = os.path.join(self.dir,pathvalue)
          if not os.path.exists(os.path.join(self.dir,node['file'])):
             missing.append((str(edgename[0]),str(edgename[1]),str(edgename[0]) + ' => ' + str(edgename[1]) + ' is missing ' + path + ' file in project'))
    return missing
        
  def create_archive(self, location):
    self.save()
    fname = os.path.join(location,self.G.name + '.tgz')
    archive = tarfile.open(fname,"w:gz")
    archive.add(os.path.join(self.dir,self.G.name + ".json"),arcname=os.path.join(self.G.name,self.G.name + ".json"))
    errors = []
    for nname in self.G.nodes():
       node = self.G.node[nname]
       if os.path.exists(os.path.join(self.dir,node['file'])):
         archive.add(os.path.join(self.dir,node['file']),arcname=os.path.join(self.G.name,node['file']))
       else:
         errors.append((str(nname),str(nname),str(nname) + " missing file"))
    for edgename in self.G.edges():
      edge= self.G[edgename[0]][edgename[1]]
      errors.extend(self._archive_edge(edgename[0],edgename[1],edge,self.G.name, archive))
    archive.close()
    return fname,errors

  def _archive_edge(self,start,end,edge, archive_name,archive):
    errors = []
    for path,ownership in self.edgeFilePaths.iteritems():
      for pathvalue in getPathValues(edge,path):
         if not pathvalue or len(pathvalue) == 0:
             continue
         newpathname = os.path.join(self.dir,pathvalue)
         if os.path.exists(newpathname):
           archive.add(newpathname,arcname=os.path.join(archive_name,pathvalue))
         else:
           errors.append((str(start),str(end),str(start) + ' => ' + str(end) + ': ' + ' missing ' + pathvalue))
    return errors

  def _archive_path(self, child, archive_name, archive, pathGraph):
     node = self.G.node[child]
     pathGraph.add_node(child,**node)
     archive.add(os.path.join(self.dir,node['file']),arcname=os.path.join(archive_name,node['file']))
     errors = []
     for parent in self.G.predecessors(child):
       errors.extend(self._archive_edge(self.G[parent][child],archive_name,archive))
       pathGraph.add_edge(parent,child,**self.G[parent][child])
       errors.extend(self._archive_path(parent,archive_name, archive,pathGraph))
     return errors

  def _updatePathValue(self,d,path,value):
      pos = path.find('.')
      if pos < 0:
           d[path] = value
      else:
          self._updatePathValue(d[path[0:pos]],path[pos+1:], value)

  def _buildPath(self, value, edgePaths):
      if type(value) is dict and edgePaths[0] in value:
         return edgePaths[0] + (("." + self._buildPath(value[edgePaths[0]],edgePaths[1:])) if len(edgePaths)>1 else '')
      return ''

  def _buildStructure(self,path,value):
       pos = path.find('.')
       if pos > 0:
             return {path[0:pos]:self._buildStructure(path[pos+1:],value)}
       return {path:value}

  def _updateEdgePathValue(self, start, end, path, value):
        self._updatePathValue(self.G[start][end],path,value)
        for edgePath in self.edgeFilePaths:
            struct  = self._buildStructure(path,value)
            revisedPath = self._buildPath(struct, edgePath.split('.'))
            if revisedPath == edgePath:
                ownership = self.edgeFilePaths[revisedPath]
                if ownership:
                   filenamevalue,ownershipvalue = self._handle_inputfile(getPathValues(struct, revisedPath)[0])
                   self._updatePathValue(self.G[start][end],revisedPath,filenamevalue)
                   self._updatePathValue(self.G[start][end],ownership,ownershipvalue)
                return
 
  def create_path_archive(self, location, end):
    self.save()
    if end in self.G.nodes():
      node = self.G.node[end]
      archive_name=node['file'].replace('.','_')
      archive = tarfile.open(os.path.join(location,archive_name + '.tgz'),"w:gz")
      pathGraph = nx.DiGraph(name="Empty")
      errors = self._archive_path(end,archive_name, archive,pathGraph)
      filename=os.path.abspath(os.path.join(self.dir,archive_name + '.json'))

      old = None
      if os.path.exists(filename):
        old = 'backup.json'
        shutil.copy2(filename, old)

      with open(filename, 'w') as f:
        jg = json.dump(json_graph.node_link_data(pathGraph),f,indent=2)
      archive.add(filename,arcname=os.path.join(archive_name,archive_name + '.json'))
      archive.close()
      if old is not None:
        shutil.copy2(old,filename)
      else:
        os.remove(filename)
      return errors

class VideoGraph(ImageGraph):

  def __init__(self, pathname):
    ImageGraph.__init__(self,pathname,projecttype='video')

  def openImage(self,fileName, metadata={},mask=False):
    imgDir = os.path.split(os.path.abspath(fileName))[0]
    return openImage(fileName, \
                     videoFrameTime=None if 'change_pts_time' not in metadata else metadata['change_pts_time'], \
                     isMask=mask, \
                     preserveSnapshot=imgDir== os.path.abspath(self.dir))

  def _saveImage(self,pathname,image):
    image.save(newpathname,exif=image.info['exif'])

