import Tkinter as tk
import tkMessageBox
import os
import platform
from math import atan2, pi, cos, sin
from description_dialog import DescriptionCaptureDialog, createCompareDialog
import collections

"""
Class and support for the graph view canvas of the JT
"""

EventTuple = collections.namedtuple('EventTuple', ['x_root','y_root','items'])

def restrictPosition(position):
    return max(position, 5)

def condenseName(name):
    if len(name) > 15:
      pos = name.rfind('_')
      pos = name.rfind('-')  if pos < 0 else pos
      pos = 7 if pos < 0 else len(name)-pos
      return name[0:5] + '..' + name[-pos:]
    return name

class MaskGraphCanvas(tk.Canvas):
    crossHairConnect = False

    toItemIds = {}
    itemToNodeIds = {}
    itemToEdgeIds = {}
    itemToCanvas = {}
    marked = None
    lastNodeAdded = None
    uiProfile = None

    lassoitems = None
    lassobox = None

    drag_item = None
    drag_data = None
    scrollregion = (100,100)
    region = (0,0)

    def __init__(self, master, uiProfile, scModel, callback, **kwargs):
        self.scModel = scModel
        self.uiProfile = uiProfile
        self.callback = callback
        self.master = master
        tk.Canvas.__init__(self, master, **kwargs)
        self.bind('<ButtonPress-1>', self.startregion)
        self.bind('<ButtonRelease-1>', self.stopregion)
        self.bind('<B1-Motion>', self.regionmove)
        self.bind('<Button-2>' if platform.system() == 'Darwin' else '<Button-3>',
                  self.regionmenu)
        self._plot_graph()
        self.scrollregion = kwargs['scrollregion']

    def clear(self):
        self._unmark()
        self.delete(tk.ALL)
        self.toItemIds = {}
        self.crossHairConnect = False
        self.itemToNodeIds = {}
        self.itemToEdgeIds = {}
        self.itemToCanvas = {}
        self.lassoitems = None
        self.lassobox = None
        self.drag_item = None
        self.drag_data = None

    def plot(self, home_node):
        self.clear()
        self._plot_graph()

    #        if (home_node is not None):
    #           self.center_on_node(home_node)

    def _node_center(self, node_name):
        """Calcualte the center of a given node"""
        item_id = self.toItemIds[node_name]
        b = self.bbox(item_id[1])
        return ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)

    def center_on_node(self, node_name):
        """Center canvas on given **DATA** node"""
        try:
            wid = self.toItemIds[node_name][1]
        except ValueError as e:
            return

        x, y = self.coords(wid)

        x-=self.winfo_width()/2
        y-=self.winfo_height()/2

        x = max(x,0)
        y = max(y, 0)

        # Find center of canvas
        w = self.scrollregion[2] #- self.winfo_width()
        h =  self.scrollregion[3] #-self.winfo_height()
        if w == 0:
            # We haven't been drawn yet
            w = int(self['width'])
            h = int(self['height'])

        # Calc delta to move to center
        delta_x = w - x
        delta_y = h - y

        self.xview_moveto(x/w)
        self.yview_moveto(y/h)
       # self.move(tk.ALL, delta_x, delta_y)

    def redrawNode(self, nodeid):
        wid = self.toItemIds[nodeid][1] if nodeid in self.toItemIds else None
        if wid is not None and wid in self.itemToCanvas:
            n = self.scModel.getGraph().get_node(nodeid)
            #         self.move(wid,0,0)
            if n is None:
                self.itemToCanvas[wid].node_name = 'Missing'
            else:
                self.itemToCanvas[wid].node_name = n['file']
            self.itemToCanvas[wid].render()
            self.update_idletasks()

    def addNew(self, ids):
        wx, wy = self.winfo_width(), self.winfo_height()
        center = (0, 50)
        for name in self.scModel.getGraph().get_nodes():
            n = self.scModel.getGraph().get_node(name)
            if (n.has_key('xpos')):
                center = (max(center[0], n['xpos']), min(center[1], n['ypos']))
        if (center[0] + 75 > wx):
            center = (center[0], center[1] + 30)
        else:
            center = (center[0] + 75, center[1])
        for id in ids:
            node = self.scModel.getGraph().get_node(id)
            node['xpos'] = center[0]
            node['ypos'] = center[1]
            self.lastNodeAdded = node
            self._mark(self._draw_node(id))
            center = (center[0], center[1] + 30)

    def add(self, start, end):
        center = self._node_center(start)
        wx, wy = self.winfo_width(), self.winfo_height()
        node = self.scModel.getGraph().get_node(end)
        if ('ypos' not in node or node['ypos'] <= 0) or \
                ('xpos' not in node or node['xpos'] <= 0):
            node['ypos'] = center[1] + int(wy / 4.0)
            node['xpos'] = center[0]
            if (self.lastNodeAdded is not None):
                diff = abs(self.lastNodeAdded['xpos'] - node['xpos']) + \
                       abs(self.lastNodeAdded['ypos'] - node['ypos'])
                if diff < 10:
                    node['xpos'] += 40
        self.lastNodeAdded = node
        self._draw_node(end)
        self._mark(self._draw_edge(start, end))

    def update(self):
        self.plot(self.scModel.start)

    def _get_id(self, event):
        if (hasattr(event, 'obtype')):
            return self.toItemIds[event.item_name][1]
        for item in self.find_closest(event.x, event.y):
            return item
        return None

    def onNodeButtonRelease(self, event):
        """End drag of an object"""

        # reset the drag information
        self.setDragData(None)

    def selectCursor(self, event):
        self.config(cursor='crosshair')
        self.crossHairConnect = not (event == 'compare')
        for k, v in self.itemToCanvas.items():
            v.config(cursor='crosshair')

    def regionmenu(self,event):
        if  self.lassoitems is not None and len(self.lassoitems) > 0:
            proxy = EventTuple(event.x_root,event.y_root,[self.itemToNodeIds[item] for item in self.lassoitems])
            self.callback(proxy,'rcGroup')

    def regionmove(self, event):
        if self.lassobox:
            self.delete(self.lassobox)
        if not self.lassoitems:
            x = self.canvasx(event.x)
            y = self.canvasy(event.y)
            self.setDragData((event.x, event.y))
            self.lassobox = self.create_rectangle(self.region[0], self.region[1], x, y)
        else:
            for item in self.lassoitems:
                self.moveItem(event, item)
            self.setDragData((event.x, event.y))

    def startregion(self, event):
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        self.region = (x, y)

    def add_selected_item(self,item):
        addedid = [k for (k, v) in self.itemToCanvas.items() if v == item][0]
        edgeid = self.itemToEdgeIds[addedid] if addedid in self.itemToEdgeIds else None
        if edgeid is not None:
            start = [k for (k, v) in self.itemToNodeIds.items() if v == edgeid[0]][0]
            end = [k for (k, v) in self.itemToNodeIds.items() if v == edgeid[1]][0]
            if start in self.itemToCanvas:
               self.itemToCanvas[start].selectgroup()
            if end in self.itemToCanvas:
               self.itemToCanvas[end].selectgroup()
            if self.lassoitems:
                if start not in self.lassoitems:
                    self.lassoitems.append(start)
                if end not in self.lassoitems:
                    self.lassoitems.append(end)
            else:
                self.lassoitems = [start,end]
        else:
            nodeid = self.itemToNodeIds[addedid] if addedid in self.itemToNodeIds else None
            if nodeid is not None:
                item.selectgroup()
                if self.lassoitems:
                    if nodeid not in self.lassoitems:
                        self.lassoitems.append(addedid)
                else:
                    self.lassoitems = [addedid]




    def stopregion(self, event):
        if self.lassobox:
            self.delete(self.lassobox)
        if self.lassoitems:
            for item in self.lassoitems:
                if item in self.itemToCanvas:
                    self.itemToCanvas[item].deselectgroup()
            self.lassoitems = None
            return
        x = self.canvasx(event.x)
        y = self.canvasy(event.y)
        items = self.find_enclosed(min(self.region[0], x), min(y, self.region[1]), \
                                   max(self.region[0], x), max(y, self.region[1]))

        self.lassoitems = [item for item in items
                           if item in self.itemToCanvas and isinstance(self.itemToCanvas[item], NodeObj)]
        for item in self.lassoitems:
            if item in self.itemToCanvas:
                self.itemToCanvas[item].selectgroup()

    def deselectCursor(self, event):
        cursor = self.cget("cursor")
        if cursor == 'crosshair':
            self.config(cursor='')
            for k, v in self.itemToCanvas.items():
                v.config(cursor='')

    def onNodeButtonPress(self, event):
        """Being drag of an object"""
        # record the item and its location
        item = self._get_id(event)
        cursor = self.cget("cursor")
        if (item is None):
            self.deselectCursor(None)
            return

        if cursor == 'crosshair':
            nodeId = self.itemToNodeIds[item]
            preds = self.scModel.getGraph().predecessors(nodeId)
            im, filename = self.scModel.getImageAndName(nodeId)
            if filename is None:
                self.itemToNodeIds.pop(item)
                self.clear()
                self.update()
                return
            file_without_path = os.path.split(filename)[1]
            ok = False
            if self.crossHairConnect:
                if nodeId == self.scModel.start:
                    tkMessageBox.showwarning("Error", "Cannot connect to the same node")
                elif len(preds) == 0 or (len(preds) == 1 and self.scModel.isDonorEdge(preds[0], nodeId)):
                    d = DescriptionCaptureDialog(self.master, self.uiProfile,self.scModel,
                                                 self.scModel.getNodeFileType(nodeId), im, file_without_path)
                    if (
                                d.description is not None and d.description.operationName != '' and d.description.operationName is not None):
                        msg, ok = self.scModel.connect(nodeId, mod=d.description)
                        if msg is not None:
                            tkMessageBox.showwarning("Connect Error", msg)
                    else:
                        ok = False
                elif len(preds) == 1:
                    msg, ok = self.scModel.connect(nodeId)
                    if msg is not None:
                        tkMessageBox.showwarning("Connect Error", msg)
                else:
                    tkMessageBox.showwarning("Error", "Destination node already has two predecessors")
            else:
                im1, im2, mask, analysis = self.scModel.compare(nodeId)
                createCompareDialog(self.master, im2, mask, nodeId, analysis, self.scModel.get_dir(),
                                    self.scModel.getLinkType(self.scModel.start, nodeId))
            self.deselectCursor(None)
            if ok:
                self._mark(self._draw_edge(self.scModel.start, self.scModel.end))
                self.callback(event, "n")
            return

        self.setDragData((event.x, event.y), item=item)

    def draw_edge(self,start, end):
        self._mark(self._draw_edge(start, end))

    def setDragData(self, tuple, item=None):
        self.drag_item = item
        self.drag_data = tuple

    def getDragData(self, item, x, y):
        return self.drag_data if self.drag_data else (x, y)

    def showNode(self, node):
        if node not in self.toItemIds:
            return
        item_id = self.toItemIds[node][1]
        self._mark(item_id)
        self.center_on_node(node)

    def showEdge(self, start, end):
        if (start, end) not in self.toItemIds:
            self._mark(self._draw_edge(start, end))
        else:
            self._mark(self.toItemIds[(start, end)][1])
        self.center_on_node(start)

    def onNodeMotion(self, event):
        """Handle dragging of an object"""
        if self.drag_item is None:
            return
        self.moveItem(event, self.drag_item)
        # record the new position
        self.setDragData((event.x, event.y), item=self.drag_item)

    def moveItem(self, event, item):
        # compute how much this object has moved
        xp = event.x
        yp = event.y
        dragInfo = self.getDragData(item, event.x, event.y)
        delta_x = xp - dragInfo[0]
        delta_y = yp - dragInfo[1]

        # move the object the appropriate amount
        self.move(item, delta_x, delta_y)

        # Redraw any edges
        b = self.bbox(item)
        from_xy = ((b[0] + b[2]) / 2, (b[1] + b[3]) / 2)
        from_node = self.itemToNodeIds[item]
        node = self.scModel.getGraph().get_node(from_node)
        if node is None:
            self.remove()
            return
        node['xpos'] = restrictPosition(from_xy[0])
        node['ypos'] = restrictPosition(from_xy[1])
        for n in self.scModel.getGraph().successors(from_node):
            to_xy = self._node_center(n)
            spline_xy = self._spline_center(*from_xy + to_xy + (5,))
            self.coords(self.toItemIds[(from_node, n)][0], (from_xy + spline_xy + to_xy))
            self.coords(self.toItemIds[(from_node, n)][1], spline_xy)

        to_xy = from_xy
        for n in self.scModel.getGraph().predecessors(from_node):
            from_xy = self._node_center(n)
            spline_xy = self._spline_center(*from_xy + to_xy + (5,))
            self.coords(self.toItemIds[(n, from_node)][0], (from_xy + spline_xy + to_xy))
            self.coords(self.toItemIds[(n, from_node)][1], spline_xy)

    def remove(self):
        self._unmark()
        self.scModel.remove()
        self.update()

    def _unmark(self):
        if (self.marked is not None):
            if self.marked in self.itemToCanvas:
                self.itemToCanvas[self.marked].unmark()
            self.marked = None

    def _mark(self, item):
        self._unmark()
        if item in self.itemToCanvas:
            self.itemToCanvas[item].mark()
            self.itemToCanvas[item].selectModel(self.scModel)
        self.callback(None, 'n')
        self.marked = item

    def connectto(self):
        self.selectCursor('connect')

    def compareto(self):
        self.selectCursor('compare')

    def onTokenRightClick(self, event, showMenu=True):
        self._unmark()
        item = self._get_id(event)
        eventname = 'rcNode'
        e = None
        if (item is not None):
            if self.itemToNodeIds.has_key(item):
                self.scModel.selectImage(self.itemToNodeIds[item])
            else:
                e = self.itemToEdgeIds[item]
                if e is not None:
                    self.scModel.selectEdge(e[0], e[1])
                    eventname = 'rcEdge' if self.scModel.isEditableEdge(e[0], e[1]) else 'rcNonEditEdge'
            self._mark(item)
            self.callback(event, eventname if showMenu else 'n')
            if e is not None:
                edge = self.scModel.getGraph().get_edge(e[0], e[1])
                if edge is not None and item in self.itemToCanvas:
                    self.itemToCanvas[item].update(edge)

    def onNodeKey(self, event):
        self._unmark()
        item = self._get_id(event)
        if (item is not None):
            self.scModel.selectImage(self.itemToNodeIds[item])
            self.callback(event, "n")
            self._mark(item)

    def _plot_graph(self):
        # Create nodes
        if (len(self.scModel.getGraph().get_nodes()) == 0):
            return

        scale = min(self.winfo_width(), self.winfo_height())
        if scale == 1:
            # Canvas not initilized yet; use height and width hints
            scale = int(min(self['width'], self['height']))

        for n in self.scModel.getGraph().get_nodes():
            self._draw_node(n)

        # Create edges
        for frm, to in set(self.scModel.getGraph().get_edges()):
            self._draw_edge(frm, to)

    def _spline_center(self, x1, y1, x2, y2, m):
        """Given the coordinate for the end points of a spline, calcuate
        the mipdoint extruded out m pixles"""
        a = (x2 + x1) / 2
        b = (y2 + y1) / 2
        beta = (pi / 2) - atan2((y2 - y1), (x2 - x1))

        xa = a - m * cos(beta)
        ya = b + m * sin(beta)
        return (xa, ya)

    def reformat(self,scale=1.2,min_distance=50):
        from networkx.drawing.nx_agraph import graphviz_layout
        import networkx
        nodes = self.scModel.getGraph().G.nodes()
        baseTuples = self.scModel.getTerminalToBasePairs(suffix=None)
        gg = networkx.nx.DiGraph()
        for n in self.scModel.getGraph().G.nodes():
            gg.add_node(n,file = self.scModel.getGraph().G.node[n]['file'])
        for e in self.scModel.getGraph().G.edges():
            gg.add_edge(e[0],e[1],op=self.scModel.getGraph().G.edge[e[0]][e[1]]['op'])
        positions = graphviz_layout(gg, prog='dot',
                                    root=baseTuples[0][1] if len(baseTuples) > 0 else None)
        xs = [x for (x, y) in positions.values()]
        ys = [y for (x, y) in positions.values()]
        minxs = min(xs)
        minys = min(ys)
        maxxs = max(xs)
        maxys = max(ys)
        width = max(xs) - minxs
        height = max(ys) - minys
        predictedheight = (height / (height + width)) * len(self.scModel.getGraph().get_nodes()) * 50
        predictedwidth = (width / (height + width)) * len(self.scModel.getGraph().get_nodes()) * 50
        for n in self.scModel.getGraph().get_nodes():
            node = self.scModel.getGraph().get_node(n)
            node['xpos']=(maxxs-positions[n][0])*scale + 25
            node['ypos']=(maxys-positions[n][1])*scale + 25
        self.update()

    def _draw_node(self, node_id):
        if node_id in self.toItemIds:
            marker, wid = self.toItemIds[node_id]
            return wid
        wx, wy = self.winfo_width(), self.winfo_height()

        node = self.scModel.getGraph().get_node(node_id)
        if node is None:
            return
        if (node.has_key('xpos')):
            x = node['xpos']
        else:
            x = int(wx / 10)
        if (node.has_key('ypos')):
            y = node['ypos']
        else:
            y = int(wy / 10)

        n = self.scModel.getGraph().get_node(node_id)
        if 'nodetype' not in n:
            self.scModel.labelNodes(node_id)

        nodeC = NodeObj(self, node_id, condenseName(n['file']), n)
        wid = self.create_window(x, y, window=nodeC, anchor=tk.CENTER,
                                 tags='node')
        node['xpos'] = x
        node['ypos'] = y
        self.toItemIds[node_id] = (nodeC.marker, wid)
        self.itemToNodeIds[wid] = node_id
        self.itemToCanvas[wid] = nodeC
        return wid

    def _draw_edge(self, u, v):
        edge = self.scModel.getGraph().get_edge(u, v)
        x1, y1 = self._node_center(u)
        x2, y2 = self._node_center(v)
        xa, ya = self._spline_center(x1, y1, x2, y2, 5)
        lineC = LineTextObj(self, edge, (u, v), (x1, y1, xa, ya, x2, y2))
        wid = self.create_window(xa, ya, window=lineC, anchor=tk.CENTER,
                                 tags='edge')
        self.toItemIds[(u, v)] = (lineC.marker, wid)
        self.itemToEdgeIds[wid] = (u, v)
        self.itemToCanvas[wid] = lineC
        return wid


class NodeObj(tk.Canvas):
    node_name = ''
    marker = None

    def __init__(self, master, node_id, node_name, node):
        tk.Canvas.__init__(self, width=24, height=24, highlightthickness=0)

        self.master = master
        self.node_id = node_id
        self.node_name = node_name
        self.node = node

        self.bind('<ButtonPress-1>', self._host_event('onNodeButtonPress'))
        self.bind('<ButtonRelease-1>', self._host_event('onNodeButtonRelease'))
        self.bind('<B1-Motion>', self._host_event('onNodeMotion'))
        self.bind('<Button-2>' if platform.system() == 'Darwin' else '<Button-3>',
                  self._host_event('onTokenRightClick'))
        self.bind('<Double-Button-1>', self._host_event('onTokenRightClick'))
        self.bind('<Shift-ButtonPress-1>', self.addregion)
        #        self.bind('<Key>', self._host_event('onNodeKey'))
        #        self.bind('<Enter>', lambda e: self.focus_set())
        #        self.bind('<Leave>', lambda e: self.master.focus())

        # Draw myself
        self.render()

    def addregion(self, event):
        self.master.add_selected_item(self)

    def selectModel(self, model):
        model.selectImage(self.node_id)

    def render(self):
        """Draw on canvas what we want node to look like"""
        self.delete(tk.ALL)
        node_text = self.node_name
        if len(node_text) > 20:
            mid = len(node_text) / 2
            node_text = node_text[0:mid] + os.linesep + node_text[mid:]
        self.label = self.create_text(0, 0, text=node_text, font='Times 10 bold')
        self.ismarked = False

        bbox = self.bbox(self.label)
        bbox = [abs(x) for x in bbox]
        br = ((bbox[0] + bbox[2]), (bbox[1] + bbox[3]))

        self.config(width=br[0] + 10, height=br[1] + 20)

        # Place label and marker
        mid = (int(br[0] / 2.0) + 5, int(br[1] / 2.0) + 12)
        self.coords(self.label, mid)

        lowx = mid[0] - 5
        lowy = 0
        highx = mid[0] + 5
        highy = 0
        if self.node['nodetype'] == 'base':
            self.marker = polygon_star(self, lowx + 10, 7, 7, 3, fill='red', outline='black')
        elif self.node['nodetype'] == 'final':
            self.marker = self.create_rectangle(lowx + 0, 0, lowx + 12, 12, fill='red', outline='black')
        else:
            self.marker = self.create_oval(lowx + 0, 0, lowx + 12, 12, fill='red', outline='black')

            # Figure out how big we really need to be

        #        self.coords(self.marker, mid[0]-5,0, mid[0]+5,10)

    def unmark(self):
        self.ismarked = False
        self.itemconfig(self.marker, fill='red')

    def mark(self):
        self.ismarked = True
        self.itemconfig(self.marker, fill='yellow')

    def selectgroup(self):
        self.itemconfig(self.marker, fill='white', dash=4)

    def deselectgroup(self):
        self.itemconfig(self.marker, fill='yellow' if self.ismarked  else 'red', dash=1)

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
            event.item_name = self.node_id
            return func(event)

        return _wrapper


class LineTextObj(tk.Canvas):
    def __init__(self, master, edge, edge_name, coords):
        tk.Canvas.__init__(self, width=20, height=10, highlightthickness=0)

        self.edge = edge
        self.master = master
        self.edge_name = edge_name

        self.bind('<Button-2>' if platform.system() == 'Darwin' else '<Button-3>',
                  self._host_event('onTokenRightClick'))
        self.bind('<Double-Button-1>', self._host_event('onTokenRightClick'))
        self.bind('<Shift-ButtonPress-1>', self.addregion)
        #        self.bind('<Enter>', lambda e: self.focus_set())
        #        self.bind('<Leave>', lambda e: self.master.focus())

        self._render(coords)

    def addregion(self, event):
        self.master.add_selected_item(self)

    def _newcfg(self):
        cfg = {}
        includeInMask = ('recordMaskInComposite' in self.edge and self.edge['recordMaskInComposite'] == 'yes')
        cfg['tags'] = 'edge'
        cfg['smooth'] = True
        cfg['arrow'] = tk.LAST
        cfg['arrowshape'] = (30, 40, 5)
        cfg['width'] = 3
        if not includeInMask:
            cfg['stipple'] = 'gray50'
            cfg['fill'] = 'black'
        else:
            cfg['fill'] = 'blue'
        return cfg

    def selectModel(self, model):
        model.selectEdge(self.edge_name[0],self.edge_name[1])

    def update(self, edge):
        self.edge = edge
        includeInMask = ('recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'yes')
        name = self.edge['op'] + '*' if includeInMask else self.edge['op']
        self.itemconfig(self.label, text=name)

    def _render(self, coords):
        cfg = self._newcfg()
        self.marker = self.master.create_line(*coords, **cfg)
        includeInMask = ('recordMaskInComposite' in self.edge and self.edge['recordMaskInComposite'] == 'yes')
        name = self.edge['op'] + '*' if includeInMask else self.edge['op']
        if len(name) > 25:
            l = len(name) / 2
            pos = 0
            sel = 0
            for c in name:
                if c.isupper():
                    sel = pos
                if pos > l:
                    break
                pos += 1
            name = name[0:sel] + os.linesep + name[sel:]
        self.label = self.create_text(2, 2, text=name, anchor=tk.NW, font='Times 10 bold italic')
        # Figure out how big we really need to be
        bbox = self.bbox(self.label)
        bbox = [abs(x) for x in bbox]
        br = (max((bbox[0] + bbox[2]), 20), max((bbox[1] + bbox[3]), 20))
        self.config(width=br[0] + 10, height=br[1] + 10)

    def unmark(self):
        cfg = self._newcfg()
        #       cfg['fill'] = 'black'
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


def polygon_star(canvas, x, y, p, t, outline="#476042", fill='yellow', width=1):
    points = []
    for i in (1, -1):
        points.extend((x, y + i * p))
        points.extend((x + i * t, y + i * t))
        points.extend((x + i * p, y))
        points.extend((x + i * t, y - i * t))
    return canvas.create_polygon(points, outline=outline,
                                 fill=fill, width=width)

def find_level(graph, node, positions=dict()):
    if node not in positions:
        if len(graph.predecessors()) > 0:
            positions[node] = 0 #9999
            for predecessor in graph.predecessors():
                base = find_level(graph, predecessor, positions) + 1
                if base > positions[node]:
                    positions[node] = base
        else:
            positions[node] = 0
    return positions[node]

def find_max_width(levels):
    count_at_level = {}
    for node,level in levels.iteritems():
        if level in count_at_level:
            count_at_level[level]+=1
        else:
            count_at_level[level]=0
    max_count = 0
    for level, count in count_at_level.iteritems():
        max_count = max(max_count, count)
    return max_count,count_at_level



    # Main path no Donors
    # Final nodes should be deepest
    # If two parents, offset from right most parent
    # If mutiple same row, choose order by distance between parents, tie breakers sorted by length to donor
