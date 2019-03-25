# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================


import Queue as queue
import argparse
import copy
import json
import random
import shutil
import sys
import traceback
from datetime import datetime
from functools import partial
from threading import Thread, Semaphore

import networkx as nx
import numpy as np
from maskgen import group_operations
from maskgen import maskGenPreferences
from maskgen import plugins
from maskgen import scenario_model
from maskgen import software_loader
from maskgen import tool_set
from maskgen.batch.permutations import *
from maskgen.graph_output import ImageGraphPainter
from maskgen.image_graph import ImageGraph
from maskgen.loghandling import set_logging,set_logging_level
from maskgen.preferences_initializer import initial_user
from maskgen.software_loader import getRule
from maskgen.support import getValue
from maskgen.userinfo import get_username
from maskgen.validation.core import Severity
from networkx.readwrite import json_graph
from maskgen.external.exporter import ExportManager

export_manager = ExportManager()


class IntObject:
    value = 0
    lock = Lock()

    def __init__(self, value=0):
        self.value = value
        pass

    def decrement(self):
        with self.lock:
            current_value = self.value
            self.value -= 1
            return current_value

    def increment(self):
        with self.lock:
            self.value += 1
            return self.value



def _findTops(graph):
    """
    Find and return top node name
    :return:
    @rtype: str
    """
    return [node for node in graph.nodes() if len(graph.predecessors(node)) == 0]


def _listOfAllNodes(graph):
    """
    BFS
    :param graph:
    :return: Return all nodes in the graph, top to bottom breadth-first
    """
    children = _findTops(graph)
    pos = 0
    while pos < len(children):
        next = children[pos]
        for child in graph.successors(next):
            if child not in children:
                children.append(child)
        pos += 1
    return children

def new_id(node_id):
    import uuid
    """
      :param node_id:
      :param: graph
      :return:
      @type graph: nx.DiGraph
      @type node_id: str
      """
    parts = node_id.split('##')
    return parts[0] + str(uuid.uuid4())

def duplicate_path(graph, new_node_id, old_node_id, to_visit):
    """
    Duplicate all the children edges and nodes starting with
    old_node_id, replacing the duplicates with the new parent
    new_node_id.
    :param graph: the graph
    :param new_node_id: the replacement for next_node
    :param old_node_id: the next node to process
    :param to_visit: nodes to still process; add new nodes to this list
    :return:
    """
    for next_node in graph.successors(old_node_id):
        node = graph.node[next_node]
        dup_node_id = new_id(next_node)
        graph.add_node(dup_node_id, **node)
        if getValue(node, 'source', '$$') == old_node_id:
                graph.node[dup_node_id]['source'] = new_node_id
        to_visit.append(dup_node_id)
        graph.add_edge(new_node_id, dup_node_id, **graph[old_node_id][next_node])
        duplicate_path(graph,dup_node_id,next_node,to_visit)

def split_sourced_graph(graph, to_visit):
    """
    Graph edges indicate a split point with multiple parents, one which is labeled as a source, are split
    :param graph:
    :param: to_visit
    :return:
    @type graph: nx.DiGraph
    @type to_visit: list
    """
    while len(to_visit) > 0:
        node_id = to_visit.pop(0)
        node = graph.node[node_id]
        preds = []
        source = getValue(node, 'source', '$$')
        for pred in graph.predecessors(node_id):
            edge = graph.edge[pred][node_id]
            if getValue(edge,'split',False) and \
                    not getValue(edge,'donor',False) and \
                    source not in [pred,'$$']:
                preds.append(pred)
        # if source not specific in node, assume the first one
        if source == '$$':
            preds = preds[1:]
        if len(preds) == 0:
            continue
        for pred in preds:
            dup_node_id = new_id(node_id)
            graph.add_node(dup_node_id, **node)
            graph.node[dup_node_id]['source'] = pred
            to_visit.append(dup_node_id)
            graph.add_edge(pred, dup_node_id, **graph[pred][node_id])
            graph.remove_edge(pred, node_id)
            duplicate_path(graph, dup_node_id, node_id, to_visit)
    return graph

def separate_paths(graph):
    """
    Graph edges indicate a split point with multiple parents, one which is labeled as a source, are split
    :param graph:
    :return: graph augmented
    @type graph: nx.DiGraph
    """
    return split_sourced_graph(graph, _listOfAllNodes(graph))

def remap_links(json_data):
    """
    Networkx usings links that reference nodes by position.
    The incoming JSON data allows the user to load by id.
    How to tell the difference: The source and target are strings.
    :param json_data: networkx compliant dictionary
    :return:
    @type: dict
    @rtype: dict
    """
    node_list = json_data['nodes']
    node_index = {}
    for pos in range(len(node_list)):
        node_index[node_list[pos]['id']] = pos
    link_list = json_data['links']

    def remap_link(link, key, node_index):
        if key in link and type(link[key]) in [str,unicode]:
            if link[key] not in node_index:
                raise IndexError('Node ID {} not found in link'.format(link[key]))
            return node_index[link[key]]
        return link[key]

    new_linked_list = []
    for item in link_list:
        new_link = copy.copy(item)
        new_link .update ({
            'source': remap_link(item, 'source', node_index),
            'target': remap_link(item, 'target', node_index)
        })
        new_linked_list.append(new_link)
    json_data['links'] = new_linked_list
    return json_data

def loadJSONInitializer(global_state):
    d = {}
    jsonKeys = [key for key in global_state if str(key).endswith('.json.load')]
    for k in jsonKeys:
        d[k[0:-5]] = json.load(open(global_state[k]))
    return d

def loadJSONGraph(pathname):
    logging.getLogger('maskgen').info('Loading JSON file {}'.format(pathname))
    with open(pathname, "r") as f:
        try:
            json_data = json.load(f, encoding='utf-8')
        except  ValueError:
            json_data = json.load(f)
        if 'picks' in json_data:
            return ProjectPicker(json_data)
        return BatchProject(json_data)
    return None

class ProjectPicker:

    def __init__(self,picker_json):
        self.subs = {}
        for pick_key, spec_file_name in picker_json['picks'].iteritems():
            self.subs[pick_key] = loadJSONGraph(spec_file_name)

    def executeForProject(self, project, nodes, workdir=None, global_variables={}):
        for node in nodes:
            base_id = project.getBaseNode(node)
            key = os.path.splitext(project.getGraph().get_filename(base_id))[1][1:].lower()
            if key in self.subs:
                if not self.subs[key].executeForProject(project,[node],workdir=workdir,global_variables=global_variables):
		   return False
        return True

import string
class MyFormatter(string.Formatter):
    def __init__(self, local_state, global_state):
        self.local_state = local_state
        self.global_state = global_state
        string.Formatter.__init__(self)

    def get_value(self, key, args, kwargs):
        if isinstance(key, (int, long)):
            return args[key]
        elif '@' in key:
            return getValue(getNodeState(key[key.rfind('@') + 1:], self.local_state), key[:key.rfind('@')])
        else:
            return self.global_state[key]


def getNoneDonorPredecessor(graph, target):
    """

    :param graph:
    :return:
    @type graph: ImageGraph
    """
    viable = [pred for pred in graph.predecessors(target) if graph.get_edge(pred, target)['op'] != 'Donor']
    return viable[0] if len(viable) > 0 else None


def getGraphFromLocalState(local_state):
    """

    :param local_state:
    :return:
    @type local_state: dict
    @rtype: ImageGraph
    """
    return local_state['model'].getGraph()

def rangeNumberPicker(value, convert_function=lambda x: int(x)):
    spec = value[value.rfind('[') + 1:-1] if value.rfind('[') >= 0 else value
    choices = []
    for section in spec.split(','):
        vals = [convert_function(x) for x in section.split(':')]
        beg = vals[0] if len(vals) > 0 else 0
        end = vals[1] if len(vals) > 1 else beg + convert_function(1)
        if len(vals) > 2:
            increment = vals[2]
        else:
            increment = convert_function(1)
        choices.append((beg, end, increment))
    bounds = random.choice(choices)
    return bounds

def buildIterator(spec_name, param_spec, global_state, random_selection=False):
    """
    :param param_spec: argument specification
    :param random_selection: produce a continuous stream of random selections
    :return: a iterator function to construct an iterator over possible values
    """
    if param_spec['type'] == 'list':
        new_values =[(value.format(**global_state) if type(value) in [str,unicode] else value) for value in param_spec['values']]
        if not random_selection:
            return ListPermuteGroupElement(spec_name, new_values)
        else:
            return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: random.choice(new_values)))
    elif 'int' in param_spec['type']:
        v = param_spec['type']
        beg,end,increment = rangeNumberPicker(v)
        if not random_selection:
            return IteratorPermuteGroupElement(spec_name, lambda: xrange(beg, end + 1, increment).__iter__())
        elif increment != 1:
            return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: random.choice( xrange(beg, end + 1, increment))))
        else:
            return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: random.randint(beg, end)))
    elif 'float' in param_spec['type']:
        v = param_spec['type']
        beg, end, increment = rangeNumberPicker(v, convert_function=float)
        if not random_selection:
            return IteratorPermuteGroupElement(spec_name, lambda: np.arange(beg, end, increment).__iter__())
        elif abs(increment - 1.0) > 0.000000001:
            return PermuteGroupElement(spec_name,
                                       randomGeneratorFactory(lambda: random.choice(np.arange(beg, end, increment))))
        else:
            return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: beg + random.random() * (end - beg)))
    elif param_spec['type'] == 'yesno':
        if not random_selection:
            return ListPermuteGroupElement(spec_name, ['yes', 'no'])
        else:
            return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: random.choice(['yes', 'no'])))
    elif param_spec['type'].startswith('donor'):
        mydata = local()
        local_state = mydata.current_local_state
        choices = [node for node in local_state.getGraph().nodes() \
                   if len(local_state.getGraph().predecessors(node)) == 0]
        if not random_selection:
            # do not think we can save this state since it is tied to the local project
            return PermuteGroupElement(spec_name, choices.__iter__)
        else:
            return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: random.choice(choices)))
    return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: None))


def pickArg(param_spec, node_name, spec_name, global_state, local_state):
    """
    :param global_state:
    :param name: name of the of iterator (within the group)
    :param permutegroup: the name of the permutation group
    :param toIteratorFunction:  initialize iterator with this function if missing or exhausted
    :return:
    """
    manager = global_state['permutegroupsmanager']
    permutegroup = param_spec['permutegroup'] if 'permutegroup' in param_spec else None
    if not manager.has_specification(permutegroup, node_name + '.' + spec_name):
        manager.loadParameter(permutegroup,
                              buildIterator(node_name + '.' + spec_name, param_spec, global_state,
                                            random_selection=permutegroup is None))
    return manager.current(permutegroup, node_name + '.' + spec_name)


pluginSpecFuncs = {}

def processValue(formatter,value,postProcess):
    """
    format the value, recurse if a dictionary.
    vall postProcess on every result
    :param formatter:
    :param value:
    :param postProcess:
    :return:
    @type formatter: MyFormatter
    """
    if isinstance(value,str) or isinstance(value,unicode):
        return postProcess(formatter.vformat(value,[],{}))
    elif isinstance(value,dict):
        return {k:processValue(formatter,v,postProcess) for k,v in value.iteritems()}
    else:
        return postProcess(value)

def loadCustomFunctions():
    import pkg_resources
    for p in pkg_resources.iter_entry_points("maskgen_specs"):
        logging.getLogger('maskgen').info('load spec ' + p.name)
        if p.name not in pluginSpecFuncs:
            pluginSpecFuncs[p.name] = p.load()

def callPluginSpec(specification, local_state, global_state, postProcess):
    if specification['name'] not in pluginSpecFuncs:
        raise ValueError("Invalid specification name:" + str(specification['name']))
    parameters = processValue(MyFormatter(local_state,global_state),specification['parameters'], postProcess)
    if 'state_name' in specification:
        if specification['state_name'] not in local_state:
            local_state[specification['state_name']] = dict()
        return pluginSpecFuncs[specification['name']](parameters,
                                                      state=local_state[specification['state_name']])
    return pluginSpecFuncs[specification['name']](parameters)

def specType(specification):
    if type(specification) != dict or 'type' not in specification:
        return 'value'
    else:
        return specification['type']

def executeParamSpec(specification_name, specification, global_state, local_state, node_name, predecessors):
    """
    :param specification:
    :param global_state:
    :param local_state:
    :param predecessors:
    :return:
    @rtype : tuple(image_wrap.ImageWrapper,str)
    @type predecessors: List[str]
    """
    if type(specification) != dict:
        specification = {'value':specification}
    spec_type = specType(specification)
    donothing = lambda x:  x
    postProcess = getRule(specification['function'],noopRule=donothing)  if 'function' in specification else donothing
    if spec_type == 'mask':
        if 'source' not in specification:
            raise ValueError('source attribute missing in  {}'.format(specification_name))
        target = getNodeState(specification['target'], local_state)['node']
        source = getNoneDonorPredecessor(getGraphFromLocalState(local_state), target)
        invert = specification['invert'] if 'invert' in specification else False
        edge = getGraphFromLocalState(local_state).get_edge(source,target)
        mask = os.path.join(local_state['model'].get_dir(), getValue(edge,'maskname',defaultValue=''))
        if invert:
            tool_set.openImageFile(mask, isMask=True).invert().save(mask + '.png')
            mask = mask + '.png'
        return postProcess(mask)
    elif spec_type == 'value':
        return processValue(MyFormatter(local_state,global_state),specification['value'], postProcess)
    elif spec_type == 'variable':
        if 'name' not in specification:
            raise ValueError('name attribute missing in  {}'.format(specification_name))
        if 'source' not in specification:
            raise ValueError('name attribute missing in  {}'.format(specification_name))
        val = getValue(getNodeState(specification['source'], local_state),specification['name'])
        if val is None:
            raise ValueError('Missing variable {} in from {} while processing {}'.format(specification['name'],
                                                                                         specification['source'],
                                                                                         specification_name))
        if 'permutegroup' in specification:
            source_spec = copy.copy(val)
            source_spec['permutegroup'] = specification['permutegroup']
            return postProcess(pickArg(source_spec, node_name, specification_name, global_state, local_state))
        else:
            return postProcess(val)
    elif spec_type == 'donor':
        if 'source' in specification:
            if specification['source'] == 'base':
                return local_state['model'].getBaseNode(local_state['model'].start)
            return getNodeState(specification['source'], local_state)['node']
        if len(predecessors) != 1:
            raise ValueError('Donor specification {} missing source '.format(specification['name']))
        return postProcess(predecessors[0])
    elif spec_type == 'imagefile':
        if 'source' not in specification:
            raise ValueError('name attribute missing in  {}'.format(specification_name))
        node_state = getNodeState(specification['source'], local_state)
        if 'node' not in node_state:
            raise ValueError('Node {} did not generate a project node.  Try using type "input" in {}'.format(
                specification['source'], specification_name))
        return postProcess(getGraphFromLocalState(local_state).get_image(node_state['node'])[1])
    elif spec_type == 'input':
        if 'source' not in specification:
            raise ValueError('name attribute missing in  {}'.format(specification_name))
        return postProcess(getNodeState(specification['source'], local_state)['output'])
    elif spec_type == 'plugin':
        return postProcess(callPluginSpec(specification, local_state, global_state, postProcess))
    elif spec_type.startswith('global'):
        if 'name' not in specification:
            raise ValueError('source attribute missing in {}'.format(specification_name))
        return global_state[specification['name']]
    return postProcess(pickArg(specification, node_name, specification_name, global_state, local_state))


def pickArgs(local_state, global_state, node_name, argument_specs, operation, predecessors):
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
            args[spec_param] = executeParamSpec(spec_param, spec, global_state, local_state, node_name, predecessors)
    for param in operation.mandatoryparameters:
        if argument_specs is None or param not in argument_specs:
            paramDef = operation.mandatoryparameters[param]
            if 'source' in paramDef and paramDef['source'] is not None and paramDef['source'] != startType:
                continue
            v = pickArg(paramDef, node_name, param, global_state, local_state)
            if v is None:
                raise ValueError('Missing Value for parameter ' + param + ' in ' + operation.name)
            args[param] = v
    for param in operation.optionalparameters:
        if argument_specs is None or param not in argument_specs:
            v = pickArg(operation.optionalparameters[param], node_name, param, global_state, local_state)
            if v is not None:
                args[param] = v
    return args


def getNodeState(node_name, local_state):
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

def getNodeStateFromPredecessor(current_node, local_state, graph):
    """

    :param current_node
    :param local_state:
    :param graph:
    :return:
    @type local_state: Dict
    @type graph: DiGraph
    @rtype: Dict
    """
    for pred in graph.predecessors(current_node):
        if pred in local_state and 'node' in local_state[pred]:
            return getNodeState(pred, local_state)
    for pred in graph.predecessors(current_node):
        result = getNodeStateFromPredecessor(pred, local_state, graph)
        if result is not None:
            return result
    return None

def pickImageIterator(specification, spec_name, global_state):
    if 'picklists' not in global_state:
        global_state['picklists'] = dict()
    if 'files' in specification:
        return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: random.choice(
            [file.format(**global_state) for file in specification['files']])))
    picklist_name = specification['picklist'] if 'picklist' in specification else spec_name
    directory = specification['image_directory'].format(**global_state)
    if picklist_name not in global_state['picklists']:
        element = FilePermuteGroupElement(spec_name,
                                          directory,
                                          tracking_filename=picklist_name + '.txt',
                                          fileCheckFunction=lambda x: tool_set.fileType(x) in ['audio', 'video',
                                                                                               'image', 'zip'],
                                          filetypes=specification[
                                              'filetypes'] if 'filetypes' in specification else None)
        global_state['picklists'][picklist_name] = element
    else:
        if picklist_name in global_state['picklists'] and \
                        global_state['picklists'][picklist_name].directory != directory:
            raise ValueError('Picklist {} reference else where with a different directory. {}'.format(
                picklist_name, specification['image_directory']
            ))
        link_element = global_state['picklists'][picklist_name]
        element = LinkedPermuteGroupElement(spec_name, link_element)
    return element


class BatchOperation:
    def execute(self, graph, node_name, node, connect_to_node_name, local_state={}, global_state={}):
        """
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return: node id
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: str
        """
        pass


class ImageSelectionOperation(BatchOperation):
    def execute(self, graph, node_name, node, connect_to_node_name, local_state={}, global_state={}):
        """
        Add a image to the graph
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return: node id
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type local_state: Dict
        @type global_state: Dict
        @rtype: str
        """
        manager = global_state['permutegroupsmanager']
        pick = manager.current(node['permutegroup'] if 'permutegroup' in node else None,
                               node_name)
        logging.getLogger('maskgen').info('Picking file {}'.format(pick))
        getNodeState(node_name, local_state)['node'] = \
            local_state['model'].addImage(pick,
                                          prnu='prnu' in node and node['prnu'],
                                          cgi='cgi' in node and node['cgi'],
                                          **(node['arguments'] if 'arguments' in node else {}))
        return getNodeState(node_name, local_state)['node']


class BaseSelectionOperation(BatchOperation):
    def execute(self, graph, node_name, node, connect_to_node_name, local_state={}, global_state={}):
        """
        Add a image to the graph
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return: node id
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: str
        """
        manager = global_state['permutegroupsmanager']
        pick = manager.current(node['permutegroup'] if 'permutegroup' in node else None,
                               node_name)
        logging.getLogger('maskgen').info('Picking file {}'.format(pick))
        pick_file = os.path.split(pick)[1]
        name = pick_file[0:pick_file.find('.')]
        dir = os.path.join(global_state['projects'], name)
        now = datetime.now()
        timestampname = 'timestamp name' in node and node['timestamp name']
        if os.path.exists(dir) or timestampname:
            suffix = '_' + now.strftime("%Y%m%d-%H%M%S-%f")
            dir = dir + suffix
            name = name + suffix
        os.mkdir(dir)
        file_path_in_project = os.path.join(dir, pick_file)
        shutil.copy2(pick, file_path_in_project)
        logging.getLogger('maskgen').info("Build project {}".format(pick_file))
        preferred_organization = maskGenPreferences.get_key('organization')
        preferred_username=getValue(global_state,'username',defaultValue=get_username())
        suffix = os.path.splitext(pick_file)[1]
        model = scenario_model.createProject(dir,
                                             name=name,
                                             base=file_path_in_project,
                                             suffixes=tool_set.suffixes+ [suffix],
                                             username=preferred_username,
                                             organization=preferred_organization,
                                             tool='jtproject',
                                             preferences=node['arguments'] if 'arguments' in node else {})[0]
        for prop, val in local_state['project'].iteritems():
            model.setProjectData(prop, val)
        if 'edgeFilePaths' in graph.graph:
            for path in graph.graph['edgeFilePaths']:
                model.getGraph().addEdgeFilePath(path,'')
        local_state['model'] = model
        getNodeState(node_name, local_state)['node'] = local_state['model'].getNodeNames()[0]
        return getNodeState(node_name, local_state)['node']


class BaseAttachmentOperation(BatchOperation):
    logger = logging.getLogger('maskgen')

    def execute(self, graph, node_name, node, connect_to_node_name, local_state={}, global_state={}):
        """
        Represent the attachment node, attaching its name to the graph
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return: node id
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: str
        """
        getNodeState(node_name, local_state)['node'] = local_state['start node name']
        if (self.logger.isEnabledFor(logging.DEBUG)):
            self.logger.debug('Attaching to node {}'.format(local_state['start node name']))
        return getNodeState(node_name, local_state)['node']


class PreProcessedMediaOperation(BatchOperation):
    logger = logging.getLogger('maskgen')

    """
        Load target media as it conforms the source image as if the this routine called the plugin.
        In this case, the target media is the result of specific external operation.
        The plugin is configured with argument file and argument names.
        The argument file is a CSV file describing the arguments used for the specific file name.
        the first column is the image file name.
        argument names are the names associated with columns 2..n of the file.
        This plugin requires 'op','software' and 'software_version' parameters as well.
        The target file is selected by sharing the same prefix as the source file from the givem
        target media directory defined in the mandatory 'directory' parameter.
    """
    def __init__(self):
        self.index = dict()

    def _fetchArguments(self, directory, node, nodename, image_file_name, arguments, global_state={}):
        import csv
        argcopy = copy.deepcopy(arguments)
        if 'argument file' in node:
            if 'argument names' not in node:
                raise ValueError("Cannot find argument names in node {}".format(nodename))
            fullfilename = os.path.join(directory, node['argument file'].format(**global_state))
            if fullfilename not in self.index:
                argnames = node['argument names']
                if not os.path.exists(fullfilename):
                    raise ValueError("Cannot find arguments file {}".format(fullfilename))
                perfileindex = dict()
                with open(fullfilename, 'r') as fp:
                    reader = csv.reader(fp, delimiter=',')
                    for row in reader:
                        imagename = row[0]
                        args = {argnames[i]: row[i + 1] for i in range(len(argnames))}
                        perfileindex[imagename] = args
                self.index[fullfilename] = perfileindex
            argcopy.update(self.index[fullfilename][image_file_name])
        return argcopy

    def execute(self, graph, node_name, node, connect_to_node_name, local_state={}, global_state={}):
        """
        Load target media as it conforms the source image as if the this routine called the plugin.
        In this case, the target media is the result of specific external operation
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return: node id
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: str
        """
        import glob
        my_state = getNodeState(node_name, local_state)
        predecessors = [getNodeState(predecessor, local_state)['node'] for predecessor in graph.predecessors(node_name) \
                        if predecessor != connect_to_node_name and 'node' in getNodeState(predecessor, local_state)]
        predecessor_state = getNodeState(connect_to_node_name, local_state)
        local_state['model'].selectImage(predecessor_state['node'])
        if 'usebaseimage' in node and node['usebaseimage']:
            base = local_state['model'].getBaseNode(local_state['model'].start)
            self.logger.debug("Using base image {0}".format(base))
            im, filename = local_state['model'].getImageAndName(base)
        else:
            self.logger.debug("Using current image")
            im, filename = local_state['model'].currentImage()
        filename = os.path.basename(filename)
        directory = node['directory'].format(**global_state)
        if not os.path.exists(directory):
            raise ValueError('Invalid directory "' + directory + '" with node ' + node_name)
        if 'copy' in node and node['copy']:
            results = [local_state['model'].currentImage()[1]]
        else:
            results = glob.glob(directory + os.path.sep + filename[0:filename.rfind('.')] + '*')
        if len(results) == 0:
            results = glob.glob(directory + os.path.sep + local_state['model'].getName() + '*')
        if len(results) == 1:
            lastNode = local_state['model'].G.get_node(predecessor_state['node'])
            softwareDetails = scenario_model.Software(node['software'], node['software version'])
            op = software_loader.getOperation(node['op'], fake=True)
            args = pickArgs(local_state,
                            global_state,
                            node_name,
                            node['arguments'] if 'arguments' in node else None,
                            op,
                            predecessors)
            if 'experiment_id' in node:
                args['experiment_id'] = node['experiment_id']
            args['skipRules'] = True
            args['sendNotifications'] = False
            if (self.logger.isEnabledFor(logging.DEBUG)):
                self.logger.debug('Execute image {} on {} with {}'.format(node['description'],
                                                                          filename,
                                                                          str(args)))
            args = self._fetchArguments(directory, node, node_name, os.path.basename(results[0]), args, global_state)
            args = processValue(MyFormatter(local_state,global_state),args, lambda x:  x)
            filetype = tool_set.fileType(filename)
            opDetails = scenario_model.Modification(node['op'],
                                                    node['description'],
                                                    software=softwareDetails,
                                                    arguments=args,
                                                    generateMask=op.generateMask,
                                                    recordMaskInComposite=op.recordMaskInComposite(filetype) if
                                                    'recordMaskInComposite' not in node else node[
                                                        'recordMaskInComposite'],
                                                    semanticGroups=node['semanticGroups'] if 'semanticGroups' in node else [],
                                                    automated='yes')

            position = ((lastNode['xpos'] + 50 if lastNode.has_key('xpos') else
                         80), (lastNode['ypos'] + 50 if lastNode.has_key('ypos') else 200))
            local_state['model'].addNextImage(results[0], mod=opDetails,
                                              sendNotifications=False, position=position)
            my_state['output'] = results[0]
            my_state['node'] = local_state['model'].nextId()
            for predecessor in predecessors:
                local_state['model'].selectImage(predecessor)
                if (self.logger.isEnabledFor(logging.DEBUG)):
                    self.logger.debug('Project {} connect {} to {}'.format(local_state['model'].getName(),
                                                                           predecessor,
                                                                           node_name))
                local_state['model'].connect(my_state['node'],
                                             sendNotifications=False,
                                             skipDonorAnalysis='skip_donor_analysis' in node and node[
                                                 'skip_donor_analysis'])
                local_state['model'].selectImage(my_state['node'])
        elif len(results) > 1:
            raise ValueError('Directory {} contains more than one matching media for {}: {}'.format(
                directory, filename, str([os.path.basename(r) for r in results])))
        else:
            raise ValueError('Directory {} does not contain a match media for {}'.format(directory, filename))
        return my_state['node']


class PluginOperation(BatchOperation):
    logger = logging.getLogger('maskgen')

    def execute(self, graph, node_name, node, connect_to_node_name, local_state={}, global_state={}):
        """
        Add a node through an operation.
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return: node id
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: str
        """
        my_state = getNodeState(node_name, local_state)

        def isDonor(edge):
            return 'donor' in edge and edge['donor']

        predecessors = [getNodeState(predecessor, local_state)['node'] \
                        for predecessor in graph.predecessors(node_name) \
                        if predecessor != connect_to_node_name and 'node' in getNodeState(predecessor, local_state) and \
                        isDonor(graph.edge[predecessor][node_name])]

        predecessor_state = getNodeState(connect_to_node_name, local_state)
        if 'node' not in predecessor_state:
            self.logger.error('{} is not valid predecessor for {}.  Is it labeled as connect:False?'.format(connect_to_node_name,node_name))
        local_state['model'].selectImage(predecessor_state['node'])
        im, filename = local_state['model'].currentImage()
        plugin_name = node['plugin']
        plugin_op = plugins.getOperation(plugin_name)
        if plugin_op is None:
            raise ValueError('Invalid plugin name "' + plugin_name + '" with node ' + node_name)
        op = software_loader.getOperation(plugin_op['name'], fake=True)
        try:
            args = pickArgs(local_state,
                            global_state,
                            node_name,
                            node['arguments'] if 'arguments' in node else None,
                            op,
                            predecessors)
        except Exception as ex:
            raise ValueError('Invalid argument ({}) for node {}'.format(ex.message, node_name))
        if 'experiment_id' in node:
            args['experiment_id'] = node['experiment_id']
        if node_name in getValue(global_state,'passthrus',[]):
            args['passthru']= True
        if 'description' in node:
            args['description'] = node['description'].format(**global_state)
        args['skipRules'] = getValue(global_state,'skipvalidation', False)
        args['sendNotifications'] = False
        args['semanticGroups'] = node['semanticGroups'] if 'semanticGroups' in node else []
        if (self.logger.isEnabledFor(logging.DEBUG)):
            self.logger.debug('Execute plugin {} on {} with {}'.format(plugin_name,
                                                                       filename,
                                                                       str(args)))
        errors, pairs = local_state['model'].mediaFromPlugin(plugin_name, **args)
        if errors is not None or (type(errors) is list and len(errors) > 0):
            real_error = None
            for error in errors:
                if error.Severity == Severity.ERROR:
                    real_error = error.Message
                    self.logger.error("Plugin " + plugin_name + " failed: {}".format(
                        error.Message
                    ))
            if real_error is not None:
                raise ValueError("Plugin " + plugin_name + " failed:" + real_error)
        my_state['node'] = pairs[0][1]
        edge  = local_state['model'].getGraph().get_edge(pairs[0][0],pairs[0][1])
        for k,v in getValue(edge,'arguments',defaultValue={}).iteritems():
            my_state[k] = v
        if (self.logger.isEnabledFor(logging.DEBUG)):
            self.logger.debug('Plugin {} returned {}'.format(plugin_name,
                                                                       str(getValue(edge,'arguments',defaultValue={}))))
        my_state['output'] = local_state['model'].getNextImageFile()
        for predecessor in predecessors:
            local_state['model'].selectImage(predecessor)
            if (self.logger.isEnabledFor(logging.DEBUG)):
                self.logger.debug('Project {} connect {} to {}'.format(local_state['model'].getName(),
                                                                       predecessor,
                                                                       node_name))
            local_state['model'].connect(my_state['node'],
                                         sendNotifications=False,
                                         skipDonorAnalysis='skip_donor_analysis' in node and node[
                                             'skip_donor_analysis'])
            local_state['model'].selectImage(my_state['node'])
        return my_state['node']


class InputMaskPluginOperation(PluginOperation):
    logger = logging.getLogger('maskgen')

    def execute(self, graph, node_name, node, connect_to_node_name, local_state={}, global_state={}):
        """
        Add a node through an operation.
        :param graph:
        :param node_name:
        :param node:
        :param connect_to_node_name:
        :param local_state:
        :param global_state:
        :return: node id
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: str
        """
        my_state = getNodeState(node_name, local_state)

        predecessors = [getNodeState(predecessor, local_state)['node'] for predecessor in graph.predecessors(node_name) \
                        if predecessor != connect_to_node_name and 'node' in getNodeState(predecessor, local_state)]
        if connect_to_node_name is None:
            predecessor_state = getNodeStateFromPredecessor(node_name, local_state, graph)
        else:
            predecessor_state = getNodeState(connect_to_node_name, local_state)
        if 'node' not in predecessor_state:
            raise ValueError('image selection operation requires a source node')
        local_state['model'].selectImage(predecessor_state['node'])
        if 'usebaseimage' in node and node['usebaseimage']:
            base = local_state['model'].getBaseNode(local_state['model'].start)
            self.logger.debug("Using base image {0}".format(base))
            im, filename = local_state['model'].getImageAndName(base)
        else:
            self.logger.debug("Using current image")
            im, filename = local_state['model'].currentImage()
        plugin_name = node['plugin']
        prnu = node['prnu'] if 'prnu' in node else False
        plugin_op = plugins.getOperation(plugin_name)
        if plugin_op is None:
            raise ValueError('Invalid plugin name "' + plugin_name + '" with node ' + node_name)
        op = software_loader.getOperation(plugin_op['name'], fake=True)
        args = pickArgs(local_state, global_state, node_name, node['arguments'] if 'arguments' in node else None, op,
                        predecessors)
        args['skipRules'] = True
        args['sendNotifications'] = False
        if (self.logger.isEnabledFor(logging.DEBUG)):
            self.logger.debug('Calling plugin {} for {} with args {}'.format(filter,
                                                                             filename,
                                                                             str(args)))
        targetfile, params = self.imageFromPlugin(plugin_name, im, filename, node_name, local_state, prnu, **args)
        if (self.logger.isEnabledFor(logging.DEBUG)):
            self.logger.debug('Plugin {} returned args {}'.format(filter,str(params)))
        my_state['output'] = targetfile
        if params is not None and type(params) == type({}):
            for k, v in params.iteritems():
                my_state[k] = v
        return predecessor_state['node']

    def resolveDonor(selfl, k, v, local_state):
        if k.lower() == 'donor':
            return os.path.join(local_state['model'].get_dir(), local_state['model'].getFileName(v))
        return v

    def imageFromPlugin(self, filter, im, filename, node_name, local_state, prnu, **kwargs):
        import tempfile
        """
          @type filter: str
          @type im: ImageWrapper
          @type filename: str
          @rtype: list of (str, list (str,str))
        """
        file = os.path.split(filename)[1]
        file = file[0:file.rfind('.')]
        target = os.path.join(tempfile.gettempdir(), file + '_' + filter + '_' + node_name + '.png')
        if file.endswith('.png'):
            shutil.copy2(filename, target)
        else:
            tool_set.openImage(filename).save(target, format='PNG')
        local_state['cleanup'].append(target)
        params = {}
        kwargs = {k: self.resolveDonor(k, v, local_state) for k, v in kwargs.iteritems()}
        try:
            if (self.logger.isEnabledFor(logging.DEBUG)):
                self.logger.debug('Calling plugin {} for {} with args {}'.format(filter,
                                                                                 filename,
                                                                                 str(kwargs)))
            extra_args, msg = plugins.callPlugin(filter, im, filename, target, **kwargs)
            if (self.logger.isEnabledFor(logging.DEBUG)):
                self.logger.debug('Plugin {} returned  {}'.format(filter, str(extra_args)))
            if extra_args is not None and type(extra_args) == type({}):
                if 'override_target' in extra_args:
                    target = extra_args.pop('override_target')
                for k, v in extra_args.iteritems():
                    # if k not in kwargs:
                    params[k] = v
        except Exception as e:
            msg = str(e)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.error(' '.join(traceback.format_exception( exc_type, exc_value, exc_traceback,limit=10)))
            raise ValueError("Plugin " + filter + " failed:" + msg)
        return target, params


class ImageSelectionPluginOperation(InputMaskPluginOperation):
    logger = logging.getLogger('maskgen')

    def imageFromPlugin(self, filter, im, filename, node_name, local_state, prnu, **kwargs):
        import tempfile
        """
          @type filter: str
          @type im: ImageWrapper
          @type filename: str
          @rtype: list of (str, list (str,str))
        """
        file = os.path.split(filename)[1]
        file = file[0:file.rfind('.')]
        target = os.path.join(tempfile.gettempdir(), file + '_' + filter + '_' + node_name + '.png')
        if filename.endswith('.png'):
            shutil.copy2(filename, target)
        else:
            tool_set.openImage(filename).save(target, format='PNG')
        local_state['cleanup'].append(target)
        params = {}
        try:
            extra_args, msg = plugins.callPlugin(filter, im, filename, target, **kwargs)
            if 'file' not in extra_args:
                raise ValueError('file key expected in result to identify chosen file')
            else:
                pick = extra_args.pop('file')
                logging.getLogger('maskgen').info('Picking file {}'.format(pick))
                getNodeState(node_name, local_state)['node'] = local_state['model'].addImage(pick, prnu=prnu)
            if extra_args is not None and type(extra_args) == type({}):
                for k, v in extra_args.iteritems():
                    if k not in kwargs:
                        params[k] = v
        except Exception as e:
            msg = str(e)
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.error(' '.join(traceback.format_exception( exc_type, exc_value, exc_traceback,limit=10)))
            raise ValueError("Plugin " + filter + " failed:" + msg)
        return target, params


batch_operations = {'BaseSelection': BaseSelectionOperation(),
                    'ImageSelection': ImageSelectionOperation(),
                    'ImageSelectionPluginOperation': ImageSelectionPluginOperation(),
                    'PluginOperation': PluginOperation(),
                    'InputMaskPluginOperation': InputMaskPluginOperation(),
                    'NodeAttachment': BaseAttachmentOperation(),
                    'PreProcessedMediaOperation': PreProcessedMediaOperation()}


def getOperationGivenDescriptor(descriptor):
    """

    :param descriptor:
    :return:
    @rtype : BatchOperation
    """
    return batch_operations[descriptor['op_type']]


def findBaseNodes(graph, node):
    predecessors = graph.predecessors(node)
    if len(predecessors) == 0:
        return [node]
    nodes = []
    for pred in predecessors:
        nodes.extend(findBaseNodes(graph, pred))
    return nodes


def findBaseImageNodes(graph, node):
    """

    :param graph:
    :param node:
    :return:
    @type graph: nx.DiGraph
    """
    return [node for node in findBaseNodes(graph, node) if
            graph.node[node]['op_type'] == 'BaseSelection']


def checkGraph(graph):
    if 'projectDescription' in graph:
        graph['projectdescription'] = graph['projectDescription']
    if 'technicalSummary' in graph:
        graph['technicalsummary'] = graph['technicalSummary']
    for item in ['projectdescription','organization','technicalsummary','name']:
        if item not in graph:
            raise ValueError('Missing {} in project graph'.format(item))

class BatchProject:
    logger = logging.getLogger('maskgen')

    G = nx.DiGraph(name="Empty")

    def __init__(self, json_data):
        """
        :param json_data:
        @type json_data: nx.DiGraph or dictionary
        """
        if isinstance(json_data, nx.Graph):
            self.G = json_data
        else:
            self.G = separate_paths(json_graph.node_link_graph(remap_links(json_data), multigraph=False, directed=True))
        checkGraph(self.G.graph)
        initial_user(maskGenPreferences,
                     username=getValue(self.G.graph,'username',
                                                      defaultValue=maskGenPreferences.get_key('username')))
        self.saveGraphImage('.')


    def _buildLocalState(self):
        local_state = {'cleanup': list()}
        local_state['project'] = {}
        for k in self.G.graph:
            if k not in ['recompress', 'name', 'edgeFilePaths']:
                local_state['project'][k] = self.G.graph[k]
        return local_state

    def getName(self):
        return self.G.graph['name'] if 'name' in self.G.graph else 'Untitled'

    def getConnectToNodes(self,op_node_name):
        connecttonodes = [predecessor for predecessor in self.G.predecessors(op_node_name)
           if getValue(self.G.edge[predecessor][op_node_name], 'source', defaultValue=False)]
        if len(connecttonodes) > 0:
            return connecttonodes
        return [predecessor for predecessor in self.G.predecessors(op_node_name)
         if self.G.node[predecessor]['op_type'] != 'InputMaskPluginOperation' and \
         not getValue(self.G.edge[predecessor][op_node_name], 'donor', defaultValue=False) and \
         getValue(self.G.edge[predecessor][op_node_name],'connect',defaultValue=True)]

    def _processQueueOfNodes(self, local_state, global_state, queue, completed):
        while len(queue) > 0:
            op_node_name = queue.pop(0)
            if op_node_name in completed:
                continue
            if op_node_name not in self.G.nodes():
                logging.getLogger('maskgen').error('Project {} missing node {}'.format(self.getName(), op_node_name))
            predecessors = list(self.G.predecessors(op_node_name))
            # skip if a predecessor is missing
            if len([pred for pred in predecessors if pred not in completed]) > 0:
                continue
            connecttonodes = self.getConnectToNodes(op_node_name)
            node = self.G.node[op_node_name]
            if len(connecttonodes) > 0 and 'source' in node:
                connect_to_node_name = node['source']
            else:
                if len(connecttonodes) == 0:
                    self.logger.info('No source connections found for {}'.format(op_node_name))
                elif len(connecttonodes) > 1:
                    self.logger.warn('More than source connection for {}, picking {} as the source'.format(op_node_name, connecttonodes[0]))
                connect_to_node_name = connecttonodes[0] if len(connecttonodes) > 0 else None
            self.logger.debug('Starting: {}'.format(op_node_name))
            self._execute_node(op_node_name, connect_to_node_name, local_state, global_state)
            completed.append(op_node_name)
            if (self.logger.isEnabledFor(logging.DEBUG)):
                self.logger.debug('Completed: {}'.format(op_node_name))
            queue.extend(self.G.successors(op_node_name))

    def _postProcessProject(self, local_state, global_state):
        recompress = self.G.graph['recompress'] if 'recompress' in self.G.graph else False
        rename = self.G.graph['rename'] if 'rename' in self.G.graph else True
        sm = local_state['model']
        if recompress:
            self.logger.debug("Run Save As")
            op = group_operations.CopyCompressionAndExifGroupOperation(local_state['model'])
            op.performOp()
        if rename:
            sm.renameFileImages()
        sm.save()
        summary_file = os.path.join(sm.get_dir(), '_overview_.png')
        ImageGraphPainter(sm.getGraph()).output(summary_file)
        if 'archives' in global_state:
            sm.export(global_state['archives'])

    def _cleanUp(self, local_state):
        for file in local_state['cleanup']:
            if os.path.exists(file):
                try:
                    os.remove(file)
                except:
                    # MS Windows?
                    continue

    def executeForProject(self, project, nodes, workdir=None, global_variables={}):
        global_state = {'project': self,
                        'workdir': project.get_dir() if workdir is None else workdir,
                        'permutegroupsmanager': PermuteGroupManager(
                            dir=project.get_dir() if workdir is None else workdir)
                        }
        if global_variables is not None:
            if type(global_variables) == str:
                global_state.update({pair[0]: pair[1] for pair in [pair.split('=') \
                                                                        for pair in global_variables.split(',')]})
            else:
                global_state.update(global_variables)
        self.loadPermuteGroups(global_state)
        self.logger.info('Building project {} with local state'.format(project.getName()))
        local_state = self._buildLocalState()
        mydata = local()
        mydata.current_local_state = local_state
        self.logger.info('Building project {} with global state: {} '.format(project.getName(),
                                                                             str(global_state)))
        local_state['model'] = project
        base_node = self._findBase()
        try:
            retain = []
	    for op_node_name in self.G.nodes():
   		op_node_data = self.G.node[op_node_name]
		if getValue(op_node_data,'global',False):
                    retain.append(op_node_name)
            completed = []
            for node in nodes:
                # establish the starting point
                local_state['start node name'] = node
                queue = [base_node]
                queue.extend([top for top in _findTops(self.G) if top != base_node])
                self._processQueueOfNodes(local_state, global_state, queue, completed)
                completed = copy.copy(retain)
            self._postProcessProject(local_state, global_state)
        except Exception as e:
            project_name = project.getName()
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.error(' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback, limit=10)))
            logging.getLogger('maskgen').error('Creation of project {} failed: {}'.format(project_name, str(e)))
            return False
        finally:
            self._cleanUp(local_state)
        return True

    def executeOnce(self, global_state=dict()):
        permuteGroupManager = global_state['permutegroupsmanager']
        permuteGroupManager.save()
        permuteGroupManager.next()
        local_state = self._buildLocalState()
        mydata = local()
        mydata.current_local_state = local_state
        self.logger.info('Building project with global state: {} '.format(str(global_state)))
        base_node = self._findBase()
        ok = False
        if base_node is None:
            self.logger.error("A suitable base node for this project {} was not found".format(self.getName()))
        try:
            self._execute_node(base_node, None, local_state, global_state)
            local_state['model'].setProjectData('batch specification name', self.getName())
            queue = [top for top in _findTops(self.G) if top != base_node]
            logging.getLogger('maskgen').info('Project {} top level nodes {}'.format(self.getName(), ','.join(queue)))
            queue.extend(self.G.successors(base_node))
            project_name = local_state['model'].getName() if 'model' in local_state else 'NA'
            self._processQueueOfNodes(local_state, global_state, queue, [base_node])
            ok = True
            self._postProcessProject(local_state,global_state)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.error(' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback, limit=10)))
            if not ok:
                logging.getLogger('maskgen').error('Creation of project {} failed: {}'.format(project_name, str(e)))
                permuteGroupManager.retainFailedState()
                if 'model' in local_state:
                    if 'removebadprojects' in global_state and not global_state['removebadprojects']:
                        local_state['model'].save()
                    else:
                        shutil.rmtree(local_state['model'].get_dir())
                return None, project_name
        finally:
            self._cleanUp(local_state)
        self.logger.info('Creation of project {} succeeded'.format(project_name))
        return local_state['model'].get_dir(), project_name

    def saveGraphImage(self, dir='.', use_id=False):
        """

        :param dir:
        :param use_id: True if the ID is used as a node name
        :return:
        """
        filename = os.path.join(dir, self.getName() + '.png')
        self._draw(use_id=use_id).write_png(filename)
        filename = os.path.join(dir, self.getName() + '.csv')
        position = 0
        with open(filename, 'w') as f:
            for nodeid in self.G.nodes():
                node = self.G.node[nodeid]
                f.write(nodeid + ',' + str(position) + '\n')
                position += 1

    colors_bytype = {'InputMaskPluginOperation': 'blue'}

    def _draw(self,use_id=False):
        import pydot
        pydot_nodes = {}
        pygraph = pydot.Dot(graph_type='digraph')
        for node_id in self.G.nodes():
            node = self.G.node[node_id]
            op_type = node['op_type']
            if use_id:
                name = node_id
            else:
                name = op_type
                if op_type in ['PluginOperation', 'InputMaskPluginOperation']:
                    name = node['plugin']
                    if 'description'  in node:
                        name = node['description']
                elif op_type in ['PreProcessedMediaOperation']:
                    name = node['op']
                    if 'description'  in node:
                        name = node['description']
            color = self.colors_bytype[op_type] if op_type in self.colors_bytype else 'black'
            pydot_nodes[node_id] = pydot.Node(node_id, label='"' + name + '"',
                                              shape='plain',
                                              color=color)
            pygraph.add_node(pydot_nodes[node_id])
        for edge_id in self.G.edges():
            node = self.G.node[edge_id[0]]
            op_type = node['op_type']
            color = self.colors_bytype[op_type] if op_type in self.colors_bytype else 'black'
            pygraph.add_edge(
                pydot.Edge(pydot_nodes[edge_id[0]], pydot_nodes[edge_id[1]], color=color))
        return pygraph

    def validate(self):
        """
        Return list of error strings
        :return:
        @rtype : List[str]
        """

        errors = []
        topcount = 0
        for top in _findTops(self.G):
            top_node = self.G.node[top]
            if top_node['op_type'] == 'BaseSelection':
                topcount += 1
        if topcount > 1:
            errors.append("More than one BaseSelection node")
        if topcount == 0:
            errors.append("Missing one BaseSelection node")

    def loadPermuteGroups(self, global_state):
        permuteGroupManager = global_state['permutegroupsmanager']
        for node_name in self.G.nodes():
            node = self.G.node[node_name]
            if 'arguments' in node:
                for name, spec in node['arguments'].iteritems():
                    specification = {'value': spec} if type(spec) != dict else spec
                    if 'permutegroup' in specification and specType(specification) not in ['value','variable']:
                        permuteGroupManager.loadParameter(specification['permutegroup'],
                                                          buildIterator(node_name + '.' + name, specification, global_state))
            if 'op_type' in node and node['op_type'] in ['BaseSelection', 'ImageSelection']:
                permutegroup = node['permutegroup'] if 'permutegroup' in node else None
                permuteGroupManager.loadParameter(permutegroup,
                                                  pickImageIterator(node,
                                                                    node_name,
                                                                    global_state))



    def _findBase(self):
        """
        Find and return top node name
        :return:
        @rtype: str
        """
        tops = _findTops(self.G)
        for top in tops:
            top_node = self.G.node[top]
            if top_node['op_type'] in ['BaseSelection', 'NodeAttachment']:
                return top
        return None

    def _execute_node(self, node_name, connect_to_node_name, local_state, global_state):
        """
        :param local_state:
        :param global_state:
        :return:
        @rtype: maskgen.scenario_model.ImageProjectModel
        """
        try:
            if (self.logger.isEnabledFor(logging.DEBUG)):
                self.logger.debug('_execute_node {} connect to {}'.format(node_name,
                                                                          str(connect_to_node_name)))
            return getOperationGivenDescriptor(self.G.node[node_name]).execute(self.G,
                                                                               node_name,
                                                                               self.G.node[node_name],
                                                                               connect_to_node_name,
                                                                               local_state=local_state,
                                                                               global_state=global_state)
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            self.logger.error(' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback, limit=10)))
            logging.getLogger('maskgen').error(str(e))
            raise e


def createGlobalState(projectDirectory, stateDirectory,
                      permuteGroupManager=None,
                      removeBadProjects=True,
                      stopOnError=False,
                      skipValidation=False,
                      fromFailedStateFile=None):
    """
    :param projectDirectory: directory for resulting projects
    :param stateDirectory:  directory for maintaining picklists and other state
    :param fromFailedStateFile: a failed permutation state file in the state directory, if available
    :return:
    @type projectDirectory: str
    @type stateDirectory: str
    @type fromFailedStateFile: str
    """
    return {'projects': projectDirectory,
            'workdir': stateDirectory,
            'removebadprojects' : removeBadProjects,
            'stoponerror': stopOnError,
            'skipvalidation': skipValidation,
            'permutegroupsmanager': permuteGroupManager if permuteGroupManager is not None else \
                                                        PermuteGroupManager(dir=stateDirectory,
                                                        fromFailedStateFile=fromFailedStateFile)}

class QueueThreadWorker:
    def __init__(self, iq):
        """

        :param iq:
        @type iq: queue.Queue
        """
        self.iq = iq

    def __executeOnce(self, globalState):
        project_directory = None
        project_name = None
        try:
            globalState['project'].loadPermuteGroups(globalState)
            project_directory, project_name = globalState['project'].executeOnce(globalState)
            globalState['permutegroupsmanager'].save()
            if project_directory is not None:
                logging.getLogger('maskgen').info('Completed {}'.format(project_directory))
            else:
                logging.getLogger('maskgen').error(
                    'Detected failure from project {}'.format(project_directory))
        except Exception as e:
            logging.getLogger('maskgen').error(
                'Due caught failure  {} from project {}'.format(str(e), project_directory))
        return project_directory, project_name

    def execute(self):
        exit = False
        while not exit:
            globalState = self.iq.get()
            if str(globalState) == 'Stop':
                exit = True
            else:
                batchProject = globalState['project']
                id = globalState['uuid']
                logging.getLogger('maskgen').info('Executing {} as {}'.format(
                    batchProject.getName(),
                    id))
                flushLogs()
                project_directory, project_name = self.__executeOnce(globalState)
                if project_directory is None and getValue(globalState,'stoponerror',defaultValue=False):
                    exit=True
                if 'notify_function' in globalState:
                    globalState['notify_function'](batchProject.getName(),id, project_directory, project_name)


def thread_worker(iq):
    """

     :param iq:
     :param oq:
     @type iq: queue.Queue
     @type notify_function: function
     """
    logging.getLogger('maskgen').info(
        'Starting Thread')
    QueueThreadWorker(iq).execute()


def updateAndInitializeGlobalState(global_state, global_variables=dict(), initializers=None):
    if global_variables is not None:
        if type(global_variables) == str and len(global_variables)>0:
            global_state.update({pair[0]: pair[1] for pair in [pair.split('=') \
                                                                    for pair in global_variables.split(',')]})
        else:
            global_state.update(global_variables)
    return loadGlobalStateInitialers(global_state,initializers)

def loadGlobalStateInitialers(global_state, initializers):
    import importlib
    if initializers is None:
        return global_state
    for initializer in initializers.split(','):
        mod_name, func_name = initializer.rsplit('.', 1)
        try:
            mod = importlib.import_module(mod_name)
            initializer_func = getattr(mod, func_name)
            global_state.update(initializer_func(global_state))
        except Exception as e:
            logging.getLogger('maskgen').error('Unable to load initializer {}: {}'.format(initializer, str(e)))
    return global_state

def do_nothing_notify(spec_name, id, project_directory, project_name):
    pass

def export_notify(url, redactions, spec_name, id, project_directory, project_name):
    import shutil
    if project_directory is None:
        return
    model = scenario_model.ImageProjectModel(os.path.join(project_directory,project_name + '.json'))
    path, error_list = model.export('.', redacted=[redaction.strip() for redaction in  redactions])
    export_manager.sync_upload(path, url)
    if len(error_list) == 0:
        shutil.rmtree(project_directory)

class WaitToFinish:
    def __init__(self, count=1, name=''):
        self.lock = Semaphore()
        self.lock.acquire()
        self.count = IntObject(count)
        self.name = name

    def wait_notify(self, spec_name, id, project_directory, project_name):
        logging.getLogger('maskgen').info('Received completion of {} as {}'.format(self.name, id))
        if self.count.decrement() == 0:
            self.lock.release()

    def wait(self):
        logging.getLogger('maskgen').info('Waiting completion {}'.format(self.name, id))
        self.lock.acquire()


def flushLogs():
    for handler in logging.getLogger('maskgen').handlers:
        handler.flush()


class BatchExecutor:
    """
    Manages multi-threaded execution of batch projects sharing the same state space.
    """
    def __init__(self,
                 results,
                 workdir='.',
                 global_variables=None,
                 initializers=None,
                 loglevel=50,
                 threads_count=1,
                 skipValidation=False,
                 removeBadProjects=True,
                 stopOnError=False,
                 fromFailedStateFile=None,
                 testMode=False,
                 passthrus=[]):
        """
        :param results:  project results directory
        :param workdir:  working directory for pool lists and other permutation states
        :param global_variables: dictionary of global variables (or a comma-separated list of name=value)
        :param initializers: list of functions (or a comma-separated list of namespace qualified function names
        :param loglevel: 0-100 (see python logging)
        :param threads_count: number of threads
        :param removeBadProjects: projects that failed are removed
        :param stopOnError: stop processing if an error occurs
        :param fromFailedStateFile: a file containing failed state of permutations groups from which to run
        :param passthrus: list of plugins to pass thru / do not run
        :param skipValidation: If True, do not validate project after completion
        @type results : str
        @type workdir : str
        @type global_variables : dict
        @type initializers : list of functions
        @type loglevel: int
        @type threads_count: int
        @type removeBadProjects: bool
        @type stopOnError: bool
        @type fromFailedStateFile: str
        @type passthru: list of str
        """
        if not os.path.exists(results):
            os.mkdir(results)
        if not os.path.isdir(results):
            logging.getLogger('maskgen').error('invalid directory for results: ' + results)
            return
        manager = plugins.loadPlugins()
        if testMode:
            plugins.EchoInterceptor(manager.getBroker())
        self.removeBadProjects = removeBadProjects
        self.__setupThreads(threads_count)
        self.workdir = os.path.abspath(workdir)
        loadCustomFunctions()
        set_logging(workdir)
        logging.getLogger('maskgen').info('Setting working directory to {}'.format(self.workdir))
        if loglevel is not None:
            logging.getLogger('maskgen').setLevel(logging.INFO if loglevel is None else int(loglevel))
            set_logging_level(logging.INFO if loglevel is None else int(loglevel))
        self.permutegroupsmanager = PermuteGroupManager(dir=self.workdir,fromFailedStateFile=fromFailedStateFile)
        self.initialState = createGlobalState(results,
                                              self.workdir,
                                              permuteGroupManager=self.permutegroupsmanager,
                                              removeBadProjects=removeBadProjects,
                                              stopOnError=stopOnError,
                                              fromFailedStateFile=fromFailedStateFile,
                                              skipValidation=skipValidation)
        self.initialState = updateAndInitializeGlobalState(self.initialState,
                                                           global_variables=global_variables,
                                                           initializers=initializers)
        if len(passthrus) > 0:
            self.initialState.update({'passthrus':passthrus})

    def __setupThreads(self, threads_count):
        self.threads = []
        name = 0
        self.iq = queue.Queue(threads_count)
        for i in range(int(threads_count)):
            name += 1
            t = Thread(target=thread_worker, name=str(name), kwargs={'iq': self.iq})
            self.threads.append(t)
            t.start()

    def runProject(self, batchProject, count=1, notify_function=do_nothing_notify):

        """
        Run in a thread
        :param batchProject:
        :param count:
        :return:
        @type batchProject: BatchProject
        """
        import uuid
        logging.getLogger('maskgen').info('Queue up {} projects'.format(count))
        while count > 0:
            myid = uuid.uuid4()
            globalState = {
                'project': batchProject,
                'uuid': myid,
                'notify_function': notify_function
            }
            globalState.update(self.initialState)
            logging.getLogger('maskgen').info('Queueing {} as {}'.format(batchProject.getName(), myid))
            self.iq.put(globalState)
            count -= 1
        return uuid

    def runProjectLocally(self, batchProject, notify_function=do_nothing_notify):
        """
        Run in a in the this current thread
        :param batchProject:
        :param count:
        :return:
        @type batchProject: BatchProject
        """
        import uuid
        myid = uuid.uuid4()
        globalState = {
            'project': batchProject,
            'uuid': myid
        }
        globalState.update(self.initialState)
        logging.getLogger('maskgen').info('Running {} as {}'.format(batchProject.getName(), myid))
        batchProject.loadPermuteGroups(globalState)
        project_directory, project_name = batchProject.executeOnce(globalState)
        notify_function(batchProject.getName(), myid, project_directory, project_name)
        return project_directory, project_name

    def finish(self):
        """
        Send termination and wait for threads to finish
        :return:
        """
        logging.getLogger('maskgen').info('Stopping Threads')
        for thread in self.threads:
            self.iq.put('Stop')
        logging.getLogger('maskgen').info('Waiting for Threads termination')
        for thread in self.threads:
            thread.join()
        logging.getLogger('maskgen').info('Thread termination complete')


def main(argv=sys.argv[1:]):
    global threadGlobalState
    parser = argparse.ArgumentParser()
    parser.add_argument('--specification', required=True, help='JSON File')
    parser.add_argument('--count', required=False, help='number of projects to build')
    parser.add_argument('--threads', required=False, help='number of projects to build')
    parser.add_argument('--workdir', required=False,
                        help='directory to maintain and look for lock list, logging and permutation files')
    parser.add_argument('--projects', required=True, help='project results directory')
    parser.add_argument('--loglevel', required=False, help='log level')
    parser.add_argument('--graph', required=False, action='store_true', help='create graph PNG file')
    parser.add_argument('--global_variables', required=False, help='global state initialization')
    parser.add_argument('--initializers', required=False, help='global state initialization')
    parser.add_argument('--from_state', required=False, help='permutation state file')
    parser.add_argument('--export',required=False, help='export to given s3 url')
    parser.add_argument('--keep_failed',required=False,action='store_true')
    parser.add_argument('--stop_on_error', required=False, action='store_true')
    parser.add_argument('--skip_validation', required=False, action='store_true')
    parser.add_argument('--test', required=False, action='store_true')
    parser.add_argument('--passthrus', required=False, default='none', help='plugins to passthru')
    parser.add_argument('--redactions', required=False, default='', help='comma separated list of file argument to exclude from export')
    args = parser.parse_args(argv)
    prefLoader = MaskGenLoader()

    if prefLoader.get_key('skip_compare',default_value=False):
        logging.getLogger('maskgen').ERROR('skip_compare is set.  This should not be used in batch mode')
        return

    batchProject = loadJSONGraph(args.specification)
    be = BatchExecutor(args.projects,
                       workdir='.' if args.workdir is None or not os.path.exists(args.workdir) else args.workdir,
                       global_variables=args.global_variables,
                       initializers=args.initializers,
                       threads_count=int(args.threads) if args.threads else 1,
                       loglevel=args.loglevel,
                       stopOnError=args.stop_on_error,
                       removeBadProjects=not args.keep_failed,
                       fromFailedStateFile=args.from_state,
                       testMode=args.test,
                       skipValidation=args.skip_validation,
                       passthrus=args.passthrus.split(',') if args.passthrus != 'none' else [])

    notify = partial(export_notify,args.export, args.redactions.split(',')) if args.export is not None else do_nothing_notify

    if args.graph:
        batchProject.saveGraphImage(be.workdir)
    try:
        be.runProject(batchProject,
                      count=int(args.count) if args.count else 1,
                      notify_function=notify
                      )
    finally:
        be.finish()


if __name__ == '__main__':
    main(sys.argv[1:])
