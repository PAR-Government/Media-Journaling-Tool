from PIL import Image, ImageTk
import networkx as nx
from networkx.readwrite import json_graph
from copy import copy
import json
import os
import shutil
import cv2
import getpass

try:
  import pwd
except ImportError:
  class Pwd():
     def getpwuid(self, user):
          return getpass.getuser()
  pwd = Pwd()

def get_username():
    return pwd.getpwuid( os.getuid() )[ 0 ]

def get_pre_name(file):
  pos = file.rfind('.')
  return file[0:pos] if (pos > 0) else file

def get_suffix(file):
  pos = file.rfind('.')
  return file[pos:] if (pos > 0) else '.json'

def queue_nodes(g,nodes,node,func):
  for s in g.successors(node):
    if len(g.predecessors(s)) > 1:
        continue
    queue_nodes(g,nodes,s,func)
    func(g.edge[node][s])
    nodes.append(s)
  return nodes

class ImageGraph:
  G = nx.DiGraph(name="Empty")
  U = nx.DiGraph(name="undo")
  idc = 0
  dir = os.path.abspath('.')

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
    includePathInUndo = False
    if (not os.path.exists(newpathname)):
      includePathInUndo = True
      if (os.path.exists(pathname)):
        shutil.copy2(pathname, newpathname)
      elif image is not None:
        image.save(newpathname)
    self.G.add_node(nname, seriesname=(origname if seriesname is None else seriesname), file=fname, ownership=('yes' if includePathInUndo else 'no'))
    self.U = nx.DiGraph(name="undo")
    self.U.add_node(nname, action='addNode', file=fname, ownership=('yes' if includePathInUndo else 'no'))
    return nname
    
  def undo(self):
    # hack for now
    if (len(self.U.nodes()) > 1):
      self.G = self.U
    else:
      for nid in self.U.nodes():
        node = self.U.node[nid]
        if (node['action'] == 'addNode'):
           if (node['ownership'] == 'yes'):
             os.remove(os.path.join(self.dir,node['file']))
           self.G.remove_node(nid)
        if (node['action'] == 'addEdge'):
           if (node['ownership'] == 'yes'):
             os.remove(os.path.join(self.dir,nid))
           self.G.remove_edge(node['start'],node['end'])
    self.U = nx.DiGraph(name="undo")

  def update_edge(self, start, end,op=None,description=None):
    if start is None or end is None:
      return
    if not self.G.has_node(start) or not self.G.has_node(end):
      return
    if (op is not None):
      self.G[start][end]['op'] = op 
    if (description is not None):
      self.G[start][end]['description'] = description
    
  def add_edge(self,start, end, maskname=None,mask=None, op='Change',description=''):
    im =  Image.fromarray(mask)
    newpathname = os.path.join(self.dir,maskname)
    includePathInUndo = False
    if (not os.path.exists(newpathname)):
      cv2.imwrite(newpathname,mask)
      includePathInUndo = True
    self.G.add_edge(start,end, maskname=maskname, op=op, description=description, username=get_username())
    self.U = nx.DiGraph(name="undo")
    self.U.add_node(maskname, action='addEdge',start=start,end=end,ownership=('yes' if includePathInUndo else 'no'))
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

  def remove(self,node,edgeFunc=None):
    def maskRemover(edge):
       if edgeFunc is not None:
         edgeFunc(edge)
       f = os.path.abspath(os.path.join(self.dir,edge['maskname']))
       if (os.path.exists(f)):
          os.remove(f)
    self.U = self.G.copy()
    for p in self.G.predecessors(node):
      if edgeFunc is not None:
        edgeFunc(self.G.edge[p][node])
      maskRemover(self.G.edge[p][node])
    nodes_to_remove = queue_nodes(self.G,[node],node,maskRemover)
    for n in nodes_to_remove:
      if (self.G.has_node(n)):
        f = os.path.abspath(os.path.join(self.dir,self.G.node[n]['file']))
        if (self.G.node[n]['ownership']=='yes' and os.path.exists(f)):
          os.remove(f)
        self.G.remove_node(n)

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

  def save(self):
     filename=os.path.abspath(os.path.join(self.dir,self.G.name + '.json'))
     self.G.add_node('idcount',count=self.idc)
     with open(filename, 'w') as f:
        jg = json.dump(json_graph.node_link_data(self.G),f,indent=2)
     self.G.remove_node('idcount')

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
