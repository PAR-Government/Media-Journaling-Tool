# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from maskgen.software_loader import getOperations, SoftwareLoader, getRule,strip_version
from maskgen.support import getValue
from maskgen.tool_set import fileType, openImage, openImageFile, validateAndConvertTypedValue
from maskgen.image_graph import ImageGraph, GraphProxy
import os
from collections import namedtuple
from abc import ABCMeta, abstractmethod
from enum import Enum
from maskgen import MaskGenLoader

global_loader = SoftwareLoader()

class Severity(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

ValidationMessage = namedtuple('ValidationMessage', ['Severity', 'Start', 'End', 'Message', 'Module'], verbose=False)

def hasErrorMessages(validationMessageList, contentCheck=lambda x: False):
    """
    True if messages as errors and contentCheck(Message)
    :param validationMessageList:
    :param contentCheck: additional content check function
    :return:
    @type validationMessageList: list of ValidationMessage
    @:rtype: bool
    """
    if validationMessageList is None:
        return False
    for msg in validationMessageList:
        if msg.Severity == Severity.ERROR and contentCheck(msg.Message):
            return True
    return False

def sortMessages(validationMessageList):
    return sorted(validationMessageList,key=lambda x: (Severity.CRITICAL.value - x.Severity.value,x.Start,x.End, x.Module, x.Message))

def removeErrorMessages(validationMessageList, removeSelector=lambda x: False):
    """
    Remove  error messages selected by the selector
    :param validationMessageList:
    :param removeSelector: indicator for messages to remove
    :return:
    @type validationMessageList: list of ValidationMessage
    @:rtype: bool
    """
    if validationMessageList is None:
        return None
    return [msg for msg in validationMessageList if not removeSelector(msg.Message)]

class ValidationAPI(object):
    __metaclass__ = ABCMeta

    def __init__(self, preferences):
        """

        :param preferences:
        :return:
        @type preferences: MaskGenLoader
        """
        self.preferences = preferences
        pass

    @abstractmethod
    def isConfigured(self):
        """
        :return: return true if validator is configured an usable
        @rtype: bool
        """
        return False

    @abstractmethod
    def isExternal(self):
        return False

    def reload(self):
        """
        Reload configuratio
        :return:
        """
        pass

    def check_graph(self, graph):
        """
        Graph meta-data level errors only
        :param graph: image graph
        :return: list of (severity,str)
        @type graph: ImageGraph
        @rtype: list of (severity,str)
         """
        return []

    def check_edge(self, op, graph, frm, to):
        """
        :param op: Operation structure
        :param graph: image graph
        :param frm: edge source
        :param to:  edge target
        :return: list of (severity,str)
        @type op: Operation
        @type graph: ImageGraph
        @type frm: str
        @type to: str
        @rtype: list of (Severity,str)
        """
        return []

    def check_node(self, node, graph):
        """
        :param node: node id
        :param graph: image graph
        :return: list of (severity,str)
        @type node: str
        @type graph: ImageGraph
        @rtype: list of (Severity,str)
        """
        return []

    @abstractmethod
    def test(self):
        """
        :return: Error message if system is not configured properly otherwise None
        @rtype: str
        """

    def get_journal_exporttime(self, journalname):
        """
        :param journalname:  name of the journal
        :return: export time of journal
        @type journalname: str
        @rtype: str
        """


def allRegisteredSubclassesSelector():
    return [subclass for subclass in ABCMeta.__subclasses__(ValidationAPI)
            if subclass != ValidationAPIComposite]


def setValidators(preferences, validators):
    """
    :param validators:
    :return:
    @type  list of class(ValidationAPI)
    """
    preferences['validation_apis'] = [
        item.__module__ + '.' + item.__name__ for item in validators]


def getClassFromName(fullName):
    import importlib
    className = fullName[fullName.rfind('.') + 1:]
    moduleName = fullName[0:fullName.rfind('.')]
    module = importlib.import_module(moduleName)
    return getattr(module, className)


def getRegisteredValidatorClasses(preferences):
    """

    :param selectorFunction:
    :return:
    @rtype selectorFunction: (MaskGenLoader) -> list of class(ValidationAPI)
    """
    import importlib
    names = preferences['validation_apis'] if 'validation_apis' in preferences else None
    if names is None:
        return allRegisteredSubclassesSelector()
    return [
        getClassFromName(name) for name in names
        ]


class ValidationAPIComposite(ValidationAPI):
    def __init__(self, preferences, external=False):
        self.preferences = preferences
        self.external = external
        self.instances = []

        selector = getRegisteredValidatorClasses(self.preferences)
        for subclass in selector:
            instance = subclass(self.preferences)
            if instance.isConfigured() and (not instance.isExternal() or self.external):
                self.instances.append(instance)

    def _get_subclassinstances(self):
        return self.instances

    def isConfigured(self):
        """
        :return: return true if validator is configured an usable
        @rtype: bool
        """
        return len([subclassinstance for subclassinstance in self._get_subclassinstances()]) > 0

    def isExternal(self):
        result = False
        for subclassinstance in self._get_subclassinstances():
            result |= subclassinstance.isExternal()
        return result

    def check_edge(self, op, graph, frm, to):
        """
        :param op: Operation structure
        :param graph: image graph
        :param frm: edge source
        :param to:  edge target
        :return:
        @type op: Operation
        @type graph: ImageGraph
        @type frm: str
        @type to: str
        """
        result = []
        for subclassinstance in self._get_subclassinstances():
            result.extend(subclassinstance.check_edge(op, graph, frm, to))
        return result

    def check_graph(self, graph):
        """
        Graph meta-data level errors only
        :param graph: image graph
        :return:
        @type graph: ImageGraph
        """
        result = []
        for subclassinstance in self._get_subclassinstances():
            result.extend(subclassinstance.check_graph(graph))
        return result

    def check_node(self, node, graph):
        """
        :param node: node id
        :param graph: image graph
        :return:
        @type node: str
        @type graph: ImageGraph
        """
        result = []
        for subclassinstance in self._get_subclassinstances():
            result.extend(subclassinstance.check_node(node, graph))
        return result

    def reload(self):
        """
        :return:
        """
        for subclassinstance in self._get_subclassinstances():
            subclassinstance.reload()

    def test(self):
        """
        :return: Error message if system is not configured properly otherwise None
        @rtype: str
        """
        for subclassinstance in self._get_subclassinstances():
            result = subclassinstance.test()
            if result is not None:
                return result

    def get_journal_exporttime(self, journalname):
        """
        :param journalname:  name of the journal
        :return: export time of journal
        @type journalname: str
        @rtype: str
        """
        for subclassinstance in self._get_subclassinstances():
            result = subclassinstance.get_journal_exporttime(journalname)
            if result is not None:
                return result


class Validator:
    """
    Manage JT Project validators configured through
    (1) Project level
    (2) Node Level
    (3) Operation Level
       (a) configured within Operation definitions from operation.json.
       (b) input masks
       (c) operation validatity
       (d) sofware validatity
       (e) mandatory and optional parameters
    """

    def __init__(self, preferences, gopLoader):
        self.preferences = preferences
        self.gopLoader = gopLoader
        ops = getOperations()
        self.rules = {}
        for op, data in ops.iteritems():
            self.set_rules(op, data.rules)

    def set_rules(self, op, ruleNames):
        rules = [getRule(name, globals=globals(), default_module='maskgen.graph_rules') for name in ruleNames if len(name) > 0]
        self.rules[op] = [rule for rule in rules if rule is not None]

    def run_graph_suite(self, graph, external=None):
        """
        Run the validation suite including rules determined by operation definitions associated
        with each edge in the graph.

        :param graph:
        :param gopLoader:
        :param preferences:
        :param external:
        :return: list fo  ValidationMessage
        @type graph: ImageGraph
        @type gopLoader: GroupOperationsLoader
        @type preferences: MaskGenLoader
        @rtype:  list of ValidationMessage
        """
        if len(graph.get_nodes()) == 0:
            return []

        total_errors = []
        finalNodes = []
        # check for disconnected nodes
        # check to see if predecessors > 1 consist of donors
        for node in graph.get_nodes():
            if not graph.has_neighbors(node):
                total_errors.append(ValidationMessage(Severity.ERROR, str(node), str(node),
                                                      str(node) + ' is not connected to other nodes',
                                                      'Graph'))
            predecessors = graph.predecessors(node)
            if len(predecessors) == 1 and graph.get_edge(predecessors[0], node)['op'] == 'Donor':
                total_errors.append(ValidationMessage(Severity.ERROR,
                                                      str(predecessors[0]),
                                                      str(node), str(node) +
                                                      ' donor links must coincide with another link to the same destintion node',
                                                      'Graph'))
            successors = graph.successors(node)
            if len(successors) == 0:
                finalNodes.append(node)

        # check project type
        project_type = graph.get_project_type()
        matchedType = [node for node in finalNodes if
                       fileType(os.path.join(graph.dir, graph.get_node(node)['file'])) == project_type]
        if len(matchedType) == 0 and len(finalNodes) > 0:
            graph.setDataItem('projecttype',
                              fileType(os.path.join(graph.dir, graph.get_node(finalNodes[0])['file'])))

        nodeSet = set(graph.get_nodes())

        # check graph cuts
        for found in graph.findRelationsToNode(nodeSet.pop()):
            if found in nodeSet:
                nodeSet.remove(found)

        # check graph cuts
        for node in nodeSet:
            total_errors.append(ValidationMessage(Severity.ERROR,
                                                  str(node),
                                                  str(node),
                                                  str(node) + ' is part of an unconnected subgraph',
                                                  'Graph'))

        # check all files accounted for
        for file_error_tuple in graph.file_check():
            total_errors.append(ValidationMessage(Severity.ERROR,
                                                  file_error_tuple[0],
                                                  file_error_tuple[1],
                                                  file_error_tuple[2],
                                                  'Graph'))

        # check cycles
        cycleNode = graph.getCycleNode()
        if cycleNode is not None:
            total_errors.append(ValidationMessage(Severity.ERROR,
                                                  str(cycleNode),
                                                  str(cycleNode),
                                                  "Graph has a cycle",
                                                  'Graph'))

        valiation_apis = ValidationAPIComposite(self.preferences, external=external)

        total_errors.extend(valiation_apis.check_graph(graph))

        for node in graph.get_nodes():
            total_errors.extend(valiation_apis.check_node(node, graph))
            for error in run_node_rules(graph, node, external=external, preferences=self.preferences):
                if type(error) != tuple:
                    error = (Severity.ERROR, str(error))
                total_errors.append(ValidationMessage(error[0], str(node), str(node), error[1],'Node'))

        for frm, to in graph.get_edges():
            edge = graph.get_edge(frm, to)
            op = edge['op']
            total_errors.extend(valiation_apis.check_edge(op, graph, frm, to))
            errors = run_all_edge_rules(self.gopLoader.getOperationWithGroups(op, fake=True),
                                    self.rules[op] if op in self.rules else [],
                                    graph, frm, to)
            if len(errors) > 0:
                total_errors.extend(errors)
        return total_errors

    def run_edge_rules(self,graph, frm, to):
        """

        :param graph:
        :param frm:
        :param to:
        :return:
        @rtype: list of ValidationMessage
        @type frm: str
        @type to: str
        @type graph: ImageGraph
        """
        edge = graph.get_edge(frm, to)
        op = edge['op']
        valiation_apis = ValidationAPIComposite(self.preferences, external=True)
        total_errors = valiation_apis.check_edge(op, graph, frm, to)
        errors = run_all_edge_rules(self.gopLoader.getOperationWithGroups(op, fake=True),
                                self.rules[op] if op in self.rules else [],
                                graph, frm, to)
        if len(errors) > 0:
            total_errors.extend(errors)
        return total_errors




##==========================================
## NODE RULES
##==========================================
def run_node_rules(graph, node, external=False, preferences=None):
    import re
    import hashlib
    """

    :param graph: ImageGraph
    :param node:
    :param preferences:
    :return:
    @type preferences: MaskGenLoader
    @rtype: list of ValidationMessage
    @type frm: str
    @type to: str
    @type graph: ImageGraph
    """
    errors = []
    nodeData = graph.get_node(node)
    multiplebaseok = graph.getDataItem('provenance', default_value='no') == 'yes'

    if 'file' not in nodeData:
        errors.append((Severity.ERROR, 'Missing file information.'))
    else:
        pattern = re.compile(r'[\|\'\"\(\)\,\$\?]')
        foundItems = pattern.findall(nodeData['file'])
        if foundItems:
            errors.append((Severity.ERROR,
                           "Invalid characters {}  used in file name {}.".format(str(foundItems), nodeData['file'])))

    if nodeData['nodetype'] == 'final':
        fname = os.path.join(graph.dir, nodeData['file'])
        if os.path.exists(fname):
            with open(fname, 'rb') as rp:
                hashname = hashlib.md5(rp.read()).hexdigest()
                if hashname not in nodeData['file']:
                    errors.append(
                        (Severity.WARNING, "Final image {} is not composed of its MD5.".format(nodeData['file'])))

    if nodeData['nodetype'] == 'base' and not multiplebaseok:
        for othernode in graph.get_nodes():
            othernodeData = graph.get_node(othernode)
            if node != othernode and othernodeData['nodetype'] == 'base':
                errors.append((Severity.ERROR, "Projects should only have one base image"))

    if nodeData['nodetype'] in ('base', 'final', 'donor'):
        if 'file' not in nodeData:
            errors.append((Severity.ERROR, 'Missing media file'))
        else:
            file = nodeData['file']
            suffix_pos = file.rfind('.')
            if suffix_pos > 0:
                if file[suffix_pos:].lower() != file[suffix_pos:]:
                    errors.append(
                        (Severity.ERROR, nodeData['file'] + ' suffix (' + file[suffix_pos:] + ') is not lower case'))
    return errors


##==========================================
## LINK/EDGE RULES
##==========================================

def run_all_edge_rules(op, rules, graph, frm, to):
    """

    :param op:
    :param graph:
    :param frm:
    :param to:
    :return:
    @type op: Operation
    @type graph: ImageGraph
    @type frm: str
    @type to: str
    """
    graph = GraphProxy(graph)
    results = initial_link_check(op, graph, frm, to)
    for rule in rules:
        res = rule(op, graph, frm, to)
        if res is not None:
            if type(res) == str:
                res = ValidationMessage(Severity.ERROR, frm, to, res,rule.__name__)
            else:
                res = ValidationMessage(res[0], frm, to, res[1],rule.__name__)
            results.append(res)
    return results


def initial_link_check(op, graph, frm, to):
    """
    Check each link/edge for common integrity errors
    :param op:
    :param graph:
    :param frm:
    :param to:
    :return:
    @rtype: list of ValidationMessage
    @type op: Operation
    @type graph: ImageGraph
    @type frm: str
    @type to: str
    """
    edge = graph.get_edge(frm, to)
    operationResult = check_operation(edge, op, graph, frm, to)
    if operationResult is not None:
        return [operationResult]
    result = []
    result.extend(check_version(edge, op, graph, frm, to))
    result.extend(check_link_errors(edge, op, graph, frm, to))
    result.extend(check_mandatory(edge, op, graph, frm, to))
    result.extend(check_arguments(edge, op, graph, frm, to))
    result.extend(check_masks(edge, op, graph, frm, to))
    return result


def check_operation(edge, op, graph, frm, to):
    """

    :param edge:
    :param op:
    :param graph:
    :param frm:
    :param to:
    :return:
     @type edge: dict
    @type op: Operation
    @type graph: ImageGraph
    @type frm: str
    @type to: str
    """
    if op.name == 'Donor':
        return None
    if op.category == 'Bad':
        return ValidationMessage(Severity.ERROR,
                                 frm,
                                 to,
                                 'Operation ' + op.name + ' is invalid',
                                 'Operation')


def check_link_errors(edge, op, graph, frm, to):
    """
    Check if a link has errors recorded during creation of the change masks.
    :param edge:
    :param op:
    :param graph:
    :param frm:
    :param to:
    :return:
    @rtype:  list of (Severity, str)
    """
    if 'errors' in edge and edge['errors'] and len(edge['errors']) > 0:
        return [ValidationMessage(Severity.WARNING,
                                  frm,
                                  to,
                                  'Link has mask processing errors',
                                  'Change Mask')]
    return []


def check_version(edge, op, graph, frm, to):
    """
    :param edge:
    :param op:
    :param graph:
    :param frm:
    :param to:
    :return:
    @type edge: dict
    @type op: Operation
    @type graph: ImageGraph
    @type frm: str
    @type to: str
    @rtype:  (Severity, str)
    """
    global global_loader
    if op.name == 'Donor':
        return []
    if 'softwareName' in edge and 'softwareVersion' in edge:
        sname = edge['softwareName']
        sversion = strip_version(edge['softwareVersion'])
        if sversion not in global_loader.get_versions(sname):
            return [ValidationMessage(Severity.WARNING,
                                      '',
                                      '',
                                      sversion + ' not in approved set for software ' + sname,
                                      'Software')]
    return []


def check_arguments(edge, op, graph, frm, to):
    """
    Check operation arguments are in the correct type format
    :param edge:
    :param op:
    :param graph:
    :param frm:
    :param to:
    :return:
    @type edge: dict
    @type op: Operation
    @type graph: ImageGraph
    @type frm: str
    @type to: str
    @rtype: list of (Severity, str)
    """
    if op.name == 'Donor':
        return []
    args = [(k, v) for k, v in op.mandatoryparameters.iteritems()]
    args.extend([(k, v) for k, v in op.optionalparameters.iteritems()])
    results = []
    for argName, argDef in args:
        try:
            argValue = getValue(edge, 'arguments.' + argName)
            if argValue:
                validateAndConvertTypedValue(argName, argValue, op)
        except ValueError as e:
            results.append(ValidationMessage(Severity.ERROR,
                                             frm,
                                             to,
                                             argName + str(e),
                                             'Argument {}'.format(argName)))
    return results


def check_masks(edge, op, graph, frm, to):
    """
      Validate a typed operation argument
      return the type converted argument if necessary
      raise a ValueError if invalid
    :param edge:
    :param op:
    :param graph:
    :param frm:
    :param to:
    :return: list of (Severity, str)
    @type edge: dict
    @type op: Operation
    @type graph: ImageGraph
    @type frm: str
    @type to: str
     @rtype:  list of (Severity, str)
    """
    if not op.generateMask and graph.getNodeFileType(frm) != 'image':
        return []
    if 'maskname' not in edge or edge['maskname'] is None or \
                    len(edge['maskname']) == 0 or not os.path.exists(os.path.join(graph.dir, edge['maskname'])):
        return [ValidationMessage(Severity.ERROR,
                                  frm,
                                  to,
                                  'Link mask is missing. Recompute the link mask.',
                                  'Change Mask')]
    inputmaskname = edge['inputmaskname'] if 'inputmaskname' in edge  else None
    if inputmaskname is not None and len(inputmaskname) > 0 and \
            not os.path.exists(os.path.join(graph.dir, inputmaskname)):
        return [ValidationMessage(Severity.ERROR,
                                  frm,
                                  to,
                                  "Input mask file {} is missing".format(inputmaskname),
                                  'Input Mask')]
    if inputmaskname is not None and len(inputmaskname) > 0 and \
            os.path.exists(os.path.join(graph.dir, inputmaskname)):
        if fileType(os.path.join(graph.dir, inputmaskname)) == 'audio':
            return []
        inputmask = openImage(os.path.join(graph.dir, inputmaskname))
        if inputmask is None:
            return [ValidationMessage(Severity.ERROR,
                                      frm,
                                      to,
                                      "Input mask file {} is missing".format(inputmaskname),
                                      'Input Mask')]
        inputmask = inputmask.to_mask().to_array()
        mask = openImageFile(os.path.join(graph.dir, edge['maskname'])).invert().to_array()
        if inputmask.shape != mask.shape:
            return [ValidationMessage(Severity.ERROR,
                                      frm,
                                      to,
                                      'input mask name parameter has an invalid size',
                                      'Input Mask')]
    return []


def check_mandatory(edge, opInfo, graph, frm, to):
    """
    Check mandatory parameters.
    Check optional parameters condition on mandatory parameter values.
    'inputmaskname' is treated special since it has historically been placed outside the arguments list.
    :param edge:
    :param opInfo:
    :param graph:
    :param frm:
    :param to:
    :return: list of (Severity, str)
    @type edge: dict
    @type op: Operation
    @type graph: ImageGraph
    @type frm: str
    @type to: str
    @rtype:  list of (Severity, str)
    """
    if opInfo.name == 'Donor':
        return []
    if opInfo.category == 'Bad':
        return [ValidationMessage(Severity.ERROR,
                                  frm,
                                  to,
                                  opInfo.name + ' is not a valid operation',
                                  'Mandatory')] if opInfo.name != 'Donor' else []
    args = edge['arguments'] if 'arguments' in edge  else []
    frm_file = graph.get_image(frm)[1]
    frm_file_type = fileType(frm_file)
    missing = [param for param in opInfo.mandatoryparameters.keys() if
               (param not in args or len(str(args[param])) == 0) and \
               ('source' not in opInfo.mandatoryparameters[param] or opInfo.mandatoryparameters[param][
                   'source'] == frm_file_type)]
    for param_name, param_definition in opInfo.optionalparameters.iteritems():
        if 'rule' in param_definition:
            if param_name not in args:
                for dep_param_name, dep_param_value in param_definition['rule'].iteritems():
                    if getValue(args, dep_param_name, defaultValue=dep_param_value) == dep_param_value:
                        missing.append(param_name)
    missing = set(missing)
    inputmaskrequired = 'inputmaskname' in missing
    if inputmaskrequired:
        filename = getValue(edge, 'inputmaskname', defaultValue='')
        if len(filename) > 0 and os.path.exists(os.path.join(graph.dir, filename)):
            missing.remove('inputmaskname')
    return [ValidationMessage(Severity.ERROR,
                              frm,
                              to,
                              'Mandatory parameter ' + m + ' is missing',
                              'Mandatory') for m in missing]
