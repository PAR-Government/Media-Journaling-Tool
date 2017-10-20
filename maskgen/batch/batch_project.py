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
from maskgen import plugins
from maskgen import group_operations
import logging
from threading import Thread, local, currentThread
import numpy as np
from maskgen.batch.permutations import *
import time
from datetime import datetime
from maskgen.loghandling import set_logging


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


def loadJSONGraph(pathname):
    with open(pathname, "r") as f:
        json_data = {}
        try:
            json_data = json.load(f, encoding='utf-8')
            G = json_graph.node_link_graph(json_data, multigraph=False, directed=True)
        except  ValueError:
            json_data = json.load(f)
            G = json_graph.node_link_graph(json_data, multigraph=False, directed=True)
        return BatchProject(G, json_data)
    return None


def buildIterator(spec_name, param_spec, global_state, random_selection=False):
    """
    :param param_spec: argument specification
    :param random_selection: produce a continuous stream of random selections
    :return: a iterator function to construct an iterator over possible values
    """
    if param_spec['type'] == 'list':
        if not random_selection:
            return ListPermuteGroupElement(spec_name, param_spec['values'])
        else:
            return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: random.choice(param_spec['values'])))
    elif 'int' in param_spec['type']:
        v = param_spec['type']
        vals = [int(x) for x in v[v.rfind('[') + 1:-1].split(':')]
        beg = vals[0] if len(vals) > 0 else 0
        end = vals[1] if len(vals) > 1 else beg + 1
        if not random_selection:
            increment = 1
            if len(vals) > 2:
                increment = vals[2]
            return IteratorPermuteGroupElement(spec_name, lambda: xrange(beg, end + 1, increment).__iter__())
        else:
            return PermuteGroupElement(spec_name, randomGeneratorFactory(lambda: random.randint(beg, end)))
    elif 'float' in param_spec['type']:
        v = param_spec['type']
        vals = [float(x) for x in v[v.rfind('[') + 1:-1].split(':')]
        beg = vals[0] if len(vals) > 0 else 0
        end = vals[1] if len(vals) > 1 else beg + 1.0
        if not random_selection:
            increment = 1
            if len(vals) > 2:
                increment = vals[2]
            return IteratorPermuteGroupElement(spec_name, lambda: np.arange(beg, end, increment).__iter__())
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


def loadCustomFunctions():
    import pkg_resources
    for p in pkg_resources.iter_entry_points("maskgen_specs"):
        logging.getLogger('maskgen').info('load spec ' + p.name)
        pluginSpecFuncs[p.name] = p.load()


def callPluginSpec(specification, local_state):
    if specification['name'] not in pluginSpecFuncs:
        raise ValueError("Invalid specification name:" + str(specification['name']))
    if 'state_name' in specification:
        if specification['state_name'] not in local_state:
            local_state[specification['state_name']] = dict()
        return pluginSpecFuncs[specification['name']](specification['parameters'],
                                                      state=local_state[specification['state_name']])
    return pluginSpecFuncs[specification['name']](specification['parameters'])


def executeParamSpec(specification_name, specification, global_state, local_state, node_name, predecessors):
    import copy
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
        return os.path.join(local_state['model'].get_dir(), local_state['model'].getGraph().get_edge_image(source,
                                                                                                           target,
                                                                                                           'maskname')[
            1])
    elif specification['type'] == 'value':
        return specification['value']
    elif specification['type'] == 'variable':
        if 'permutegroup' in specification:
            source_spec = copy.copy(getNodeState(specification['source'], local_state)[specification['name']])
            source_spec['permutegroup'] = specification['permutegroup']
            return pickArg(source_spec, node_name, specification_name, global_state, local_state)
        else:
            return getNodeState(specification['source'], local_state)[specification['name']]
    elif specification['type'] == 'donor':
        if 'source' in specification:
            if specification['source'] == 'base':
                # return  local_state['model'].getImageAndName(local_state['model'].getBaseNode(local_state['model'].start))[1]
                return local_state['model'].getBaseNode(local_state['model'].start)
            return getNodeState(specification['source'], local_state)['node']
        return random.choice(predecessors)
    elif specification['type'] == 'imagefile':
        source = getNodeState(specification['source'], local_state)['node']
        return local_state['model'].getGraph().get_image(source)[1]
    elif specification['type'] == 'input':
        return getNodeState(specification['source'], local_state)['output']
    elif specification['type'] == 'plugin':
        return callPluginSpec(specification, local_state)
    elif specification['type'].startswith('global'):
        return global_state[specification['name']]
    return pickArg(specification, node_name, specification_name, global_state, local_state)


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


def working_abs_file(global_state, filename):
    return os.path.join(global_state['workdir'] if 'workdir' in global_state else '.', filename)


def pickImageIterator(specification, spec_name, global_state):
    if 'picklists' not in global_state:
        global_state['picklists'] = dict()
    picklist_name = specification['picklist'] if 'picklist' in specification else spec_name
    if picklist_name not in global_state['picklists']:
        element = FilePermuteGroupElement(spec_name,
                                          specification['image_directory'],
                                          tracking_filename=picklist_name + '.txt')
        global_state['picklists'][picklist_name] = element
    else:
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
    def execute(self, graph, node_name, node, connect_to_node_name, local_state={}, global_state={}):
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
        @type local_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        manager = global_state['permutegroupsmanager']
        pick = manager.current(node['permutegroup'] if 'permutegroup' in node else None,
                               node_name)
        logging.getLogger('maskgen').info('Thread {} picking file {}'.format(currentThread().getName(), pick))
        getNodeState(node_name, local_state)['node'] = local_state['model'].addImage(pick)
        return local_state['model']


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
        :return:
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        manager = global_state['permutegroupsmanager']
        pick = manager.current(node['permutegroup'] if 'permutegroup' in node else None,
                               node_name)
        logging.getLogger('maskgen').info('Thread {} picking file {}'.format(currentThread().getName(), pick))
        pick_file = os.path.split(pick)[1]
        name = pick_file[0:pick_file.rfind('.')]
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
        logging.getLogger('maskgen').info("Thread {} build project {}".format(currentThread().getName(), pick_file))
        local_state['model'] = scenario_model.createProject(dir,
                                                            name=name,
                                                            base=file_path_in_project,
                                                            suffixes=tool_set.suffixes)[0]
        for prop, val in local_state['project'].iteritems():
            local_state['model'].setProjectData(prop, val)
        getNodeState(node_name, local_state)['node'] = local_state['model'].getNodeNames()[0]
        return local_state['model']


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
        :return:
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        getNodeState(node_name, local_state)['node'] = local_state['start node name']
        if (self.logger.isEnabledFor(logging.DEBUG)):
            self.logger.debug('Thread {} attaching to node {}'.format(currentThread().getName(), local_state['start node name']))
        return local_state['model']


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
        :return:
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        my_state = getNodeState(node_name, local_state)

        predecessors = [getNodeState(predecessor, local_state)['node'] \
                        for predecessor in graph.predecessors(node_name) \
                        if predecessor != connect_to_node_name and 'node' in getNodeState(predecessor, local_state)]

        predecessor_state = getNodeState(connect_to_node_name, local_state)
        local_state['model'].selectImage(predecessor_state['node'])
        im, filename = local_state['model'].currentImage()
        plugin_name = node['plugin']
        plugin_op = plugins.getOperation(plugin_name)
        if plugin_op is None:
            raise ValueError('Invalid plugin name "' + plugin_name + '" with node ' + node_name)
        op = software_loader.getOperation(plugin_op['name'], fake=True)
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
            self.logger.debug('Thread {} Execute plugin {} on {} with {}'.format(currentThread().getName(),
                                                                             plugin_name,
                                                                             filename,
                                                                             str(args)))
        errors, pairs = local_state['model'].imageFromPlugin(plugin_name, **args)
        if errors is not None or (type(errors) is list and len(errors) > 0):
            raise ValueError("Plugin " + plugin_name + " failed:" + str(errors))
        my_state['node'] = pairs[0][1]
        for predecessor in predecessors:
            local_state['model'].selectImage(predecessor)
            if (self.logger.isEnabledFor(logging.DEBUG)):
                self.logger.debug('Thread {} project {} connect {} to {}'.format(currentThread().getName(),
                                                                                 local_state['model'].getName(),
                                                                                 predecessor,
                                                                                 node_name))
            local_state['model'].connect(my_state['node'],
                                         sendNotifications=False,
                                         skipDonorAnalysis='skip_donor_analysis' in node and node[
                                             'skip_donor_analysis'])
            local_state['model'].selectImage(my_state['node'])
        return local_state['model']


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
        :return:
        @type graph: nx.DiGraph
        @type node_name : str
        @type node: Dict
        @type connect_to_node_name : str
        @type global_state: Dict
        @type global_state: Dict
        @rtype: scenario_model.ImageProjectModel
        """
        my_state = getNodeState(node_name, local_state)

        predecessors = [getNodeState(predecessor, local_state)['node'] for predecessor in graph.predecessors(node_name) \
                        if predecessor != connect_to_node_name and 'node' in getNodeState(predecessor, local_state)]
        predecessor_state = getNodeState(connect_to_node_name, local_state)
        local_state['model'].selectImage(predecessor_state['node'])
        im, filename = local_state['model'].currentImage()
        plugin_name = node['plugin']
        plugin_op = plugins.getOperation(plugin_name)
        if plugin_op is None:
            raise ValueError('Invalid plugin name "' + plugin_name + '" with node ' + node_name)
        op = software_loader.getOperation(plugin_op['name'], fake=True)
        args = pickArgs(local_state, global_state, node_name, node['arguments'] if 'arguments' in node else None, op,
                        predecessors)
        args['skipRules'] = True
        args['sendNotifications'] = False
        targetfile, params = self.imageFromPlugin(plugin_name, im, filename, node_name, local_state, **args)
        my_state['output'] = targetfile
        if params is not None and type(params) == type({}):
            for k, v in params.iteritems():
                my_state[k] = v
        return local_state['model']

    def resolveDonor(selfl, k, v, local_state):
        if k.lower() == 'donor':
            return os.path.join(local_state['model'].get_dir(),local_state['model'].getFileName(v))
        return v

    def imageFromPlugin(self, filter, im, filename, node_name, local_state, **kwargs):
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
            tool_set.openImageFile(filename).save(target, format='PNG')
        local_state['cleanup'].append(target)
        params = {}
        kwargs = {k: self.resolveDonor(k, v, local_state) for k, v in kwargs.iteritems()}
        try:
            if (self.logger.isEnabledFor(logging.DEBUG)):
                    self.logger.debug('Thread {} calling plugin {} for {} with args {}'.format(currentThread().getName(),
                                                                                        filter,
                                                                                        filename,
                                                                                       str(kwargs)))
            extra_args, msg = plugins.callPlugin(filter, im, filename, target, **kwargs)
            if extra_args is not None and type(extra_args) == type({}):
                for k, v in extra_args.iteritems():
                    #if k not in kwargs:
                    params[k] = v
        except Exception as e:
            msg = str(e)
            raise ValueError("Plugin " + filter + " failed:" + msg)
        return target, params


class ImageSelectionPluginOperation(InputMaskPluginOperation):
    logger = logging.getLogger('maskgen')

    def imageFromPlugin(self, filter, im, filename, node_name, local_state, **kwargs):
        import tempfile
        """
          @type filter: str
          @type im: ImageWrapper
          @type filename: str
          @rtype: list of (str, list (str,str))
        """
        file = os.path.split(filename)[1]
        file = file[0:file.rfind('.')]
        target = os.path.join(tempfile.gettempdir(), file + '_' + filter+ '_' + node_name + '.png')
        if filename.endswith('.png'):
            shutil.copy2(filename, target)
        else:
            tool_set.openImageFile(filename).save(target, format='PNG')
        local_state['cleanup'].append(target)
        params = {}
        try:
            extra_args, msg = plugins.callPlugin(filter, im, filename, target, **kwargs)
            if 'file' not in extra_args:
                raise ValueError('file key expected in result to identify chosen file')
            else:
                pick = extra_args.pop('file')
                logging.getLogger('maskgen').info('Thread {} picking file {}'.format(currentThread().getName(), pick))
                getNodeState(node_name, local_state)['node'] = local_state['model'].addImage(pick)
            if extra_args is not None and type(extra_args) == type({}):
                for k, v in extra_args.iteritems():
                    if k not in kwargs:
                        params[k] = v
        except Exception as e:
            msg = str(e)
            raise ValueError("Plugin " + filter + " failed:" + msg)
        return target, params


batch_operations = {'BaseSelection': BaseSelectionOperation(),
                    'ImageSelection': ImageSelectionOperation(),
                    'ImageSelectionPluginOperation': ImageSelectionPluginOperation(),
                    'PluginOperation': PluginOperation(),
                    'InputMaskPluginOperation': InputMaskPluginOperation(),
                    'NodeAttachment': BaseAttachmentOperation()}


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


class BatchProject:
    logger = logging.getLogger('maskgen')

    G = nx.DiGraph(name="Empty")

    def __init__(self, G, json_data):
        """
        :param G:
        @type G: nx.DiGraph
        """
        self.G = G
        self.json_data = json_data
        tool_set.setPwdX(tool_set.CustomPwdX(self.G.graph['username']))

    def _buildLocalState(self):
        local_state = {'cleanup' :list()}
        local_state['project'] = {}
        for k in self.G.graph:
            if k not in ['recompress', 'name']:
                local_state['project'][k] = self.G.graph[k]
        return local_state

    def getName(self):
        return self.G.graph['name'] if 'name' in self.G.graph else 'Untitled'

    def executeForProject(self, project, nodes):
        recompress = self.G.graph['recompress'] if 'recompress' in self.G.graph else False
        global_state = {'picklists_files': {},
                        'project': self,
                        'workdir': project.get_dir(),
                        'count': None,
                        'permutegroupsmanager': PermuteGroupManager(dir=project.get_dir())
                        }
        self.logger.info('Thread {} building project {} with local state'.format(currentThread().getName(),
                                                                                   project.getName()))
        local_state = self._buildLocalState()
        mydata = local()
        mydata.current_local_state = local_state
        self.logger.info('Thread {} building project {} with global state: {} '.format(currentThread().getName(),
                                                                                       project.getName(),
                                                                                    str(global_state)))
        local_state['model'] = project
        base_node = self._findBase()
        try:
            for node in nodes:
                # establish the starting point
                local_state['start node name'] = node
                completed = []
                queue = [base_node]
                queue.extend(self.G.successors(base_node))
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

                    connect_to_node_name = connecttonodes[0] if len(connecttonodes) > 0 else None
                    self.logger.debug('{} Starting: {}'.format(currentThread().getName(), op_node_name))
                    self._execute_node(op_node_name, connect_to_node_name, local_state, global_state)
                    completed.append(op_node_name)
                    self.logger.debug('{} Completed: {}'.format(currentThread().getName(), op_node_name))
                    queue.extend(self.G.successors(op_node_name))
            if recompress:
                self.logger.debug("Run Save As")
                op = group_operations.CopyCompressionAndExifGroupOperation(project)
                op.performOp()
            local_state['model'].renameFileImages()
            if 'archives' in global_state:
                project.export(global_state['archives'])
        except Exception as e:
            project_name = project.getName()
            logging.getLogger('maskgen').error('Creation of project {} failed: {}'.format(project_name, str(e)))
            return False
        finally:
            for file in local_state['cleanup']:
                if os.path.exists(file):
                    os.remove(file)
        return True

    def executeOnce(self, global_state=dict()):
        # print 'next ' + currentThread().getName()
        global_state['permutegroupsmanager'].save()
        global_state['permutegroupsmanager'].next()
        recompress = self.G.graph['recompress'] if 'recompress' in self.G.graph else False
        local_state = self._buildLocalState()
        mydata = local()
        mydata.current_local_state = local_state
        self.logger.info('Thread {} building project with global state: {} '.format(currentThread().getName(),
                                                                                    str(global_state)))
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
                node = self.G.node[op_node_name]
                if len(connecttonodes) > 0 and 'source' in node:
                    connect_to_node_name = node['source']
                else:
                    connect_to_node_name = connecttonodes[0] if len(connecttonodes) > 0 else None
                self._execute_node(op_node_name, connect_to_node_name, local_state, global_state)
                completed.append(op_node_name)
                if (self.logger.isEnabledFor(logging.DEBUG)):
                    self.logger.debug('{} Completed: {}'.format(currentThread().getName(), op_node_name))
                queue.extend(self.G.successors(op_node_name))
            if recompress:
                self.logger.debug("Run Save As")
                op = group_operations.CopyCompressionAndExifGroupOperation(local_state['model'])
                op.performOp()
            local_state['model'].renameFileImages()
            if 'archives' in global_state:
                local_state['model'].export(global_state['archives'])
        except Exception as e:
            project_name = local_state['model'].getName() if 'model' in local_state else 'NA'
            logging.getLogger('maskgen').error('Creation of project {} failed: {}'.format(project_name, str(e)))
            if 'model' in local_state:
                shutil.rmtree(local_state['model'].get_dir())
            return None
        finally:
            for file in local_state['cleanup']:
                if os.path.exists(file):
                    os.remove(file)
        return local_state['model'].get_dir()

    def dump(self, global_state):
        filename = working_abs_file(global_state, self.getName() + '.png')
        self._draw().write_png(filename)
        filename = self.getName() + '.csv'
        position = 0
        with open(filename, 'w') as f:
            for node in self.json_data['nodes']:
                f.write(node['id'] + ',' + str(position) + '\n')
                position += 1

    colors_bytype = {'InputMaskPluginOperation': 'blue'}

    def _draw(self):
        import pydot
        pydot_nodes = {}
        pygraph = pydot.Dot(graph_type='digraph')
        for node_id in self.G.nodes():
            node = self.G.node[node_id]
            name = op_type = node['op_type']
            if op_type in ['PluginOperation', 'InputMaskPluginOperation']:
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
        for top in self._findTops():
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
                    if 'permutegroup' in spec and spec['type'] != 'variable':
                        permuteGroupManager.loadParameter(spec['permutegroup'],
                                                          buildIterator(node_name + '.' + name, spec, global_state))
            if 'op_type' in node and node['op_type'] in ['BaseSelection', 'ImageSelection']:
                permutegroup = node['permutegroup'] if 'permutegroup' in node else None
                permuteGroupManager.loadParameter(permutegroup,
                                                  pickImageIterator(node,
                                                                    node_name,
                                                                    global_state))

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
                self.logger.debug('_execute_node {}  by {} connect to {}'.format(node_name, currentThread().getName(),
                                                                             str(connect_to_node_name)))
            return getOperationGivenDescriptor(self.G.node[node_name]).execute(self.G,
                                                                               node_name,
                                                                               self.G.node[node_name],
                                                                               connect_to_node_name,
                                                                               local_state=local_state,
                                                                               global_state=global_state)
        except Exception as e:
            logging.getLogger('maskgen').error(str(e))
            raise e


def getBatch(jsonFile, loglevel=50):
    """
    :param jsonFile:
    :return:
    @return BatchProject
    """
    FORMAT = '%(asctime)-15s %(message)s'
    logging.basicConfig(format=FORMAT, level=50 if loglevel is None else int(loglevel))
    logging.getLogger('maskgen').setLevel(logging.INFO if loglevel is None else int(loglevel))
    return loadJSONGraph(jsonFile)


def thread_worker(globalState=dict()):
    # import copy
    count = globalState['count']
    permutegroupsmanager = globalState['permutegroupsmanager']
    if count is not None:
        logging.getLogger('maskgen').info(
            'Starting worker thread {}. Current count is {}'.format(currentThread().getName(), count.value))
    while ((count and count.decrement() > 0) or (count is None and permutegroupsmanager.hasNext())):
        try:
            project_directory = globalState['project'].executeOnce(globalState)
            if project_directory is not None:
                logging.getLogger('maskgen').info('Thread {} Completed {}'.format(currentThread().getName(),
                                                                                  project_directory))
            else:
                logging.getLogger('maskgen').error(
                    'Exiting thread {} due to failure to create project'.format(currentThread().getName()))
                break
        except Exception as e:
            logging.getLogger('maskgen').info('Completed thread: ' + str(e))

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

def main():
    global threadGlobalState
    parser = argparse.ArgumentParser()
    parser.add_argument('--json', required=True, help='JSON File')
    parser.add_argument('--count', required=False, help='number of projects to build')
    parser.add_argument('--threads', required=False, help='number of projects to build')
    parser.add_argument('--workdir', required=False,
                        help='directory to maintain and look for lock list, logging and permutation files')
    parser.add_argument('--results', required=True, help='project results directory')
    parser.add_argument('--loglevel', required=False, help='log level')
    parser.add_argument('--graph', required=False, action='store_true', help='create graph PNG file')
    parser.add_argument('--global_variables', required=False, help='global state initialization')
    parser.add_argument('--initializers', required=False, help='global state initialization')
    args = parser.parse_args()
    if not os.path.exists(args.results) or not os.path.isdir(args.results):
        logging.getLogger('maskgen').error('invalid directory for results: ' + args.results)
        return
    loadCustomFunctions()
    batchProject = getBatch(args.json, loglevel=args.loglevel)
    picklists_files = {}
    workdir = '.' if args.workdir is None or not os.path.exists(args.workdir) else args.workdir
    set_logging(workdir)
    threadGlobalState = {'projects': args.results,
                         'picklists_files': picklists_files,
                         'project': batchProject,
                         'workdir': workdir,
                         'count': IntObject(int(args.count)) if args.count else None,
                         'permutegroupsmanager': PermuteGroupManager(dir=workdir)
                         }
    gv = args.global_variables if args.global_variables is not None else ''
    threadGlobalState.update({ pair[0]:pair[1] for pair in [pair.split('=') for pair in  gv.split(',')]})
    loadGlobalStateInitialers(threadGlobalState,args.initializers)

    batchProject.loadPermuteGroups(threadGlobalState)
    if args.graph is not None:
        batchProject.dump(threadGlobalState)
    threads_count = args.threads if args.threads else 1
    threads = []
    name = 1
    kwargs = {'global_state':threadGlobalState}
    for i in range(int(threads_count)):
        name += 1
        t = Thread(target=thread_worker, name=str(name),kwargs=kwargs)
        threads.append(t)
        t.start()
    for thread in threads:
        thread.join()
    for k, fp in picklists_files.iteritems():
        fp.close()


if __name__ == '__main__':
    main()
