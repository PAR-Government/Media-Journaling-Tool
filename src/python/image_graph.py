from PIL import Image, ImageTk
import networkx as nx
from networkx.readwrite import json_graph
from copy import copy
import json
import os
import shutil
import cv2
import getpass
import datetime
from software_loader import Software, SoftwareLoader, getOS
import tarfile

try:
  import pwd
  import os
  class PwdX():
     def getpwuid(self):
          return pwd.getpwuid( os.getuid() )[ 0 ]
  pwdAPI = PwdX()
except ImportError:
  class PwdX():
     def getpwuid(self):
          return getpass.getuser()
  pwdAPI = PwdX()

def get_username():
    return pwdAPI.getpwuid()

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

  def getUIGraph(self):
    return self.G

  def get_name(self):
    return self.G.name

  def __init__(self, pathname):
    fname = os.path.split(pathname)[1]
    name = get_pre_name(fname)
    self.dir = os.path.abspath(os.path.split(pathname)[0])
    self.G = nx.DiGraph(name=name)
    if (os.path.exists(pathname)):
      self.load(pathname)

  def get_nodes(self):
    return self.G.nodes()

  def edges_iter(self, node):
    return self.G.edges_iter(node)

  def get_pathname(self, name):
     return os.path.join(self.dir, self.G.node[name]['file'])

  def get_edges(self):
    return self.G.edges()

  def add_node(self,pathname, seriesname=None, image=None):
    fname = os.path.split(pathname)[1]
    origname = nname = get_pre_name(fname)
    suffix = get_suffix(fname)
#    nname = nname + '_' + str(self.nextId())
    while (self.G.has_node(nname)):
      nname = nname + '_' + str(self.nextId())
      fname = nname + suffix
    newpathname = os.path.join(self.dir,fname)
    includePathInUndo = (newpathname in self.filesToRemove)
    if (not os.path.exists(newpathname)):
      includePathInUndo = True
      if (os.path.exists(pathname)):
        shutil.copy2(pathname, newpathname)
      elif image is not None:
        image.save(newpathname)
    self.G.add_node(nname, seriesname=(origname if seriesname is None else seriesname), file=fname, ownership=('yes' if includePathInUndo else 'no'), ctime=datetime.datetime.strftime(datetime.datetime.now(), '%Y-%m-%d %H:%M:%S'))
    self.U = []
    self.U.append(dict(name=nname, action='addNode', **self.G.node[nname]))
    # adding back a file that was targeted for removal
    if newpathname in self.filesToRemove:
      self.filesToRemove.remove(newpathname)
    return nname
    
  def undo(self):
    for d in self.U:
      action = d.pop('action')
      if action == 'removeNode':
         k = os.path.join(self.dir,d['file'])
         if k in self.filesToRemove:
           self.filesToRemove.remove(k)
         name = d.pop('name')
         self.G.add_node(name,**d)
      elif action == 'removeEdge':
         k = os.path.join(self.dir,d['maskname'])
         if k in self.filesToRemove:
           self.filesToRemove.remove(k)
         if 'inputmaskname' in d:
            k = os.path.join(self.dir,d['inputmaskname'])
            if k in self.filesToRemove:
              self.filesToRemove.remove(k)
         start = d.pop('start')
         end = d.pop('end')
         self.G.add_edge(start,end,**d)
      elif action == 'addNode':
         if (d['ownership'] == 'yes'):
             os.remove(os.path.join(self.dir,d['file']))
         self.G.remove_node(d['name'])
      elif action == 'addEdge':
         if (d['ownership'] == 'yes'):
             os.remove(os.path.join(self.dir,d['maskname']))
         self.G.remove_edge(d['start'],d['end'])
    self.U = []

  def update_edge(self, start, end,**kwargs):
    if start is None or end is None:
      return
    if not self.G.has_node(start) or not self.G.has_node(end):
      return
    own = None
    for k,v in kwargs.iteritems():
      if v is not None:
        if k == 'inputmaskownership' and own is None:
          own = v
        elif k=='inputmaskpathname':
          inputmaskname,own = self.handle_inputmask(v)
          self.G[start][end]['inputmaskname']=inputmaskname
        else:
          self.G[start][end][k]=v
    self.G[start][end]['inputmaskownership']=own if own is not None else 'no'

  def get_inputmaskpathname(self,start,end):
    e = self.G[start][end]
    return os.path.join(self.dir, e['inputmaskname']) if 'inputmaskname' in e and e['inputmaskname'] != '' else None

  def handle_inputmask(self,inputmaskpathname):
    includePathInUndo = False
    inputmaskname = ''
    if inputmaskpathname is not None and len(inputmaskpathname)>0:
      inputmaskname=os.path.split(inputmaskpathname)[1]
      newinputpathname = os.path.join(self.dir,inputmaskname)
      # already slated for removal
      includePathInUndo = (newinputpathname in self.filesToRemove)
      if (not os.path.exists(newinputpathname)):
        includePathInUndo = True
        if (os.path.exists(inputmaskpathname)):
          shutil.copy2(inputmaskpathname, newinputpathname)
      if newinputpathname in self.filesToRemove:
        self.filesToRemove.remove(newinputpathname)
    return inputmaskname, 'yes' if includePathInUndo else 'no'

  def add_edge(self,start, end,inputmaskpathname=None,maskname=None,mask=None,op='Change',description='',**kwargs):
    im =  Image.fromarray(mask)
    newpathname = os.path.join(self.dir,maskname)
    cv2.imwrite(newpathname,mask)
    inputmaskname,inputmaskownership= self.handle_inputmask(inputmaskpathname)
    # do not remove old version of mask if not saved previously
    if newpathname in self.filesToRemove:
      self.filesToRemove.remove(newpathname)
    self.G.add_edge(start,end, maskname=maskname,op=op, \
         description=description, username=get_username(), opsys=getOS(), \
         inputmaskname=inputmaskname, \
         inputmaskownership=inputmaskownership, \
         **kwargs)
    self.U = []
    self.U.append(dict(action='addEdge', ownership='yes', start=start,end=end, **self.G.edge[start][end]))
    return im

  def get_image(self,name):
    with open(os.path.abspath(os.path.join(self.dir,self.G.node[name]['file'])),"rb") as fp:
       im= Image.open(fp)
       im.load()
       return im

  def get_edge(self,start,end):
    return self.G[start][end] if (self.G.has_edge(start,end)) else None

  def get_edge_mask(self,start,end):
    with open(os.path.abspath(os.path.join(self.dir,self.G[start][end]['maskname'])),"rb") as fp:
       im= Image.open(fp)
       im.load()
       return im

  def _maskRemover(self,actionList, edgeFunc, start,end,edge):
       if edgeFunc is not None:
         edgeFunc(edge)
       f = os.path.abspath(os.path.join(self.dir,edge['maskname']))
       if (os.path.exists(f)):
          self.filesToRemove.add(f)
       if 'inputmaskname' in edge:
          f = os.path.abspath(os.path.join(self.dir,edge['inputmaskname']))
          if (os.path.exists(f)):
            self.filesToRemove.add(f)
       actionList.append(dict(start=start,end=end,action='removeEdge',**self.G.edge[start][end]))

  def remove(self,node,edgeFunc=None,children=False):
    self.U = []
    self.E = []
    def maskRemover(start,end,edge):
       self._maskRemover(self.E,edgeFunc,start,end,edge)
    #remove predecessor edges
    for p in self.G.predecessors(node):
      maskRemover(p,node,self.G.edge[p][node])
    # remove edges or deep dive removal
    nodes_to_remove = queue_nodes(self.G,[node],node,maskRemover) if children else \
    remove_edges(self.G,[node], node, maskRemover)
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
    self._maskRemover(self.U,edgeFunc,start,end,edge)
    self.G.remove_edge(start,end)

  def predecessors(self,node):
     return self.G.predecessors(node)

  def successors(self,node):
     return self.G.successors(node)

  def has_node(self, name):
     return self.G.has_node(name)

  def get_node(self,name):
    if self.G.has_node(name):
      return self.G.node[name]
    else:
      return None

  def load(self,pathname):
    with open(pathname,"r") as f:
      d = json.load(f)
      self.G = json_graph.node_link_graph(d)
    if (self.G.has_node('idcount')):
      self.idc = self.G.node['idcount']['count']
      self.G.remove_node('idcount')
    self.dir = os.path.abspath(os.path.split(pathname)[0])
     
  def saveas(self, pathname):
     currentdir = self.dir
     fname = os.path.split(pathname)[1]
     name = get_pre_name(fname)
     self.dir = os.path.abspath(os.path.split(pathname)[0])
     self.G.name = name
     filename=os.path.abspath(os.path.join(self.dir,self.G.name + '.json'))
     self.G.add_node('idcount',count=self.idc)
     with open(filename, 'w') as f:
        jg = json.dump(json_graph.node_link_data(self.G),f,indent=2)
     self.G.remove_node('idcount')
     self._copy_contents(currentdir)
     self.filesToRemove.clear()

  def save(self):
     filename=os.path.abspath(os.path.join(self.dir,self.G.name + '.json'))
     self.G.add_node('idcount',count=self.idc)
     with open(filename, 'w') as f:
        jg = json.dump(json_graph.node_link_data(self.G),f,indent=2)
     self.G.remove_node('idcount')
     for f in self.filesToRemove:
       os.remove(f)
     self.filesToRemove.clear()

  def nextId(self):
    self.idc+=1
    return self.idc

  def _copy_contents(self, currentdir):
    for nname in self.G.nodes():
      node = self.G.node[nname]
      oldpathname = os.path.join(currentdir,node['file'])
      newpathname = os.path.join(self.dir,node['file'])
      if (not os.path.exists(newpathname)):
          shutil.copy2(oldpathname, newpathname)
    for edgename in self.G.edges():
      edge= self.G[edgename[0]][edgename[1]]
      oldpathname = os.path.join(currentdir,edge['maskname'])
      newpathname = os.path.join(self.dir,edge['maskname'])
      if (not os.path.exists(newpathname)):
          shutil.copy2(oldpathname, newpathname)
      if 'inputmasknanme' in edge:
        oldpathname = os.path.join(currentdir,edge['inputmaskname'])
        newpathname = os.path.join(self.dir,edge['inputmaskname'])
        if (not os.path.exists(newpathname)):
            shutil.copy2(oldpathname, newpathname)

  def create_archive(self, location):
    self.save()
    archive = tarfile.open(os.path.join(location,self.G.name + '.tgz'),"w:gz")
    archive.add(os.path.join(self.dir,self.G.name + ".json"),arcname=os.path.join(self.G.name,self.G.name + ".json"))
    for nname in self.G.nodes():
       node = self.G.node[nname]
       archive.add(os.path.join(self.dir,node['file']),arcname=os.path.join(self.G.name,node['file']))
    for edgename in self.G.edges():
      edge= self.G[edgename[0]][edgename[1]]
      self._archive_edge(edge,self.G.name, archive)
    archive.close()

  def _archive_edge(self,edge, archive_name,archive):
     newpathname = os.path.join(self.dir,edge['maskname'])
     archive.add(newpathname,arcname=os.path.join(archive_name,edge['maskname']))
     if 'inputmaskname' in edge:
       newpathname = os.path.join(self.dir,edge['inputmaskname'])
       archive.add(newpathname,arcname=os.path.join(archive_name,edge['inputmaskname']))

  def _archive_path(self, child, archive_name, archive, pathGraph):
     node = self.G.node[child]
     pathGraph.add_node(child,**node)
     archive.add(os.path.join(self.dir,node['file']),arcname=os.path.join(archive_name,node['file']))
     for parent in self.G.predecessors(child):
       self._archive_edge(self.G[parent][child],archive_name,archive)
       pathGraph.add_edge(parent,child,**self.G[parent][child])
       self._archive_path(parent,archive_name, archive,pathGraph)

 
  def create_path_archive(self, location, end):
    self.save()
    if end in self.G.nodes():
      node = self.G.node[end]
      archive_name=node['file'].replace('.','_')
      archive = tarfile.open(os.path.join(location,archive_name + '.tgz'),"w:gz")
      pathGraph = nx.DiGraph(name="Empty")
      self._archive_path(end,archive_name, archive,pathGraph)
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

