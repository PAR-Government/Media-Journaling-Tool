import json
import networkx as nx
from networkx.readwrite import json_graph
import os
from maskgen.software_loader import *
from maskgen import scenario_model
import maskgen.tool_set
import maskgen.group_operations
import maskgen.plugins
import random
import shutil

def loadJSONGraph(pathname):
    with open(pathname, "r") as f:
        try:
            G =  json_graph.node_link_graph(json.load(f, encoding='utf-8'), multigraph=False, directed=True)
        except  ValueError:
            G = json_graph.node_link_graph(json.load(f), multigraph=False, directed=True)
        BatchProject(pathname, graph=G)

def getBaseNodes(local_state):

def pickArg(param, local_state):
    if param['type'] == 'list':
        return random.choice(param['values'])
    elif param['type'] == 'int':
        v = param['type']
        vals = [int(x) for x in v[v.rfind('[') + 1:-1].split(':')]
        beg = vals[0] if len (vals) > 0 else 0
        end = vals[1] if len(vals) > 2 else 0
        return random.randint(beg, end)
    elif param['type'] == 'float':
        v = param['type']
        vals = [float(x) for x in v[v.rfind('[') + 1:-1].split(':')]
        beg = vals[0] if len(vals) > 0 else 0
        end = vals[1] if len(vals) > 2 else 0
        diff = end - beg
        return beg+ random.random()* diff
    elif param['type'] == 'yesno':
        return random.choice(['yes','no'])
    elif param['type'].startswith('donor'):
        choices = [node for node in local_state['model'].getGraph().nodes() \
                   if len(local_state['model'].getGraph().predecessors(node)) == 0]
        return random.choice(choices)
    return None


def executeParamSpec(specification, global_state, local_state):
    """
    :param specification:
    :param global_state:
    :param local_state:
    :return:
    @rtype : tuple(image_wrap.ImageWrapper,str)
    """
    if specification['type'] == 'mask':
       source = getNodeState(specification['source'], local_state)['node']
       target = getNodeState(specification['target'], local_state)['node']
       return local_state['model'].getGraph().get_edge_image(source, target, 'maskname')
    if specification['type'] == 'value':
        return specification['value']
    if specification['type'] == 'donor':
        source = getNodeState(specification['source'], local_state)['node']
        return local_state['model'].getGraph().get_image(source)
    return None

def pickArgs(local_state, global_state, argument_specs, operation):
    """
    :param local_state:
    :param global_state:
    :param argument_specs:
    :param operation:
    :return:
    @type operation : Operation
    """
    args = {}
    for spec_param, spec in argument_specs.iteritems():
        args[spec_param] = executeParamSpec(spec,global_state,local_state)
    for param in operation.mandatoryparameters:
        if param not in argument_specs:
            v = pickArg(param,local_state)
            if v is None:
                raise 'Missing Value for parameter ' + param + ' in ' + operation.name
            args[param] = v
    for param in operation.mandatoryparameters:
        if param not in argument_specs:
            v = pickArg(param,local_state)
            if v is not None:
                args[param] = v

def getNodeState(local_state,node_name):
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

class BatchOperation:

    def execute(self,graph, node, local_state={},global_state={}):
        """
        :param graph:
        :param node:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node: Dict
        @type global_state: Dict
        @type global_state: Dict
        @rtype: maskgen.scenario_model.ImageProjectModel
        """
        pass

class ImageSelectionOperation(BatchOperation):

    def execute(self, graph, node, local_state={},global_state={}):
        """
        Add a image to the graph
        :param graph:
        :param node:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node: Dict
        @type global_state: Dict
        @type global_state: Dict
        @rtype: maskgen.scenario_model.ImageProjectModel
        """
        pick = self._pickImage(node,local_state =local_state)
        getNodeState(node,local_state)['node'] = local_state['model'].addImage(pick)
        return local_state['model']

    def _pickImage(self,node, local_state={}):
        my_state = getNodeState(local_state, node)
        if 'listing' not in my_state:
            if not os.path.exists(node['image_directory']):
                raise ValueError("ImageSelection missing valid image_directory")
            listing = os.listdir(node['image_directory'])
            my_state['listing'] = listing
            with open('picked.txt', 'r') as fp:
                for line in fp.readlines():
                    line = line.strip()
                    if line in listing:
                        listing.remove(line)
        pick = random.choice(listing)
        listing.pop(pick)
        with open('picked.txt','a') as fp:
            fp.write(pick + '\n')
        return os.path.join(node['image_directory'],pick)

class BaseSelectionOperation(BatchOperation):

    def execute(self, graph, node, local_state={},global_state={}):
        """
        Add a image to the graph
        :param graph:
        :param node:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node: Dict
        @type global_state: Dict
        @type global_state: Dict
        @rtype: maskgen.scenario_model.ImageProjectModel
        """
        pick = self._pickImage(node,local_state =local_state)
        pick_file = os.path.split(pick)[1]
        name = pick_file[0:pick_file.rfind('.')]
        dir = os.path.join(global_state['projects'],name)
        os.mkdir(dir)
        shutil.copy2(pick, os.path.join(dir,pick_file))
        local_state['model'] = maskgen.scenario_model.createProject(dir)
        return local_state['model']

class PluginOperation(BatchOperation):

    def execute(self, graph, node, local_state={},global_state={}):
        """
        Add a node through an operation.
        :param graph:
        :param node:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node: Dict
        @type global_state: Dict
        @type global_state: Dict
        @rtype: maskgen.scenario_model.ImageProjectModel
        """
        my_state = getNodeState(local_state, node)
        for predecessor in graph.predecessors(node):
            predecessor_state= local_state[predecessor]
            pred_node = graph.node[predecessor]
            local_state['model'].selectImage(predecessor_state['node'])
            im, filename = local_state['model'].currentImage()
            plugin = pred_node['plugin']
            local_state['model'].imageFromPlugin(plugin, im, filename,**pred_node['arguments'])
        return local_state['model']


class MergeOperation(BatchOperation):

    def execute(self, graph, node, local_state={}, global_state={}):
        """
        Add a node through an operation.
        :param graph:
        :param node:
        :param local_state:
        :param global_state:
        :return:
        @type graph: nx.DiGraph
        @type node: Dict
        @type global_state: Dict
        @type global_state: Dict
        @rtype: maskgen.scenario_model.ImageProjectModel
        """
        my_state = getNodeState(local_state, node)
        for predecessor in graph.predecessors(node):
            predecessor_state = local_state[predecessor]
            pred_node = graph.node[predecessor]
            local_state['model'].selectImage(predecessor_state['node'])
            im, filename = local_state['model'].currentImage()
            plugin = pred_node['plugin']
            local_state['model'].imageFromPlugin(plugin, im, filename, **pred_node['arguments'])
        return local_state['model']

batch_operations = {'BaseSelection': BaseSelectionOperation(),'ImageSelection':ImageSelectionOperation()}

def getOperationGivenDescriptor(descriptor):
    """

    :param descriptor:
    :return:
    @rtype : BatchOperation
    """
    return batch_operations[descriptor['op_type']]

class BatchProject:
    G = nx.DiGraph(name="Empty")
    dir = '.'

    def save(self):
        filename = os.path.abspath(os.path.join(self.dir, self.G.name + '.json'))
        with open(filename, 'w') as f:
            json.dump(json_graph.node_link_data(self.G), f, indent=2, encoding='utf-8')

    def executeOnce(self, global_state=dict()):
        local_state = {}
        base_node = self._findBase()
        image_model = self._execute_node(base_node,local_state, global_state)
        queue = [top for top in self._findTops() if top != base_node]
        local_state = local_state['model'] = image_model
        while len(queue) > 0:
            op_node_name = queue.pop(0)
            self._execute_node(op_node_name, local_state, global_state)
            queue.append(self.G.successors(op_node_name))
        image_model.export(global_state['archives'])


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

    def _execute_node(self, node_name,local_state, global_state):
        """
        :param local_state:
        :param global_state:
        :return:
        @rtype: maskgen.scenario_model.ImageProjectModel
        """
        return getOperationGivenDescriptor(self.G.node[node_name]).execute(self.G, node_name, local_state = local_state, global_state=global_state)



