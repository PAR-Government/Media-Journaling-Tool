import json
import networkx as nx
import argparse
import sys
from networkx.readwrite import json_graph
import os
from maskgen import software_loader
from maskgen import scenario_model
import random
from maskgen import tool_set
import shutil
from maskgen  import plugins
from maskgen import group_operations
import logging

def loadJSONGraph(pathname):
    with open(pathname, "r") as f:
        json_data = {}
        try:
            json_data = json.load(f, encoding='utf-8')
            G =  json_graph.node_link_graph(json_data, multigraph=False, directed=True)
        except  ValueError:
            json_data = json.load(f)
            G = json_graph.node_link_graph(json_data, multigraph=False, directed=True)
        return BatchProject(G,json_data)
    return None

def pickArg(param, local_state):
    if param['type'] == 'list':
        return random.choice(param['values'])
    elif 'int' in param['type']  :
        v = param['type']
        vals = [int(x) for x in v[v.rfind('[') + 1:-1].split(':')]
        beg = vals[0] if len (vals) > 0 else 0
        end = vals[1] if len(vals) > 1 else beg+1
        return random.randint(beg, end)
    elif 'float' in param['type'] :
        v = param['type']
        vals = [float(x) for x in v[v.rfind('[') + 1:-1].split(':')]
        beg = vals[0] if len(vals) > 0 else 0
        end = vals[1] if len(vals) > 1 else beg+1.0
        diff = end - beg
        return beg+ random.random()* diff
    elif param['type'] == 'yesno':
        return random.choice(['yes','no'])
    elif param['type'].startswith('donor'):
        choices = [node for node in local_state['model'].getGraph().nodes() \
                   if len(local_state['model'].getGraph().predecessors(node)) == 0]
        return random.choice(choices)
    return None

pluginSpecFuncs = {}
def loadCustomFunctions():
    import pkg_resources
    for p in  pkg_resources.iter_entry_points("maskgen_specs"):
        print 'load spec ' + p.name
        pluginSpecFuncs[p.name] = p.load()

def callPluginSpec(specification):
    if specification['name'] not in pluginSpecFuncs:
        raise ValueError("Invalid specification name:" + str(specification['name']))
    return pluginSpecFuncs[specification['name']](specification['parameters'])

def executeParamSpec(specification, global_state, local_state, predecessors):
    """
    :param specification:
    :param global_state:
    :param local_state:
    :param predecessors:
    :return:
    @rtype : tuple(image_wrap.ImageWrapper,str)
    @type predecessors: List[str]
    """
    if specification['type'] == 'mask':
       source = getNodeState(specification['source'], local_state)['node']
       target = getNodeState(specification['target'], local_state)['node']
       return os.path.join(local_state['model'].get_dir(), local_state['model'].getGraph().get_edge_image(source, target, 'maskname')[1])
    if specification['type'] == 'value':
        return specification['value']
    if specification['type'] == 'list':
        return random.choice(specification['values'])
    if specification['type'] == 'variable':
        return getNodeState(specification['source'], local_state)[specification['name']]
    if specification['type'] == 'donor':
        if 'source' in specification:
            return getNodeState(specification['source'], local_state)['node']
        return random.choice(predecessors)
    if specification['type'] == 'imagefile':
        source = getNodeState(specification['source'], local_state)['node']
        return local_state['model'].getGraph().get_image(source)[1]
    if specification['type'] == 'input':
        return getNodeState(specification['source'], local_state)['output']
    if specification['type'] == 'plugin':
        return  callPluginSpec(specification)
    return pickArg(specification,local_state)

def pickArgs(local_state, global_state, argument_specs, operation,predecessors):
    """
    :param local_state:
    :param global_state:
    :param argument_specs:
    :param operation:
    :param predecessors:
    :return:
    @type operation : Operation
    @type predecessors: List[str]
    """
    startType = local_state['model'].getStartType()
    args = {}
    if argument_specs is not None:
        for spec_param, spec in argument_specs.iteritems():
            args[spec_param] = executeParamSpec(spec,global_state,local_state, predecessors)
    for param in operation.mandatoryparameters:
        if argument_specs is None or param not in argument_specs:
            paramDef = operation.mandatoryparameters[param]
            if 'source' in paramDef and paramDef['source'] is not None and paramDef['source'] != startType:
                continue
            v = pickArg(paramDef,local_state)
            if v is None:
                raise ValueError('Missing Value for parameter ' + param + ' in ' + operation.name)
            args[param] = v
    for param in operation.optionalparameters:
        if argument_specs is None or param not in argument_specs:
            v = pickArg(operation.optionalparameters[param],local_state)
            if v is not None:
                args[param] = v
    return args

def getNodeState(node_name,local_state):
    """

    :param local_state:
    :param node_name:
    :return:
    @type local_state: Dict
    @type node_name: str
    @rtype: Dict
    """
    if node_name in local_state:
        my_state = local_state[node_name]
    else:
        my_state = {}
        local_state[node_name] = my_state
    return my_state


def pickImage(node, global_state={}):
    if node['picklist'] not in global_state:
        if not os.path.exists(node['image_directory']):
            raise ValueError("ImageSelection missing valid image_directory")
        listing = os.listdir(node['image_directory'])
        global_state[node['picklist']] = listing
        if os.path.exists(node['picklist'] + '.txt'):
           with open(node['picklist'] + '.txt', 'r') as fp:
              for line in fp.readlines():
                  line = line.strip()
                  if line in listing:
                      listing.remove(line)
    else:
        listing = global_state[node['picklist']]
    if len(listing) == 0:
        raise ValueError("Picklist of Image Files Empty")
    pick = random.choice(listing)
    listing.remove(pick)
    with open(node['picklist'] + '.txt', 'a') as fp:
        fp.write(pick + '\n')
    return os.path.join(node['image_directory'], pick)

class BatchOperation:

    def execute(self,graph, node_name, node, connect_to_node_name,local_state={},global_state={}):
        """
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        pass

class ImageSelectionOperation(BatchOperation):

    def execute(self, graph, node_name, node, connect_to_node_name, local_state={},global_state={}):
        """
        Add a image to the graph
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        pick = pickImage(node,global_state =global_state)
        getNodeState(node_name,local_state)['node'] = local_state['model'].addImage(pick)
        return local_state['model']


class BaseSelectionOperation(BatchOperation):

    def execute(self, graph,node_name, node, connect_to_node_name, local_state={},global_state={}):
        """
        Add a image to the graph
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        pick = pickImage( node,global_state =global_state)
        pick_file = os.path.split(pick)[1]
        name = pick_file[0:pick_file.rfind('.')]
        dir = os.path.join(global_state['projects'],name)
        os.mkdir(dir)
        shutil.copy2(pick, os.path.join(dir,pick_file))
        local_state['model'] = scenario_model.createProject(dir,suffixes=tool_set.suffixes)[0]
        for prop, val in local_state['project'].iteritems():
            local_state['model'].setProjectData(prop, val)
        getNodeState(node_name, local_state)['node'] = local_state['model'].getNodeNames()[0]
        return local_state['model']

class PluginOperation(BatchOperation):
    logger = logging.getLogger('PluginOperation')

    def execute(self, graph, node_name, node,connect_to_node_name, local_state={},global_state={}):
        """
        Add a node through an operation.
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        my_state = getNodeState(node_name,local_state)

        predecessors = [getNodeState(predecessor, local_state)['node'] \
                        for predecessor in graph.predecessors(node_name) \
                        if predecessor != connect_to_node_name and 'node' in getNodeState(predecessor, local_state)]

        predecessor_state=getNodeState(connect_to_node_name, local_state)
        local_state['model'].selectImage(predecessor_state['node'])
        im, filename = local_state['model'].currentImage()
        plugin_name = node['plugin']
        plugin_op = plugins.getOperation(plugin_name)
        if plugin_op is None:
            raise ValueError('Invalid plugin name "' + plugin_name + '" with node ' + node_name)
        op = software_loader.getOperation(plugin_op['name'],fake=True)
        args = pickArgs(local_state, global_state, node['arguments'] if 'arguments' in node else None, op,predecessors)
        if 'experiment_id' in node:
            args['experiment_id'] = node['experiment_id']
        self.logger.debug('Execute plugin ' + plugin_name + ' on ' + filename  + ' with ' + str(args))
        errors, pairs = local_state['model'].imageFromPlugin(plugin_name, im, filename, **args)
        if errors is not None or  (type(errors) is list and len (errors) > 0 ):
            raise ValueError("Plugin " + plugin_name + " failed:" + str(errors))
        my_state['node'] = pairs[0][1]
        for predecessor in predecessors:
            local_state['model'].selectImage(predecessor)
            local_state['model'].connect(my_state['node'],sendNotifications=False)
            local_state['model'].selectImage(my_state['node'])
        return local_state['model']

class InputMaskPluginOperation(PluginOperation):
    logger = logging.getLogger('InputMaskPluginOperation')

    def execute(self, graph, node_name, node,connect_to_node_name, local_state={},global_state={}):
        """
        Add a node through an operation.
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        my_state = getNodeState(node_name,local_state)

        predecessors = [getNodeState(predecessor, local_state)['node'] for predecessor in graph.predecessors(node_name) \
                        if predecessor != connect_to_node_name and 'node' in getNodeState(predecessor, local_state)]
        predecessor_state=getNodeState(connect_to_node_name, local_state)
        local_state['model'].selectImage(predecessor_state['node'])
        im, filename = local_state['model'].currentImage()
        plugin_name = node['plugin']
        plugin_op = plugins.getOperation(plugin_name)
        if plugin_op is None:
            raise ValueError('Invalid plugin name "' + plugin_name + '" with node ' + node_name)
        op = software_loader.getOperation(plugin_op['name'],fake=True)
        args = pickArgs(local_state, global_state, node['arguments'] if 'arguments' in node else None, op,predecessors)
        targetfile,params = self.imageFromPlugin(plugin_name, im, filename, **args)
        my_state['output'] = targetfile
        if params is not None and type(params) == type({}):
            for k, v in params.iteritems():
                my_state[k] = v
        return local_state['model']

    def imageFromPlugin(self, filter, im, filename, **kwargs):
        import tempfile
        """
          @type filter: str
          @type im: ImageWrapper
          @type filename: str
          @rtype: list of (str, list (str,str))
        """
        file = os.path.split(filename)[1]
        file = file[0:file.rfind('.')]
        target = os.path.join(tempfile.gettempdir(),  file+ '_' + filter + '.png')
        shutil.copy2(filename, target)
        params = {}
        try:
            extra_args, msg = plugins.callPlugin(filter, im, filename, target, **kwargs)
            if extra_args is not None and type(extra_args) == type({}):
                for k, v in extra_args.iteritems():
                    if k not in kwargs:
                        params[k] = v
        except Exception as e:
            msg = str(e)
            raise ValueError("Plugin " + filter + " failed:" + msg)
        return target,params


batch_operations = {'BaseSelection': BaseSelectionOperation(),'ImageSelection':ImageSelectionOperation(),
                    'PluginOperation' : PluginOperation(),'InputMaskPluginOperation' : InputMaskPluginOperation()}

def getOperationGivenDescriptor(descriptor):
    """

    :param descriptor:
    :return:
    @rtype : BatchOperation
    """
    return batch_operations[descriptor['op_type']]

class BatchProject:
    logger = logging.getLogger('BatchProject')

    G = nx.DiGraph(name="Empty")

    def __init__(self,G,json_data):
        """
        :param G:
        @type G: nx.DiGraph
        """
        self.G = G
        self.json_data = json_data
        tool_set.setPwdX(tool_set.CustomPwdX(self.G.graph['username']))

    def _buildLocalState(self):
        local_state = {}
        local_state['project'] = {}
        for k in self.G.graph:
            if k not in ['recompress','name']:
                local_state['project'][k] =  self.G.graph[k]
        return local_state

    def getName(self):
        return self.G.graph['name'] if 'name' in self.G.graph else 'Untitled'

    def executeOnce(self, global_state=dict()):
        recompress = self.G.graph['recompress'] if 'recompress' in self.G.graph else False
        local_state = self._buildLocalState()
        self.logger.info('Build Project with global state: ' + str(global_state))
        base_node = self._findBase()
        try:
            self._execute_node(base_node, None, local_state, global_state)
            queue = [top for top in self._findTops() if top != base_node]
            queue.extend(self.G.successors(base_node))
            completed = [base_node]
            while len(queue) > 0:
                op_node_name = queue.pop(0)
                if op_node_name in completed:
                    continue
                predecessors = list(self.G.predecessors(op_node_name))
                # skip if a predecessor is missing
                if len([pred for pred in predecessors if pred not in completed]) > 0:
                    continue
                connecttonodes = [predecessor for predecessor in self.G.predecessors(op_node_name)
                            if self.G.node[predecessor]['op_type'] != 'InputMaskPluginOperation']
                #if not self.G.edge[predecessor][op_node_name]['donor']]
                connect_to_node_name = connecttonodes[0] if len(connecttonodes) > 0 else None
                self._execute_node(op_node_name, connect_to_node_name, local_state, global_state)
                completed.append(op_node_name)
                self.logger.debug('Completed: ' + op_node_name)
                queue.extend(self.G.successors(op_node_name))
            if recompress:
                self.logger.debug("Run Save As")
                op = group_operations.CopyCompressionAndExifGroupOperation(local_state['model'])
                op.performOp()
            local_state['model'].save()
            if 'archives' in global_state:
                local_state['model'].export(global_state['archives'])
        except Exception as e:
            print e
            if 'model' in local_state:
                shutil.rmtree(local_state['model'].get_dir())
            return None
        return local_state['model'].get_dir()


    def dump(self):
        filename = self.getName() + '.png'
        self._draw().write_png(filename)
        filename = self.getName() + '.csv'
        position = 0
        with open(filename,'w') as f:
            for node in self.json_data['nodes']:
                f.write(node['id']  + ',' + str(position) + '\n')
                position += 1

    colors_bytype ={ 'InputMaskPluginOperation' : 'blue'}
    def _draw(self):
        import pydot
        pydot_nodes = {}
        pygraph = pydot.Dot(graph_type='digraph')
        for node_id in self.G.nodes():
            node = self.G.node[node_id]
            name = op_type = node['op_type']
            if op_type in ['PluginOperation','InputMaskPluginOperation']:
                name = node['plugin']
            color = self.colors_bytype[op_type] if op_type in self.colors_bytype else 'black'
            pydot_nodes[node_id] = pydot.Node(node_id, label=name,
                                              shape='plain',
                                              color=color)
            pygraph.add_node(pydot_nodes[node_id])
        for edge_id in self.G.edges():
            node = self.G.node[edge_id[0]]
            op_type = node['op_type']
            color = self.colors_bytype[op_type] if op_type in self.colors_bytype else 'black'
            pygraph.add_edge(
                pydot.Edge(pydot_nodes[edge_id[0]], pydot_nodes[edge_id[1]],  color=color))
        return pygraph

    def validate(self):
        """
        Return list of error strings
        :return:
        @rtype : List[str]
        """

        errors = []
        topcount = 0
        for top in self._findTops():
            top_node = self.G.node[top]
            if top_node['op_type'] == 'BaseSelection':
                topcount += 1
        if topcount > 1:
            errors.append("More than one BaseSelection node")
        if topcount == 0:
            errors.append("Missing one BaseSelection node")


    def _findTops(self):
        """
        Find and return top node name
        :return:
        @rtype: str
        """
        return [node for node in self.G.nodes() if len(self.G.predecessors(node)) == 0]

    def _findBase(self):
        """
        Find and return top node name
        :return:
        @rtype: str
        """
        tops = self._findTops()
        for top in tops:
            top_node = self.G.node[top]
            if top_node['op_type'] == 'BaseSelection':
                return top
        return None

    def _execute_node(self, node_name,connect_to_node_name,local_state, global_state):
        """
        :param local_state:
        :param global_state:
        :return:
        @rtype: maskgen.scenario_model.ImageProjectModel
        """
        try:
            self.logger.debug('_execute_node ' + node_name + ' connect to ' + str (connect_to_node_name))
            return getOperationGivenDescriptor(self.G.node[node_name]).execute(self.G, node_name,self.G.node[node_name],connect_to_node_name, local_state = local_state, global_state=global_state)
        except Exception as e:
            print e
            raise e


def getBatch(jsonFile,loglevel=50):
    """
    :param jsonFile:
    :return:
    @return BatchProject
    """
    software_loader.loadOperations("operations.json")
    software_loader.loadSoftware("software.csv")
    software_loader.loadProjectProperties("project_properties.json")
    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT,level=50 if loglevel is None else int(loglevel))
    return  loadJSONGraph(jsonFile)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--json',             required=True,         help='JSON File')
    parser.add_argument('--count', required=False, help='number of projects to build')
    parser.add_argument('--results', required=True, help='project results directory')
    parser.add_argument('--loglevel', required=False, help='log level')
    parser.add_argument('--graph', required=False, action='store_true',help='create graph PNG file')
    args = parser.parse_args()
    if not os.path.exists(args.results) or not os.path.isdir(args.results):
        print 'invalid directory for results: ' + args.results
        return
    loadCustomFunctions()
    batchProject =getBatch(args.json, loglevel=args.loglevel)
    globalState =  {'projects' : args.results}
    count = int(args.count) if args.count is not None else 1
    if args.graph is not None:
        batchProject.dump()
    for i in range(count):
        project_directory =  batchProject.executeOnce(globalState)
        if project_directory is not None:
            print 'completed' + project_directory
        else:
            break

if __name__ == '__main__':
    main()

