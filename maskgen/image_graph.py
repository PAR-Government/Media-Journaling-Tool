import os
import networkx as nx
from networkx.readwrite import json_graph
from image_wrap import deleteImage
import json
import shutil
from software_loader import getOS
import tarfile
from tool_set import *
from time import gmtime, strftime, strptime
import logging
from maskgen import __version__
from threading import RLock

igversion = __version__

def current_version():
    return igversion


def compare_other(old, new):
    return old == new


def compare_str(old, new):
    return old.lower() == new.lower()


def extract_archive(fname, dir):
    try:
        archive = tarfile.open(fname, "r:gz", errorlevel=2)
    except Exception as e:
        try:
            archive = tarfile.open(fname, "r", errorlevel=2)
        except Exception as e:
            if archive is not None:
                archive.close()
            logging.getLogger('maskgen').critical("Cannot open archive {}; it may be corrupted ".format(fname))
            logging.getLogger('maskgen').error(str(e))
            return False

    if not os.path.exists(dir):
        os.mkdir(dir)
    archive.extractall(dir)
    archive.close()

    return True


def buildPath(value, edgePaths):
    r = []
    if type(value) is list:
        for c in range(len(value)):
            iv = value[c]
            if len(edgePaths) == 1:
                r.append('[{1:d}].{0}'.format(edgePaths[0], c))
            else:
                for path in buildPath(iv, edgePaths[1:]):
                    if len(path) > 0:
                        r.append('[{1:d}].{0}.{2}'.format(edgePaths[0], c, path))
                    else:
                        r.append('[{1:d}].{0}'.format(edgePaths[0], c))
        return r
    if type(value) is dict and edgePaths[0] in value:
        if len(edgePaths) == 1:
            return [edgePaths[0]]
        else:
            for path in buildPath(value[edgePaths[0]], edgePaths[1:]):
                r.append(edgePaths[0] + (("." + path) if len(path) > 0 else ''))
            return [x.replace('.[', '[') for x in r]
    return ['']


def extract_and_list_archive(fname, dir):
    try:
        archive = tarfile.open(fname, "r:gz", errorlevel=2)
    except Exception as e:
        try:
            archive = tarfile.open(fname, "r", errorlevel=2)
        except Exception as e:
            logging.getLogger('maskgen').critical("Cannot open archive {}; it may be corrupted ".format(fname))
            logging.getLogger('maskgen').error(str(e))
            return None

    if not os.path.exists(dir):
        os.mkdir(dir)
    archive.extractall(dir)
    l = [x.name for x in archive.getmembers()]
    archive.close()

    return l


def setPathValue(d, path, value):
    pos = path.find('.')
    lbracket = path.find('[')
    listpos = None
    nextpath = path[pos + 1:] if pos > 0 else None
    if lbracket > 0 and (pos < 0 or lbracket < pos):
        rbracket = path.find(']')
        listpos = int(path[lbracket + 1:rbracket])
        pos = lbracket
    if pos < 0:
        if listpos is not None:
            d[path][listpos] = value
        elif value is None:
            d.pop(path)
        else:
            d[path] = value
    elif listpos is not None:
        setPathValue(d[path[0:pos]][listpos], nextpath, value)
    else:
        if path[0:pos] not in d:
            d[path[0:pos]] = {}
        setPathValue(d[path[0:pos]], nextpath, value)


def getPathValues(d, path):
    """
    Given a nest structure,
    return all the values reference by the given path.
    Always returns a list.
    If the value is not found, the list is empty

    NOTE: Processing a list is its own recursion.
    """
    pos = path.find('.')
    currentpath = path[0:pos] if pos > 0 else path
    nextpath = path[pos + 1:] if pos > 0 else None
    lbracket = path.find('[')
    itemnum = None
    if lbracket >= 0 and (pos < 0 or lbracket < pos):
        rbracket = path.find(']')
        itemnum = int(path[lbracket + 1:rbracket])
        currentpath = path[0:lbracket]
        # keep the bracket for the next recurive depth
        nextpath = path[lbracket:] if lbracket > 0 else nextpath
    if type(d) is list:
        result = []
        if itemnum is not None:
            result.extend(getPathValues(d[itemnum], nextpath))
        else:
            for item in d:
                # still on the current path node
                result.extend(getPathValues(item, path))
        return result
    if pos < 0:
        if currentpath == '*':
            result = []
            for k, v in d.iteritems():
                result.append(v)
            return result
        return [d[currentpath]] if currentpath in d and d[currentpath] else []
    else:
        if currentpath == '*':
            result = []
            for k, v in d.iteritems():
                result.extend(getPathValues(v, nextpath))
            return result
        return getPathValues(d[currentpath], nextpath) if currentpath in d else []


def getPathPartAndValue(path, data):
    if path in data:
        return path, data[path]
    pos = path.rfind('.')
    if pos < 0:
        return None, None
    return getPathPartAndValue(path[0:pos], data)


def get_pre_name(file):
    pos = file.rfind('.')
    return file[0:pos] if (pos > 0) else file


def get_suffix(file):
    pos = file.rfind('.')
    return file[pos:] if (pos > 0) else '.json'


def queue_nodes(g, nodes, node, func):
    for s in g.successors(node):
        func(node, s, g.edge[node][s])
        if len(g.predecessors(s)) > 1:
            continue
        queue_nodes(g, nodes, s, func)
        nodes.append(s)
    return nodes


def remove_edges(g, nodes, node, func):
    for s in g.successors(node):
        func(node, s, g.edge[node][s])
    return nodes


def loadJSONGraph(pathname):
    with open(pathname, "r") as f:
        try:
            return json_graph.node_link_graph(json.load(f, encoding='utf-8'), multigraph=False, directed=True)
        except  ValueError as ve:
            logging.getLogger('maskgen').critical("Cannot open project {}; it may be corrupted ".format(pathname))
            logging.getLogger('maskgen').error(str(ve))
            return json_graph.node_link_graph(json.load(f), multigraph=False, directed=True)


def find_project_json(prefix, directory):
    """
    Finds all project .json file in the given directory whose subdirectory starts with prefix
    :param prefix subdirectory name begins with prefix
    :return: JSON file path name for a project
    """
    ext = '.json'
    subs = [os.path.join(directory, x) for x in os.listdir(directory) if x.startswith(prefix) and
            os.path.isdir(os.path.join(directory, x))]

    for sub in subs:
        files = []
        for f in os.listdir(sub):
            if f.endswith(ext):
                files.append(f)
        if len(files) > 0:
            sizes = [os.stat(os.path.join(sub, pick)).st_size for pick in files]
            max_size = max(sizes)
            index = sizes.index(max_size)
            return os.path.join(sub, files[index])
    return None


def createGraph(pathname, projecttype=None, nodeFilePaths={}, edgeFilePaths={}, arg_checker_callback=None):
    """
      Factory for an Project Graph, existing or new.
      Supports a tgz of a project or the .json of a project
    """
    G = None
    if (os.path.exists(pathname) and pathname.endswith('.json')):
        G = loadJSONGraph(pathname)
        projecttype = G.graph['projecttype'] if 'projecttype' in G.graph else projecttype
    if (os.path.exists(pathname) and pathname.endswith('.tgz')):
        dir = os.path.split(os.path.abspath(pathname))[0]
        elements = extract_and_list_archive(pathname, dir)
        if elements is not None and len(elements) > 0:
            picks = [el for el in elements if el.endswith('.json')]
            sizes = [os.stat(os.path.join(dir, pick)).st_size for pick in picks]
            max_size = max(sizes)
            index = sizes.index(max_size)
            pathname = os.path.join(dir, picks[index])
        else:
            pathname = find_project_json(os.path.split(pathname[0:pathname.rfind('.')])[1], dir)
        G = loadJSONGraph(pathname)
        projecttype = G.graph['projecttype'] if 'projecttype' in G.graph else projecttype

    return ImageGraph(pathname,
                      graph=G,
                      projecttype=projecttype,
                      arg_checker_callback=arg_checker_callback,
                      nodeFilePaths=nodeFilePaths,
                      edgeFilePaths=edgeFilePaths)


class ImageGraph:
    dir = os.path.abspath('.')


    def getUIGraph(self):
        return self.G

    def get_name(self):
        return self.G.name

    def __init__(self, pathname, graph=None, projecttype=None, nodeFilePaths={}, edgeFilePaths={},
                 arg_checker_callback=None):
        fname = os.path.split(pathname)[1]
        self.filesToRemove = set()
        self.U = list()
        self.lock = RLock()
        name = get_pre_name(fname)
        self.dir = os.path.abspath('.')
        self.idc = 0
        self.arg_checker_callback = arg_checker_callback
        self.G = graph if graph is not None else nx.DiGraph(name=name)
        self._setup(pathname, projecttype, nodeFilePaths, edgeFilePaths)

    def addEdgeFilePath(self, path, ownership):
        """
        :param path: the edge propertes path to a filename
                This is not a file path name.  Instead, this is a path
                through the key's of the edge dictionary leading up to the
                nested dictionary key that references a file name
        :param ownership: an attribute in the edge that informs
                the ImageGraph if the file should be removed if
                the path is changed/removed from the edge.
        :return: None
        """
        self.G.graph['edgeFilePaths'][path] = ownership

    def addNodeFilePath(self, path, ownership):
        """
        :param path: the node propertes path to a filename
               This is not a file path name.  Instead, this is a path
               through the key's of the node dictionary leading up to the
                nested dictionary key that references a file name
        :param ownership: an attribute in the node that informs
               the ImageGraph if the file should be removed if
               the path is changed/removed from the edge.
        :return: None
        """
        self.G.graph['nodeFilePaths'][path] = ownership

    def openImage(self, fileName, mask=False, metadata={}):
        imgDir = os.path.split(os.path.abspath(fileName))[0]
        return openImage(fileName,
                         videoFrameTime=None if 'Frame Time' not in metadata else getMilliSecondsAndFrameCount(
                             metadata['Frame Time']),
                         isMask=mask,
                         preserveSnapshot=(imgDir == os.path.abspath(self.dir) and \
                                           ('skipSnapshot' not in metadata or not metadata['skipSnapshot'])))

    def replace_attribute_value(self, attributename, oldvalue, newvalue):
        self._setUpdate(attributename, update_type='attribute')
        found = False
        strcompare = type(oldvalue) == type(newvalue) and type(oldvalue) is str
        comparefunc = compare_str if strcompare else compare_other
        if attributename in self.G.graph and comparefunc(self.G.graph[attributename], oldvalue):
            self.G.graph[attributename] = newvalue
            found = True
        for n in self.G.nodes():
            if attributename in self.G.node[n] and comparefunc(self.G.node[n][attributename], oldvalue):
                self.G.node[n][attributename] = newvalue
                found = True
        for e in self.G.edges():
            if attributename in self.G.edge[e[0]][e[1]] and comparefunc(self.G.edge[e[0]][e[1]][attributename],
                                                                        oldvalue):
                self.G.edge[e[0]][e[1]][attributename] = newvalue
                found = True
        return found

    def get_nodes(self):
        return self.G.nodes()

    def get_project_type(self):
        return self.G.graph['projecttype'] if 'projecttype' in self.G.graph else None


    def set_project_type(self,projecttype):
        self.G.graph['projecttype'] = projecttype

    def get_pathname(self, name):
        return os.path.join(self.dir, self.G.node[name]['file'])

    def get_edges(self):
        return self.G.edges()

    def new_name(self, fname, suffix=None):
        if suffix is None:
            suffix = get_suffix(fname)
        origname = nname = get_pre_name(fname)
        self._setUpdate(nname, update_type='node')
        while (self.G.has_node(nname)):
            posUS = origname.rfind('_')
            if posUS > 0 and origname[posUS + 1:].isdigit():
                nname = '{}_{:=02d}'.format(origname[:posUS], self.nextId())
            else:
                nname = '{}_{:=02d}'.format(origname, self.nextId())
        fname = nname + suffix
        return fname

    def __filter_args(self, args, exclude=[]):
        result = {}
        for k, v in args.iteritems():
            if v is not None and k not in exclude:
                result[k] = v
        return result

    def __scan_args(self, op, args):
        if self.arg_checker_callback is None:
            return
        self.arg_checker_callback(op, args)

    def add_node(self, pathname, nodeid=None, seriesname=None, **kwargs):
        proxypathname = getProxy(pathname)
        fname = os.path.split(pathname)[1]
        origdir = os.path.split(os.path.abspath(pathname))[0]
        filetype = fileType(pathname)
        origname = get_pre_name(fname)
        suffix = get_suffix(fname)
        newfname = self.new_name(fname, suffix.lower())
        nname = get_pre_name(newfname)
        if nodeid is not None:
            nname = nodeid
        oldpathname = os.path.join(self.dir, fname)
        if os.path.abspath(self.dir) != origdir and os.path.exists(oldpathname):
            fname = newfname
        elif suffix != suffix.lower():
            fname = origname + suffix.lower()
        newpathname = os.path.join(self.dir, fname)
        includePathInUndo = (newpathname in self.filesToRemove)
        if (not os.path.exists(newpathname)):
            includePathInUndo = True
            if (os.path.exists(pathname)):
                shutil.copy2(pathname, newpathname)
        self._setUpdate(nname, update_type='node')
        with self.lock:
            self.G.add_node(nname,
                            seriesname=(origname if seriesname is None else seriesname),
                            file=fname,
                            ownership=('yes' if includePathInUndo else 'no'),
                            username=get_username(),
                            filetype=filetype,
                            ctime=datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'),
                            **self.__filter_args(kwargs, exclude=['filetype', 'seriesname', 'username', 'ctime', 'ownership', 'file']))

            self.__scan_args('node', kwargs)

            if proxypathname is not None:
                self.G.node[nname]['proxyfile'] = proxypathname

            self.U = []
            self.U.append(dict(name=nname, action='addNode', **self.G.node[nname]))
            # adding back a file that was targeted for removal
            if newpathname in self.filesToRemove:
                self.filesToRemove.remove(newpathname)
            for path, ownership in self.G.graph['nodeFilePaths'].iteritems():
                vals = getPathValues(kwargs, path)
                if len(vals) > 0:
                    pathvalue, ownershipvalue = self._handle_inputfile(vals[0])
                    if vals[0]:
                        kwargs[path] = pathvalue
                        if len(ownership) > 0:
                            kwargs[ownership] = ownershipvalue
        return nname

    def undo(self):
        for d in list(self.U):
            action = d.pop('action')
            if action == 'removeNode':
                k = os.path.join(self.dir, d['file'])
                if k in self.filesToRemove:
                    self.filesToRemove.remove(k)
                for path, ownership in self.G.graph['nodeFilePaths'].iteritems():
                    for value in getPathValues(d, path):
                        filePath = os.path.join(self.dir, value)
                        if filePath in self.filesToRemove:
                            self.filesToRemove.remove(filePath)
                name = d.pop('name')
                self.G.add_node(name, **d)
            elif action == 'removeEdge':
                for path, ownership in self.G.graph['edgeFilePaths'].iteritems():
                    for value in getPathValues(d, path):
                        filePath = os.path.join(self.dir, value)
                        if filePath in self.filesToRemove:
                            self.filesToRemove.remove(filePath)
                start = d.pop('start')
                end = d.pop('end')
                self.G.add_edge(start, end, **d)
            elif action == 'addNode':
                if (d['ownership'] == 'yes'):
                    if os.path.exists(os.path.join(self.dir, d['file'])):
                        os.remove(os.path.join(self.dir, d['file']))
                self.G.remove_node(d['name'])
            elif action == 'addEdge':
                self.remove_edge(d['start'], d['end'])
        self.U = []

    def get_edge_image(self, start, end, path, returnNoneOnMissing=False):
        """
        Get image name and file name for image given edge identified by start and end and the edge property path
        :param start:
        :param end:
        :param path:
        :return:
        @type start: str
        @type end: str
        @type path: str
        @rtype (ImageWrapper, str)
        """
        edge = self.get_edge(start, end)
        values = getPathValues(edge, path)
        if len(values) > 0:
            value = values[0]
            fullpath = os.path.abspath(os.path.join(self.dir, value))
            if returnNoneOnMissing and not os.path.exists(fullpath):
                return None, None
            im = self.openImage(fullpath, mask=True)
            return im
        return None

    def getNodeFileType(self, nodeid):
        node = self.get_node(nodeid)
        if node is not None and 'filetype' in node:
            return node['filetype']
        else:
            return fileType(self.get_image_path(nodeid))

    def set_name(self, name):
        currentjsonfile = os.path.abspath(os.path.join(self.dir, self.G.name + '.json'))
        self.G.name = name
        newjsonfile = os.path.abspath(os.path.join(self.dir, self.G.name + '.json'))
        os.rename(currentjsonfile, newjsonfile)

    def update_node(self, node, **kwargs):
        self._setUpdate(node, update_type='node')
        if self.G.has_node(node):
            self.__scan_args('node', kwargs)
            for k, v in kwargs.iteritems():
                self.G.node[node][k] = v

    def update_edge(self, start, end, **kwargs):
        if start is None or end is None:
            return
        if not self.G.has_node(start) or not self.G.has_node(end):
            return
        self._setUpdate((start, end), update_type='edge')
        op = kwargs['op'] if 'op' in kwargs else self.G.edge[start][end]['op']
        self.__scan_args(op, kwargs)
        unsetkeys = []
        for k, v in kwargs.iteritems():
            if v is not None:
                self._updateEdgePathValue(self.G[start][end], k, v)
            else:
                unsetkeys.append(k)
        for k in unsetkeys:
            if k in self.G[start][end]:
                self.G[start][end].pop(k)

    def _handle_inputfile(self, inputfile):
        """
         Input files may need to be copied to the working project directory
        """
        includePathInUndo = False
        if inputfile is None or len(inputfile) == 0:
            return '', 'no'
        filename = os.path.split(inputfile)[1]
        newpathname = os.path.join(self.dir, filename)
        # already slated for removal
        includePathInUndo = (newpathname in self.filesToRemove)
        if not os.path.exists(newpathname):
            includePathInUndo = True
            if os.path.exists(inputfile):
                shutil.copy2(inputfile, newpathname)
            if newpathname in self.filesToRemove:
                self.filesToRemove.remove(newpathname)
        if not os.path.exists(newpathname):
            return None, None
        return filename, 'yes' if includePathInUndo else 'no'

    def update_mask(self, start, end, mask=None, maskname=None, errors=None,  **kwargs):
            self._setUpdate((start, end), update_type='edge')
            edge = self.get_edge(start,end)
            if mask is not None:
                oldmaskname =  edge['maskname'] if 'maskname' in edge else \
                    (kwargs['maskname'] if 'maskname' in kwargs else None)
                if oldmaskname is not None:
                    newmaskpathname = os.path.join(self.dir, oldmaskname)
                    mask.save(newmaskpathname)
                else:
                    newmaskpathname = os.path.join(self.dir, maskname)
                    mask.save(newmaskpathname)
                    edge['maskname'] = maskname
            elif  'maskname' in edge:
                    edge.pop('maskname')
            with self.lock:
                if errors is not None:
                    edge['errors'] = errors
                for k, v in kwargs.iteritems():
                    if k == 'maskname' and mask is None:
                        continue
                    if v is None and k in edge:
                        edge.pop(k)
                    edge[k] = v

    def copy_edge(self, start, end, dir='.', edge=dict()):
        import copy
        self._setUpdate((start, end), update_type='edge')
        edge = copy.deepcopy(edge)
        if 'maskname' in edge:
            newmaskpathname = os.path.join(self.dir, edge['maskname'])
            if os.path.exists(newmaskpathname):
                newmaskpathname = newmaskpathname[0:-4] + '_{:=02d}'.format(self.nextId()) + newmaskpathname[-4:]
            shutil.copy(os.path.join(dir, edge['maskname']), newmaskpathname)
            edge['maskname'] = os.path.split(newmaskpathname)[1]
        for k, v in edge.iteritems():
            if v is not None:
                self._copyEdgePathValue(edge, k, v, dir)
        self.G.add_edge(start,
                        end,
                        **edge)
        self.U = []
        self.U.append(dict(action='addEdge', start=start, end=end, **self.G.edge[start][end]))

    def add_edge(self, start, end, maskname=None, mask=None, op='Change', description='', **kwargs):
        import copy
        self._setUpdate((start, end), update_type='edge')
        self.__scan_args(op, kwargs)
        newmaskpathname = None
        if maskname is not None and len(maskname) > 0 and mask is not None:
            newmaskpathname = os.path.join(self.dir, maskname)
            mask.save(newmaskpathname)
        else:
            maskname = None
        for k, v in copy.deepcopy(kwargs).iteritems():
            if v is not None:
                self._updateEdgePathValue(kwargs, k, v)
        # do not remove old version of mask if not saved previously
        if newmaskpathname in self.filesToRemove:
            self.filesToRemove.remove(newmaskpathname)
        kwargs = {k: v for k, v in kwargs.iteritems() if v is not None}
        with self.lock:
            self.G.add_edge(start,
                            end,
                            maskname=maskname,
                            op=op,
                            ctime=datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S'),
                            description=description, username=get_username(), opsys=getOS(),
                            **kwargs)
            self.U = []
            self.U.append(dict(action='addEdge', start=start, end=end, **self.G.edge[start][end]))
        return mask

    def get_masks(self, name, maskname):
        result = {}
        if name in self.G.nodes() and maskname in self.G.node[name]:
            item = self.G.node[name][maskname]
            if type(item) != dict:
                filename = os.path.abspath(os.path.join(self.dir, self.G.node[name][maskname]))
                im = self.openImage(filename, mask=False)
                result[name] = (im, filename)
            else:
                for base, fname in self.G.node[name][maskname].iteritems():
                    filename = os.path.abspath(os.path.join(self.dir, fname))
                    im = self.openImage(filename, mask=True)
                    result[base] = (im, filename)
        return result

    def has_mask(self, name, maskname):
        return name in self.G.nodes() and maskname in self.G.node[name]

    def get_image(self, name, metadata=dict()):
        """
        :param name:
        :param metadata:
        :return:
        @rtype (ImageWrapper,str)
        """
        if not self.G.has_node(name):
            return None, None
        node = self.G.node[name]
        filename = os.path.abspath(os.path.join(self.dir, node['file']))
        proxy = getProxy(filename)
        if proxy and 'proxyfile' not in node:
            # do not assume the proxy will be open but make sure
            # it is preserved, since it may have been added after
            # the node was added to the project
            node['proxyfile'] = os.path.split(proxy)[1]
        im = self.openImage(filename, metadata=metadata)
        return im, filename

    def get_image_path(self, name):
        return os.path.abspath(os.path.join(self.dir, self.G.node[name]['file']))

    def get_edge(self, start, end):
        return self.G[start][end] if (self.G.has_edge(start, end)) else None

    def _edgeFileRemover(self, actionList, edgeFunc, start, end, edge):
        """
          Remove an edge and all owned files
        """
        if edgeFunc is not None:
            edgeFunc(edge)
        for path, ownership in self.G.graph['edgeFilePaths'].iteritems():
            for pathvalue in getPathValues(edge, path):
                if pathvalue and len(pathvalue) > 0 and (ownership not in edge or edge[ownership] == 'yes'):
                    f = os.path.abspath(os.path.join(self.dir, pathvalue))
                    if (os.path.exists(f)):
                        self.filesToRemove.add(f)
                        deleteImage(f)
        actionList.append(dict(start=start, end=end, action='removeEdge', **self.G.edge[start][end]))

    def _nodeFileRemover(self, name):
        """
          Remove an node and all owned files
        """
        node = self.G.node[name]
        f = os.path.abspath(os.path.join(self.dir, self.G.node[name]['file']))
        if (node['ownership'] == 'yes' and os.path.exists(f)):
            self.filesToRemove.add(f)
            deleteImage(f)

        for path, ownership in self.G.graph['nodeFilePaths'].iteritems():
            for pathvalue in getPathValues(node, path):
                if pathvalue and len(pathvalue) > 0 and (ownership not in node or node[ownership] == 'yes'):
                    f = os.path.abspath(os.path.join(self.dir, pathvalue))
                    if (os.path.exists(f)):
                        self.filesToRemove.add(f)
                        deleteImage(f)
        self.U.append(dict(name=name, action='removeNode', **self.G.node[name]))
        self.G.remove_node(name)

    def remove(self, node, edgeFunc=None, children=False):
        with self.lock:
            self.U = []
            self.E = []

            self._setUpdate(node, update_type='node')

            def fileRemover(start, end, edge):
                self._edgeFileRemover(self.E, edgeFunc, start, end, edge)

            # remove predecessor edges
            for p in self.G.predecessors(node):
                fileRemover(p, node, self.G.edge[p][node])
            # remove edges or deep dive removal
            nodes_to_remove = queue_nodes(self.G, [node], node, fileRemover) if children else \
                remove_edges(self.G, [node], node, fileRemover)
            for n in nodes_to_remove:
                if (self.G.has_node(n)):
                    self._nodeFileRemover(n)

            # edges always added after nodes to the undo list
            for e in self.E:
                self.U.append(e)
            self.E = []

    def findRelationsToNode(self, node):
        nodeSet = set()
        nodeSet.add(node)
        q = set(self.G.successors(node))
        q = q | set(self.G.predecessors(node))
        while len(q) > 0:
            n = q.pop()
            if n not in nodeSet:
                nodeSet.add(n)
                q = q | set(self.G.successors(n))
                q = q | set(self.G.predecessors(n))
        return nodeSet

    def remove_edge(self, start, end, edgeFunc=None):
        self._setUpdate((start, end), update_type='edge')
        self.U = []
        edge = self.G.edge[start][end]
        self._edgeFileRemover(self.U, edgeFunc, start, end, edge)
        self.G.remove_edge(start, end)

    def has_neighbors(self, node):
        return len(self.G.predecessors(node)) + len(self.G.successors(node)) > 0

    def predecessors(self, node):
        return self.G.predecessors(node) if self.G.has_node(node) else []

    def successors(self, node):
        return self.G.successors(node) if self.G.has_node(node) else []

    def has_edge(self,start,end):
        return self.get_edge(start,end) != None

    def has_node(self, name):
        return self.G.has_node(name)

    def getDataItem(self, item, default_value=None):
        return self.G.graph[item] if item in self.G.graph else default_value

    def setDataItem(self, item, value, excludeUpdate=False):
        localExclude = item in self.G.graph and value == self.G.graph[item]
        if not (excludeUpdate or localExclude):
            self._setUpdate(item, update_type='graph')
        self.G.graph[item] = value

    def getMetadata(self):
        return self.G.graph

    def get_node(self, name):
        if self.G.has_node(name):
            return self.G.node[name]
        else:
            return None

    def getProjectVersion(self):
        return self.G.graph['igversion'] if 'igversion' in self.G.graph else ''

    def subgraph(self, nodes):
        return ImageGraph(os.path.join(self.dir,self.get_name() + '_sub'),
                   graph=nx.DiGraph(self.G.subgraph(nodes)),
                   projecttype=self.get_project_type())

    def getVersion(self):
        return igversion

    def getCreator(self):
        return self.G.graph['creator'] if 'creator' in self.G.graph else get_username()

    def findAncestor(self,match, start):
        for pred in self.predecessors(start):
            command = match(pred, start, self.G.get_edge_data(pred,start))
            if command == 'return':
                return self.G.get_edge_data(pred,start)
            elif command != 'skip':
                ret = self.findAncestor(match, pred)
                if ret is not None:
                    return ret
        return None

    def _setup(self, pathname, projecttype, nodeFilePaths, edgeFilePaths):
        global igversion
        import logging
        logging.getLogger('maskgen').info("Opening Journal {} with JT version {}".format(
            os.path.split(pathname)[1], igversion))
        if 'igversion' not in self.G.graph:
            self.G.graph['igversion'] = igversion
        versionlen = min(8, len(self.G.graph['igversion']))
        if self.G.graph['igversion'][0:versionlen] > igversion[0:versionlen] and self.G.graph['igversion'][1] == '.':
            logging.getLogger('maskgen').error('UPGRADE JOURNALING TOOL!')
        if 'idcount' in self.G.graph:
            self.idc = self.G.graph['idcount']
        elif self.G.has_node('idcount'):
            self.idc = self.G.node['idcount']['count']
            self.G.graph['idcount'] = self.idc
            self.G.remove_node('idcount')
        self.dir = os.path.abspath(os.path.split(pathname)[0])
        if 'username' not in self.G.graph:
            self.G.graph['username'] = get_username()
        if 'creator' not in self.G.graph:
            self.G.graph['creator'] = get_username()
        if 'projecttype' not in self.G.graph and projecttype is not None:
            self.G.graph['projecttype'] = projecttype
        if 'updatetime' not in self.G.graph:
            if 'exporttime' in self.G.graph:
                self.G.graph['updatetime'] = self.G.graph['exporttime']
            else:
                self._setUpdate('project')
        # edgeFilePaths are paths to files that are managed by the graph
        # so that the paths are both archived and removed if deleted
        if 'edgeFilePaths' not in self.G.graph:
            self.G.graph['edgeFilePaths'] = {'maskname': ''}
        # nodeFilePaths are paths to files that are managed by the graph
        # so that the paths are both archived and removed if deleted
        if 'nodeFilePaths' not in self.G.graph:
            self.G.graph['nodeFilePaths'] = {'proxyfile': ''}
        for k, v in edgeFilePaths.iteritems():
            self.G.graph['edgeFilePaths'][k] = v
        for k, v in nodeFilePaths.iteritems():
            self.G.graph['nodeFilePaths'][k] = v

    def getCycleNode(self):
        l = list(nx.simple_cycles(self.G))
        if len(l) > 0:
            return l[0]

    def saveas(self, pathname):
        currentdir = self.dir
        fname = os.path.split(pathname)[1]
        name = get_pre_name(fname)
        if os.path.isdir(pathname):
            self.dir = pathname
        else:
            self.dir = os.path.join(os.path.abspath(os.path.split(pathname)[0]), name)
            os.mkdir(self.dir)
        self.G.name = name
        filename = os.path.abspath(os.path.join(self.dir, self.G.name + '.json'))
        self._copy_contents(currentdir)
        with open(filename, 'w') as f:
            jg = json.dump(json_graph.node_link_data(self.G), f, indent=2, encoding='utf-8')
        self.filesToRemove.clear()

    def save(self):
        filename = os.path.abspath(os.path.join(self.dir, self.G.name + '.json'))
        backup = filename + '.bak'
        if os.path.exists(filename):
            shutil.copy(filename, backup)
        with self.lock:
            with open(filename, 'w') as f:
                jg = json.dump(json_graph.node_link_data(self.G), f, indent=2, encoding='utf-8')
            for f in self.filesToRemove:
                if os.path.exists(f):
                    os.remove(f)
            self.filesToRemove.clear()

    def nextId(self):
        with self.lock:
            self.idc += 1
            self.G.graph['idcount'] = self.idc
            return self.idc

    def _copy_contents(self, currentdir):
        def moveFile(newdir, currentdir, name):
            oldpathname = os.path.join(currentdir, name)
            newpathname = os.path.join(newdir, name)
            if (os.path.exists(oldpathname)):
                shutil.copy2(oldpathname, newpathname)

        for nname in self.G.nodes():
            node = self.G.node[nname]
            moveFile(self.dir, currentdir, node['file'])
            for path, ownership in self.G.graph['nodeFilePaths'].iteritems():
                for pathvalue in getPathValues(node, path):
                    if not pathvalue or len(pathvalue) == 0:
                        continue
                    if len(ownership) > 0:
                        node[ownership] = 'yes'
                    moveFile(self.dir, currentdir, pathvalue)

        for edgename in self.G.edges():
            edge = self.G[edgename[0]][edgename[1]]
            for path, ownership in self.G.graph['edgeFilePaths'].iteritems():
                for pathvalue in getPathValues(edge, path):
                    if not pathvalue or len(pathvalue) == 0:
                        continue
                    if len(ownership) > 0:
                        edge[ownership] = 'yes'
                    moveFile(self.dir, currentdir, pathvalue)

    def file_check(self):
        missing = []
        for nname in self.G.nodes():
            node = self.G.node[nname]
            if not os.path.exists(os.path.join(self.dir, node['file'])):
                missing.append((str(nname), str(nname), str(nname) + ' is missing image file in project'))
            for path, ownership in self.G.graph['nodeFilePaths'].iteritems():
                for pathvalue in getPathValues(node, path):
                    if not pathvalue or len(pathvalue) == 0:
                        continue
                    if not os.path.exists(os.path.join(self.dir, pathvalue)):
                        missing.append(
                            (str(nname), str(nname), str(nname) + ' is missing ' + path + ' file in project'))
        for edgename in self.G.edges():
            edge = self.G[edgename[0]][edgename[1]]
            for path, ownership in self.G.graph['edgeFilePaths'].iteritems():
                for pathvalue in getPathValues(edge, path):
                    if not pathvalue or len(pathvalue) == 0:
                        continue
                    if not os.path.exists(os.path.join(self.dir, pathvalue)):
                        missing.append((str(edgename[0]), str(edgename[1]), str(edgename[0]) + ' => ' + str(
                            edgename[1]) + ' is missing ' + path + ' file in project'))
        return missing

    def create_archive(self, location, include=[]):
        self.G.graph['exporttime'] = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        fname, errors, names_added = self._create_archive(location, include=include)
        names_added = [os.path.split(i)[1] for i in names_added]
        tries = 0
        if len(errors) == 0:
            while not self._check_archive_integrity(fname, names_added) and tries < 3:
                fname, errors, names_added = self._create_archive(location)
                tries += 1
        return fname, ([('', '', "Failed to create archive")] if (tries == 3 and len(errors) == 0) else errors)

    def _check_archive_integrity(self, fname, names_added):
        try:
            archive = tarfile.open(fname, "r:gz", errorlevel=2)
            #         archive = ZipFile(fname,"r")
            names_removed = [os.path.split(i)[1] for i in archive.getnames()]
            for i in names_removed:
                if unicode(i) in names_added:
                    names_added.remove(unicode(i))
            archive.close()
            if len(names_added) > 0:
                return False
        except Exception as e:
            logging.getLogger('maskgen').critical("Integrity checked failed fo archive {} ".format(fname))
            logging.getLogger('maskgen').error(str(e))
            return False
        return True

    def _archive_node(self, nname, archive, names_added=list()):
        node = self.G.node[nname]
        errors = list()
        if os.path.exists(os.path.join(self.dir, node['file'])):
            archive.add(os.path.join(self.dir, node['file']), arcname=os.path.join(self.G.name, node['file']))
            names_added.append(os.path.join(self.G.name, node['file']))
        else:
            errors.append((str(nname), str(nname), str(nname) + " missing file"))
        for path, ownership in self.G.graph['nodeFilePaths'].iteritems():
            for pathvalue in getPathValues(node, path):
                if not pathvalue or len(pathvalue) == 0:
                    continue
                newpathname = os.path.join(self.dir, pathvalue)
                if os.path.exists(newpathname):
                    archive.add(newpathname, arcname=os.path.join(self.G.name, pathvalue))
                    names_added.append(os.path.join(self.G.name, pathvalue))
                else:
                    errors.append(
                        (str(nname), str(nname), str(nname) + ' missing ' + pathvalue))
        return errors

    def _output_summary(self, archive, options={}):
        """
        Add a summary PNG to the archicve
        :param archive: TarFile
        :return: None
        @type archive : TarFile
        """
        from graph_output import ImageGraphPainter
        summary_file = os.path.join(self.dir, '_overview_.png')
        try:
            ImageGraphPainter(self).output(summary_file, options=options)
            archive.add(summary_file,
                        arcname=os.path.join(self.G.name, '_overview_.png'))
        except Exception as e:
            logging.getLogger('maskgen').error("Unable to create image graph: " + str(e))

    def _create_archive(self, location, include=[]):
        self.save()
        fname = os.path.join(location, self.G.name + '.tgz')
        archive = tarfile.open(fname, "w:gz", errorlevel=2)
        archive.add(os.path.join(self.dir, self.G.name + ".json"),
                    arcname=os.path.join(self.G.name, self.G.name + ".json"))
        errors = list()
        names_added = list()
        for nname in self.G.nodes():
            self._archive_node(nname, archive, names_added=names_added)
        for edgename in self.G.edges():
            edge = self.G[edgename[0]][edgename[1]]
            errors.extend(
                self._archive_edge(edgename[0], edgename[1], edge, self.G.name, archive, names_added=names_added))
        for item in include:
            archive.add(os.path.join(self.dir, item),
                        arcname=item)
        self._output_summary(archive)
        archive.close()
        return fname, errors, names_added

    def _archive_edge(self, start, end, edge, archive_name, archive, names_added=list()):
        errors = []
        for path, ownership in self.G.graph['edgeFilePaths'].iteritems():
            for pathvalue in getPathValues(edge, path):
                if not pathvalue or len(pathvalue) == 0:
                    continue
                newpathname = os.path.join(self.dir, pathvalue)
                if os.path.exists(newpathname):
                    archive.add(newpathname, arcname=os.path.join(archive_name, pathvalue))
                    names_added.append(os.path.join(archive_name, pathvalue))
                else:
                    errors.append(
                        (str(start), str(end), str(start) + ' => ' + str(end) + ': ' + ' missing ' + pathvalue))
        return errors

    def _archive_path(self, child, archive_name, archive, pathGraph, names_added=list()):
        node = self.G.node[child]
        pathGraph.add_node(child, **node)
        self._archive_node(child, archive, names_added=names_added)
        errors = []
        for parent in self.G.predecessors(child):
            errors.extend(self._archive_edge(self.G[parent][child], archive_name, archive, names_added=names_added))
            pathGraph.add_edge(parent, child, **self.G[parent][child])
            errors.extend(self._archive_path(parent, archive_name, archive, pathGraph, names_added=names_added))
        return errors

    def getLastUpdateTime(self):
        return strptime(self.G.graph['updatetime'], "%Y-%m-%d %H:%M:%S")

    def _setUpdate(self, name, update_type=None):
        self.G.graph['updatetime'] = strftime("%Y-%m-%d %H:%M:%S", gmtime())
        self.G.graph['igversion'] = igversion

    def _buildStructure(self, path, value):
        pos = path.find('.')
        if pos > 0:
            if path[0:pos] in value:
                return {path[0:pos]: self._buildStructure(path[pos + 1:], value)}
            return {}
        return {path: value}

    def _matchPath(self, path, pathTemplate):
        pos = path.find('[')
        while pos > 0:
            end = path.find(']')
            path = path[0:pos] + path[end + 1:]
            pos = path.find('[')
        return path == pathTemplate

    def _copyEdgePathValue(self, edge, path, value, dir):
        setPathValue(edge, path, value)
        for edgePath in self.G.graph['edgeFilePaths']:
            struct = self._buildStructure(path, value)
            for revisedPath in buildPath(struct, edgePath.split('.')):
                if self._matchPath(revisedPath, edgePath):
                    ownershippath = self.G.graph['edgeFilePaths'][edgePath]
                    for pathValue in getPathValues(struct, revisedPath):
                        filenamevalue, ownershipvalue = self._handle_inputfile(os.path.join(dir, pathValue))
                        setPathValue(edge, revisedPath, filenamevalue)
                        if len(ownershippath) > 0:
                            setPathValue(edge, ownershippath, ownershipvalue)

    def _updateEdgePathValue(self, edge, path, value):
        setPathValue(edge, path, value)
        for edgePath in self.G.graph['edgeFilePaths']:
            struct = self._buildStructure(path, value)
            for revisedPath in buildPath(struct, edgePath.split('.')):
                if self._matchPath(revisedPath, edgePath):
                    ownershippath = self.G.graph['edgeFilePaths'][edgePath]
                    for pathValue in getPathValues(struct, revisedPath):
                        filenamevalue, ownershipvalue = self._handle_inputfile(pathValue)
                        setPathValue(edge, revisedPath, filenamevalue)
                        if len(ownershippath) > 0:
                            setPathValue(edge, ownershippath, ownershipvalue)

    def create_path_archive(self, location, end):
        self.save()
        names_added = list()
        if end in self.G.nodes():
            node = self.G.node[end]
            archive_name = node['file'].replace('.', '_')
            archive = tarfile.open(os.path.join(location, archive_name + '.tgz'), "w:gz")
            pathGraph = nx.DiGraph(name="Empty")
            errors = self._archive_path(end, archive_name, archive, pathGraph, names_added=list())
            filename = os.path.abspath(os.path.join(self.dir, archive_name + '.json'))
            names_added.append(filename)

            old = None
            if os.path.exists(filename):
                old = 'backup.json'
                shutil.copy2(filename, old)

            with open(filename, 'w') as f:
                jg = json.dump(json_graph.node_link_data(pathGraph), f, indent=2)
            archive.add(filename, arcname=os.path.join(archive_name, archive_name + '.json'))
            archive.close()
            if old is not None:
                shutil.copy2(old, filename)
            elif os.path.exists(filename):
                os.remove(filename)
            return errors
