import networkx as nx
import Tkinter as tk
import tkMessageBox
import tkSimpleDialog as tkd
from functools import wraps
from scenario_model import ProjectModel
import numpy as np
from math import atan2, pi, cos, sin
from description_dialog import DescriptionCaptureDialog,CompareDialog

class MaskGraphCanvas(tk.Canvas):

    crossHairConnect = False

    toItemIds = {}
    itemToNodeIds = {}
    itemToEdgeIds = {}
    itemToCanvas = {}
    marked = None
    ops = []
    lastNodeAdded = None
    
    drag_data = {'x': 0, 'y': 0, 'item': None}

    def __init__(self, master,scModel,callback,ops,**kwargs):
        self.scModel = scModel
        self.callback = callback
        self.master = master
        self.ops=ops
        tk.Canvas.__init__(self, master, **kwargs)
        self.bind('<ButtonPress-1>', self.deselectCursor)
        self._plot_graph()
   
    def clear(self):
        self._unmark()
        self.delete(tk.ALL)
        self.toItemIds = {}
        self.itemToNodeIds = {}
        self.itemToEdgeIds = {}
        self.itemToCanvas = {}

    def plot(self, home_node):
        self.clear()
        self._plot_graph()
#        if (home_node is not None):
#           self.center_on_node(home_node)

    def _node_center(self, node_name):
        """Calcualte the center of a given node"""
        item_id = self.toItemIds[node_name]
        b = self.bbox(item_id[1])
        return ( (b[0]+b[2])/2, (b[1]+b[3])/2 )

    def center_on_node(self, node_name):
        """Center canvas on given **DATA** node"""
        try:
            wid = self.toItemIds[node_name][1]
        except ValueError as e:
            return

        x,y = self.coords(wid)

        # Find center of canvas
        w = self.winfo_width()/2
        h = self.winfo_height()/2
        if w == 0:
            # We haven't been drawn yet
            w = int(self['width'])/2
            h = int(self['height'])/2

        # Calc delta to move to center
        delta_x = w - x
        delta_y = h - y

        self.move(tk.ALL, delta_x, delta_y)

    def addNew(self,ids):
       wx,wy = self.winfo_width(), self.winfo_height()
       center =  (0,50)
       for name in self.scModel.getGraph().get_nodes():
           n = self.scModel.getGraph().get_node(name)
           if (n.has_key('xpos')):
              center = ( max(center[0],n['xpos']), min(center[1],n['ypos']))
       if (center[0] + 75 > wx):
          center = (center[0], center[1]+30)
       else:
          center = (center[0]+75, center[1])
       for id in ids:
         node = self.scModel.getGraph().get_node(id)
         node['xpos'] = center[0]
         node['ypos'] = center[1]
         self.lastNodeAdded = node
         self._mark(self._draw_node(id))
         center = (center[0], center[1]+30)

    def add(self,start, end):
       center = self._node_center(start)
       wx,wy = self.winfo_width(), self.winfo_height()
       node = self.scModel.getGraph().get_node(end)
       node['ypos'] = center[1]+int(wy/4.0)
       node['xpos'] = center[0]
       if (self.lastNodeAdded is not None):
           diff = abs(self.lastNodeAdded['xpos'] - node['xpos']) + \
           abs(self.lastNodeAdded['ypos'] - node['ypos'])
           if diff < 10:
               node['xpos']+=40
       self.lastNodeAdded = node
       self._draw_node(end)
       self._mark(self._draw_edge(start,end))
     
    def update(self):
       self.plot(self.scModel.start)
          
    def _get_id(self, event):
        if (hasattr(event,'obtype')):
           return self.toItemIds[event.item_name][1]
        for item in self.find_closest(event.x, event.y):
           return item
        return None

    def onNodeButtonRelease(self, event):
        """End drag of an object"""

        # reset the drag information
        self.drag_data['item'] = None
        self.drag_data['x'] = 0
        self.drag_data['y'] = 0

    def selectCursor(self,event):
        self.config(cursor='crosshair')
        self.crossHairConnect = not (event == 'compare')
        for k,v in self.itemToCanvas.items():
           v.config(cursor='crosshair')

    def deselectCursor(self, event):
        cursor = self.cget("cursor")
        if (cursor == 'crosshair'):
           self.config(cursor='')
           for k,v in self.itemToCanvas.items():
              v.config(cursor='')

    def onNodeButtonPress(self, event):
        """Being drag of an object"""
        # record the item and its location
        item = self._get_id(event)
        cursor = self.cget("cursor")
        if (item is None):
            self.deselectCursor(None)
            return

        if (cursor == 'crosshair'):
            nodeId = self.itemToNodeIds[item]
            node = self.scModel.getGraph().get_node(nodeId)
            preds = self.scModel.getGraph().predecessors(nodeId)
            im = self.scModel.getGraph().get_image(nodeId)
            file = node['file']
            ok = False
            if self.crossHairConnect:
              if (len(preds) == 0):
                 d = DescriptionCaptureDialog(self.master,self.scModel.get_dir(),im,self.ops,file)
                 if (d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
                   msg = self.scModel.connect(nodeId,mod=d.description,software=d.getSoftware())
                   if msg is not None:
                     tkMessageBox.showwarning("Connect Error", msg)
                   else:
                     ok = True
                 else:
                   ok = False
              elif (len(preds) == 1):
                 self.scModel.connect(nodeId)
                 ok = True
              else:
                 tkMessageBox.showwarning("Error", "Destination node already has two predecessors")
            else:
                im1,im2,mask,analysis = self.scModel.compare(nodeId,seamAnalysis=False)
                CompareDialog(self.master,im2,mask,nodeId,analysis)
            self.deselectCursor(None)
            if (ok):
               self._mark(self._draw_edge(self.scModel.start,self.scModel.end))
               self.callback(event,"n")
            return

        self.drag_data["item"] = item
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

    def onNodeMotion(self, event):
        """Handle dragging of an object"""
        if self.drag_data['item'] is None:
            return
        # compute how much this object has moved
        delta_x = event.x - self.drag_data['x']
        delta_y = event.y - self.drag_data['y']
        # move the object the appropriate amount
        self.move(self.drag_data['item'], delta_x, delta_y)
        # record the new position
        self.drag_data["x"] = event.x
        self.drag_data["y"] = event.y

        # Redraw any edges
        b = self.bbox(self.drag_data['item'])
        from_xy = ( (b[0]+b[2])/2, (b[1]+b[3])/2 )
        from_node = self.itemToNodeIds[self.drag_data['item']]
        node = self.scModel.getGraph().get_node(from_node)
        node['xpos']=from_xy[0]
        node['ypos']=from_xy[1]
        for n in self.scModel.getGraph().successors(from_node):
           to_xy = self._node_center(n)
           spline_xy = self._spline_center(*from_xy+to_xy+(5,))
           self.coords(self.toItemIds[(from_node,n)][0],(from_xy+spline_xy+to_xy))
           self.coords(self.toItemIds[(from_node,n)][1],spline_xy)
    
        to_xy = from_xy
        for n in self.scModel.getGraph().predecessors(from_node):
           from_xy = self._node_center(n)
           spline_xy = self._spline_center(*from_xy+to_xy+(5,))
           self.coords(self.toItemIds[(n,from_node)][0],(from_xy+spline_xy+to_xy))
           self.coords(self.toItemIds[(n,from_node)][1],spline_xy)

    def remove(self):
       self._unmark()
       self.scModel.remove()
       self.update()

    def _unmark(self):
       if (self.marked is not None):
         self.itemToCanvas[self.marked].unmark()
         self.marked = None

    def _mark(self,item):
        self._unmark()
        self.itemToCanvas[item].mark()
        self.marked = item

    def connectto(self):
        self.selectCursor('connect')

    def compareto(self):
        self.selectCursor('compare')

    def onTokenRightClick(self, event):
       self._unmark()
       item = self._get_id(event)
       eventname = 'rcNode'
       e = None
       if (item is not None):
           if self.itemToNodeIds.has_key(item):
               self.scModel.selectImage(self.itemToNodeIds[item])
           else:
               e = self.itemToEdgeIds[item]
               self.scModel.selectPair(e[0],e[1])
               eventname= 'rcEdge' if self.scModel.isEditableEdge(e[0],e[1]) else 'rcNonEditEdge'
           self._mark(item)
           self.callback(event,eventname)
           if (e is not None):
             edge =  self.scModel.getGraph().get_edge(e[0],e[1])
             if (edge is not None):
                self.itemToCanvas[item].update(edge['op'])
    
    def onNodeKey(self, event):
       self._unmark()
       item = self._get_id(event)
       if (item is not None):
          self.scModel.selectImage(self.itemToNodeIds[item])
          self.callback(event,"n")
          self._mark(item)

    def _plot_graph(self):
        # Create nodes
        if (len(self.scModel.getGraph().get_nodes()) == 0):
            return

        scale = min(self.winfo_width(), self.winfo_height())
        if scale == 1:
            # Canvas not initilized yet; use height and width hints
            scale = int(min(self['width'], self['height']))

        # layout = self.create_layout(scale=scale, min_distance=50)

        for n in self.scModel.getGraph().get_nodes():
             self._draw_node(n)

        # Create edges
        for frm, to in set(self.scModel.getGraph().get_edges()):
            self._draw_edge(frm, to)

    def _spline_center(self, x1, y1, x2, y2, m):
        """Given the coordinate for the end points of a spline, calcuate
        the mipdoint extruded out m pixles"""
        a = (x2 + x1)/2
        b = (y2 + y1)/2
        beta = (pi/2) - atan2((y2-y1), (x2-x1))

        xa = a - m*cos(beta)
        ya = b + m*sin(beta)
        return (xa, ya)

    def _draw_node(self, id):
        wx,wy = self.winfo_width(), self.winfo_height()

        node= self.scModel.getGraph().get_node(id)
        if (node.has_key('xpos')):
          x = node['xpos']
        else:
          x = int(wx/10)
        if (node.has_key('ypos')):
          y = node['ypos']
        else:
          y = int(wy/10)

        nodeC = NodeObj(self,id)
        wid = self.create_window(x, y, window=nodeC, anchor=tk.CENTER,
                                  tags='node')
        node['xpos']=x
        node['ypos']=y
        self.toItemIds[id]=(nodeC.marker,wid)
        self.itemToNodeIds[wid]=id
        self.itemToCanvas[wid] = nodeC
        return wid

    def _draw_edge(self, u, v):
        edge =  self.scModel.getGraph().get_edge(u,v)
        x1,y1 = self._node_center(u)
        x2,y2 = self._node_center(v)
        xa,ya = self._spline_center(x1,y1,x2,y2,5)
        lineC = LineTextObj(self,edge['op'],(u,v), (x1,y1,xa,ya,x2,y2))
        wid = self.create_window(xa, ya, window=lineC, anchor=tk.CENTER,
                                  tags='edge')
        self.toItemIds[(u,v)] = (lineC.marker,wid)
        self.itemToEdgeIds[wid] = (u,v)
        self.itemToCanvas[wid] = lineC
        return wid


class NodeObj(tk.Canvas):
    node_name = ''
    marker = None
    def __init__(self, master, node_name):
        tk.Canvas.__init__(self, width=20, height=20, highlightthickness=0)

        self.master = master
        self.node_name = node_name

        self.bind('<ButtonPress-1>', self._host_event('onNodeButtonPress'))
        self.bind('<ButtonRelease-1>', self._host_event('onNodeButtonRelease'))
        self.bind('<B1-Motion>', self._host_event('onNodeMotion'))
        self.bind('<Button-2>', self._host_event('onTokenRightClick'))
        self.bind('<Double-Button-1>', self._host_event('onTokenRightClick'))
#        self.bind('<Key>', self._host_event('onNodeKey'))
#        self.bind('<Enter>', lambda e: self.focus_set())
#        self.bind('<Leave>', lambda e: self.master.focus())

        # Draw myself
        self.render(node_name)

    def render(self, node_name):
        """Draw on canvas what we want node to look like"""
        self.label = self.create_text(0, 0, text=node_name)
        self.marker = self.create_oval(0,0,15,15, fill='red',outline='black')

         # Figure out how big we really need to be
        bbox = self.bbox(self.label)
        bbox = [abs(x) for x in bbox]
        br = ( max((bbox[0] + bbox[2]),20), max((bbox[1]+bbox[3]),20) )

        self.config(width=br[0], height=br[1]+7)

        # Place label and marker
        mid = ( int(br[0]/2.0), int(br[1]/2.0)+7 )
        self.coords(self.label, mid)
        self.coords(self.marker, mid[0]-5,0, mid[0]+5,10)

    def unmark(self):
        self.itemconfig(self.marker,fill='red')

    def mark(self):
        self.itemconfig(self.marker,fill='yellow')

    def _host_event(self, func_name):
        """Wrapper to correct the event's x,y coordinates and pass to host
        canvas.  Argument should be string of name of function from
        _host_canvas to call."""
        func = getattr(self.master, func_name)
        def _wrapper(event):
            # Modify even to be relative to the host's canvas
            event.x += self.winfo_x()
            event.y += self.winfo_y()
            event.obtype = 'node'
            event.item_name = self.node_name
            return func(event)
        return _wrapper


class LineTextObj(tk.Canvas):
    def __init__(self, master,name, edge_name, coords):
        tk.Canvas.__init__(self, width=20, height=10, highlightthickness=0)

        self.name = name
        self.master = master
        self.edge_name = edge_name

        self.bind('<Button-2>', self._host_event('onTokenRightClick'))
        self.bind('<Double-Button-1>', self._host_event('onTokenRightClick'))
#        self.bind('<Enter>', lambda e: self.focus_set())
#        self.bind('<Leave>', lambda e: self.master.focus())

        self._render(name,coords)

    def _newcfg(self):
        cfg = {}
        cfg['tags'] = 'edge'
        cfg['smooth'] = True
        cfg['arrow'] = tk.LAST
        cfg['arrowshape'] = (30,40,5)
        return cfg

    def update(self, name):
        self.itemconfig(self.label, text=name)

    def _render(self, name,coords):
        cfg = self._newcfg()
        self.marker = self.master.create_line(*coords, **cfg)
        self.label = self.create_text(2,2, text=name, anchor=tk.NW)
         # Figure out how big we really need to be
        bbox = self.bbox(self.label)
        bbox = [abs(x) for x in bbox]
        br = ( max((bbox[0] + bbox[2]),20), max((bbox[1]+bbox[3]),20) )
        self.config(width=br[0]+10, height=br[1]+10)

    def unmark(self):
        cfg = self._newcfg()
        cfg['fill'] = 'black'
        self.master.itemconfig(self.marker, **cfg)

    def mark(self):
        cfg = self._newcfg()
        cfg['fill'] = 'yellow'
        self.master.itemconfig(self.marker, **cfg)

    def _host_event(self, func_name):
        """Wrapper to correct the event's x,y coordinates and pass to host
        canvas.  Argument should be string of name of function from
        _host_canvas to call."""
        func = getattr(self.master, func_name)
        def _wrapper(event):
            # Modify even to be relative to the host's canvas
            event.x += self.winfo_x()
            event.y += self.winfo_y()
            event.obtype = 'edge'
            event.item_name = self.edge_name
            return func(event)
        return _wrapper
