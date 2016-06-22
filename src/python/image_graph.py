from PIL import Image, ImageTk
import networkx as nx
from networkx.readwrite import json_graph
from copy import copy
import json
import os
import shutil
import cv2

def queue_nodes(g,nodes,node,func):
  for s in g.successors(node):
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

  def set_name(self, name):
    self.G.name = name

  def get_name(self):
    return self.G.name

  def __init__(self, name, dir):
    self.G = nx.DiGraph(name=name)
    self.dir = os.path.abspath(dir)

  def get_nodes(self):
    return self.G.nodes()

  def edges_iter(self, node):
    return self.G.edges_iter(node)

  def get_edges(self):
    return self.G.edges()

  def add_node(self,pathname, seriesname=None):
    fname = os.path.split(pathname)[1]
    origname = nname = fname[0:fname.rfind('.')]
    suffix = fname[fname.rfind('.'):]
    while (self.G.has_node(nname)):
      nname = nname + '_' + str(self.nextId())
      fname = nname + suffix
    newpathname = os.path.join(self.dir,fname)
    includePathInUndo = False
    if (not os.path.exists(newpathname)):
      shutil.copy2(pathname, newpathname)
      includePathInUndo = True
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

  def add_edge(self,start, end, maskname=None,mask=None, op='Change',description=''):
    im =  Image.fromarray(mask)
    newpathname = os.path.join(self.dir,maskname)
    includePathInUndo = False
    if (not os.path.exists(newpathname)):
      cv2.imwrite(newpathname,mask)
      includePathInUndo = True
    self.G.add_edge(start,end, maskname=maskname, op=op, description=description)
    self.U = nx.DiGraph(name="undo")
    self.U.add_node(maskname, action='addEdge',start=start,end=end,ownership=('yes' if includePathInUndo else 'no'))
    return im

  def get_image(self,name):
    with open(os.path.abspath(os.path.join(self.dir,self.G.node[name]['file']))) as fp:
       im= Image.open(fp)
       im.load()
       return im

  def get_edge(self,start,end):
    return self.G[start][end]

  def get_edge_mask(self,start,end):
    with open(os.path.abspath(os.path.join(self.dir,self.G[start][end]['maskname']))) as fp:
       im= Image.open(fp)
       im.load()
       return im

  def remove(self,node,edgeFunc):
    self.U = self.G.copy()
    for p in self.G.predecessors(node):
      edgeFunc(self.G.edge[p][node])
    nodes_to_remove = queue_nodes(self.G,[node],node,edgeFunc)
    for n in nodes_to_remove:
      if (self.G.has_node(n)):
        self.G.remove_node(n)

  def predecessors(self,node):
     return self.G.predecessors(node)

  def successors(self,node):
     return self.G.successors(node)

  def has_node(self, name):
     return self.G.has_node(name)

  def get_node(self,name):
    return self.G.node[name]

  def load(self,fname):
    with open(fname) as f:
      d = json.load(f)
      self.G = json_graph.node_link_graph(d)
    if (self.G.has_node('idcount')):
      self.idc = self.G.node['idcount']['count']
      self.G.remove_node('idcount')
     
  def save(self):
     filename=os.path.abspath(os.path.join(self.dir,self.G.name + '.json'))
     self.G.add_node('idcount',count=self.idc)
     with open(filename, 'w') as f:
        jg = json.dump(json_graph.node_link_data(self.G),f,indent=2)
     self.G.remove_node('idcount')

  def nextId(self):
    self.idc+=1
    return self.idc
