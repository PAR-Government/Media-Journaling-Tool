# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from maskgen.software_loader import getOperations, SoftwareLoader, getRule,strip_version
from maskgen.support import getValue, ModuleStatus
from maskgen.tool_set import fileType, openImage, openImageFile, validateAndConvertTypedValue,composeCloneMask,md5_of_file
from maskgen.image_graph import ImageGraph, GraphProxy,current_version
import os
from abc import ABCMeta, abstractmethod
from enum import Enum
from maskgen import MaskGenLoader
from maskgen.image_wrap import ImageWrapper
import logging

global_loader = SoftwareLoader()

class Severity(Enum):
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4

class ValidationMessage:

    def __init__(self,Severity, Start, End, Message, Module,Fix=None):
        self.Severity = Severity
        self.Start = Start
        self.End = End
        self.Message = Message
        self.Module = Module
        self.Fix = Fix

    def astuple(self):
        return (self.Severity,self.Start,self.End,self.Module,self.Message)

    def __getitem__(self, item):
        return [self.Severity,self.Start,self.End,self.Message,self.Module,self.Fix][item]

    def applyFix(self,graph):
        self.Fix(graph,self.Start,self.End)

def hasErrorMessages(validationMessageList, contentCheck=lambda x: True):
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
        if msg.Severity.value == Severity.ERROR.value and contentCheck(msg.Message):
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

class ValidationStatus(ModuleStatus):

    def __init__(self,module_name, component, percentage):
        ModuleStatus.__init__(self,'Validation', module_name,component,percentage)

def ignoreStatus(validation_status):
    """

    :param validation_status:
    :return:
    @type validation_status: ValidationStatus
    """
    pass

def logStatus(validation_status):
    """
    :param validation_status:
    :return:
    @type validation_status: ValidationStatus
    """
    logging.getLogger('maskgen').info(
        'Validation module {} for component {}: {}% Complete'.format(validation_status.module_name,
                                                                     validation_status.component,
                                                                     validation_status.percentage))

class ValidationAPIComposite(ValidationAPI):


    def __init__(self, preferences, external=False, status_cb=logStatus):
        self.preferences = preferences
        self.external = external
        self.instances = []
        self.status_cb = status_cb

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
            self.status_cb(ValidationStatus(subclassinstance.__class__.__name__,'edge {}:{}'.format(frm,to),0))
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
            self.status_cb(ValidationStatus(subclassinstance.__class__.__name__, 'graph', 0))
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
            self.status_cb(ValidationStatus(subclassinstance.__class__.__name__, 'node {}'.format(node), 0))
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
        complete = 0.0
        advance = 100.0/len(self.instances)
        for subclassinstance in self._get_subclassinstances():
            self.status_cb(ValidationStatus(subclassinstance.__class__.__name__, 'graph export time', complete))
            result = subclassinstance.get_journal_exporttime(journalname)
            complete += advance
            if result is not None:
                break
        self.status_cb(ValidationStatus(subclassinstance.__class__.__name__, 'graph export time', 100.0))
        return result


def renameToMD5(graph,start,end):
    """
       :param graph:
       :param start:
       :param end:
       :return:
       @type graph: ImageGraph
       @type start: str
       @type end: str
    """
    import shutil
    file_path_name =graph.get_image_path(start)
    filename = os.path.basename(file_path_name)
    if os.path.exists(file_path_name):
        try:
            suffix = os.path.splitext(filename)[1]
            new_file_name = md5_of_file(file_path_name) + suffix
            fullname = os.path.join(graph.dir, new_file_name)
        except:
            logging.getLogger('maskgen').error(
                'Missing file or invalid permission: {} '.format(file_path_name))
            return
        try:
            os.rename(file_path_name, fullname)
            logging.getLogger('maskgen').info(
                'Renamed {} to {} '.format(filename, new_file_name))
            graph.update_node(start, file=new_file_name)
        except Exception as e:
            logging.getLogger('maskgen').error(
                    ('Failure to rename file {} : {}.  Trying copy').format(file_path_name, str(e)))
            shutil.copy2(file_path_name, fullname)
            logging.getLogger('maskgen').info(
                    'Renamed {} to {} '.format(filename, new_file_name))
            graph.update_node(start, file=new_file_name)


def repairMask(graph,start,end):
    """
      :param graph:
      :param start:
      :param end:
      :return:
      @type graph: ImageGraph
      @type start: str
      @type end: str
      """
    edge = graph.get_edge(start,end)
    startimage, name = graph.get_image(start)
    finalimage, fname = graph.get_image(end)
    mask = graph.get_edge_image(start,end, 'maskname')
    inputmaskname = os.path.splitext(name)[0] + '_inputmask.png'
    ImageWrapper(composeCloneMask(mask, startimage, finalimage)).save(inputmaskname)
    edge['inputmaskname'] = os.path.split(inputmaskname)[1]
    graph.setDataItem('autopastecloneinputmask', 'yes')


class ValidationCallback:

    def __init__(self,advance_percent=1.0,start_percent=0.0, status_cb=logStatus):
        self.advance_percent = advance_percent
        self.current_percent = start_percent
        self.status_cb = status_cb

    def update_state(self,validation_status):
        """
        :param validation_status:
        :return:
        @type validation_status : ValidationStatus
        """
        self.status_cb(ValidationStatus(validation_status.module_name,validation_status.component,self.current_percent))
        self.current_percent += self.advance_percent

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
        ops = gopLoader.getAllOperations()
        self.rules = {}
        self.edge_mod_rules = {}
        for op, data in ops.iteritems():
            self.set_rules(op, data.rules)

    def set_rules(self, op, ruleNames):
        strippedRuleNames = [r[r.find(':') + 1:] for r in ruleNames if len(r) > 0]
        designations = [r[:r.find(':')] for r in ruleNames if len(r) > 0]
        rules = [getRule(name, globals=globals(), default_module='maskgen.graph_rules') for name in strippedRuleNames]
        self.rules[op] = [rule for rule in rules if rule is not None]
        self.edge_mod_rules[op] = [rules[i] for i in range(len(rules)) if rules[i] is not None and designations[i] != 'donor']

    def run_graph_suite(self, graph, external=None, status_cb=None):
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
        if status_cb is None:
            if ('log.validation' not in self.preferences or self.preferences['log.validation'] == 'yes'):
                status_cb = logStatus
            else:
                status_cb  = ignoreStatus
        nodeSet = set(graph.get_nodes())
        nodecount = len(nodeSet)
        edgecount = len(graph.get_edges())
        if nodecount == 0:
            return []

        total_errors = []
        finalNodes = []

        upgrades = graph.getDataItem('jt_upgrades',default_value=[])
        if graph.getVersion() not in upgrades or graph.getVersion() != current_version():
            total_errors.append(ValidationMessage(Severity.ERROR, '','',
                                                 'The journal was not upgraded due to an error. Try saving and reopening the journal',
                                                  'Graph',
                                                  None))

        # check for disconnected nodes
        # check to see if predecessors > 1 consist of donors
        status_cb(ValidationStatus('Connectivity', 'graph', 0))
        for node in graph.get_nodes():
            if not graph.has_neighbors(node):
                total_errors.append(ValidationMessage(Severity.ERROR, str(node), str(node),
                                                      str(node) + ' is not connected to other nodes',
                                                      'Graph',
                                                      None))
            predecessors = graph.predecessors(node)
            if len(predecessors) == 1 and graph.get_edge(predecessors[0], node)['op'] == 'Donor':
                total_errors.append(ValidationMessage(Severity.ERROR,
                                                      str(predecessors[0]),
                                                      str(node), str(node) +
                                                      ' donor links must coincide with another link to the same destintion node',
                                                      'Graph',
                                                      None))
            successors = graph.successors(node)
            if len(successors) == 0:
                finalNodes.append(node)

        status_cb(ValidationStatus('Project Type','Graph',4))
        # check project type
        project_type = graph.get_project_type()
        matchedType = [node for node in finalNodes if
                       fileType(os.path.join(graph.dir, graph.get_node(node)['file'])) == project_type]
        if len(matchedType) == 0 and len(finalNodes) > 0:
            graph.setDataItem('projecttype',
                              fileType(os.path.join(graph.dir, graph.get_node(finalNodes[0])['file'])))

        status_cb(ValidationStatus('Graph Cuts', 'Graph', 5))
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
                                                  'Graph',
                                                  None))

        status_cb(ValidationStatus('File Check', 'Graph', 6))
        # check all files accounted for
        for file_error_tuple in graph.file_check():
            total_errors.append(ValidationMessage(Severity.ERROR,
                                                  file_error_tuple[0],
                                                  file_error_tuple[1],
                                                  file_error_tuple[2],
                                                  'Graph',
                                                  None))

        status_cb(ValidationStatus('Cycle Check', 'Graph', 8))
        # check cycles
        cycleNode = graph.getCycleNode()
        if cycleNode is not None:
            total_errors.append(ValidationMessage(Severity.ERROR,
                                                  str(cycleNode),
                                                  str(cycleNode),
                                                  "Graph has a cycle",
                                                  'Graph',
                                                  None))

        status_cb(ValidationStatus('Final Node Check', 'Duplicates', 9))
        finalfiles = set()
        duplicates = dict()
        for node in finalNodes:
            filename = graph.get_node(node)['file']
            if filename in finalfiles and filename not in duplicates:
                duplicates[filename] = node
            finalfiles.add(filename)

        # check duplicate final end nodes
        if len(duplicates) > 0:
            for filename,node in duplicates.iteritems():
                total_errors.append(ValidationMessage(Severity.ERROR,
                                                      str(node),
                                                      str(node),
                                                      "Duplicate final end node file %s" % filename,
                                                      'Graph',
                                                      None))


        validation_callback = ValidationCallback(advance_percent=90.0/(nodecount + edgecount),start_percent=10.0,status_cb=status_cb)
        valiation_apis = ValidationAPIComposite(self.preferences, external=external, status_cb=validation_callback.update_state)
        validation_callback.advance_percent = 90.0/((nodecount + edgecount)*(1+len(valiation_apis.instances)) + len(valiation_apis.instances))

        total_errors.extend(valiation_apis.check_graph(graph))

        for node in graph.get_nodes():
            total_errors.extend(valiation_apis.check_node(node, graph))
            validation_callback.update_state(ValidationStatus('Internal','node {}'.format(node),0))
            for error in run_node_rules(graph, node, external=external, preferences=self.preferences):
                if type(error) != tuple:
                    error = (Severity.ERROR, str(error))
                total_errors.append(ValidationMessage(error[0], str(node), str(node), error[1],'Node',None if len(error) == 2 else error[2]))

        for frm, to in graph.get_edges():
            edge = graph.get_edge(frm, to)
            op = edge['op']
            total_errors.extend(valiation_apis.check_edge(op, graph, frm, to))
            validation_callback.update_state(ValidationStatus('Internal', 'edge {}:{}'.format(frm, to),0))
            errors = run_all_edge_rules(self.gopLoader.getOperationWithGroups(op, fake=True),
                                    self.rules[op] if op in self.rules else [],
                                    graph, frm, to)
            if len(errors) > 0:
                total_errors.extend(errors)
        validation_callback.status_cb(ValidationStatus('Validation','Complete',100.0))
        return total_errors

    def run_edge_rules(self, graph, frm, to, isolated=False):
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
        rules = self.rules if not isolated else self.edge_mod_rules
        errors = run_all_edge_rules(self.gopLoader.getOperationWithGroups(op, fake=True),
                                    rules[op] if op in rules else [],
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
    def rename(graph, start, end):
        node = graph.get_node(start)
        file = node['file']
        pattern = re.compile(r'[\|\'\"\(\)\,\$\? ]')
        new_name = re.sub(pattern,'_',file)
        os.rename(os.path.join(graph.dir, file),os.path.join(graph.dir, new_name))
        node['file'] = new_name

    def remove_proxy(graph, start, end):
        node = graph.get_node(start)
        if 'proxyfile' in node:
            node.pop('proxyfile')

    errors = []
    nodeData = graph.get_node(node)
    multiplebaseok = graph.getDataItem('provenance', default_value='no') == 'yes'

    if 'file' not in nodeData:
        errors.append((Severity.ERROR, 'Missing file information.'))
    else:
        pattern = re.compile(r'[\|\'\"\(\)\,\$\?]')
        foundItems = pattern.findall(nodeData['file'])
        if foundItems:
            fix = rename if nodeData['nodetype'] == 'interim' else None
            errors.append((Severity.ERROR,
                           "Invalid characters {}  used in file name {}.".format(str(foundItems), nodeData['file']),
                           fix))

    if nodeData['nodetype'] == 'final':
        fname = os.path.join(graph.dir, nodeData['file'])
        if os.path.exists(fname):
            with open(fname, 'rb') as rp:
                hashname = hashlib.md5(rp.read()).hexdigest()
                if hashname not in nodeData['file']:
                    errors.append(
                        (Severity.WARNING, "Final image {} is not composed of its MD5.".format(nodeData['file']),
                         renameToMD5))
        proxy = getValue(nodeData,'proxyfile', None)
        if proxy is not None:
            errors.append(
                (Severity.ERROR, "Final media {} cannot be hidden by a proxy.".format(nodeData['file']),remove_proxy))

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
                res = ValidationMessage(Severity.ERROR, frm, to, res,rule.__name__,None)
            else:
                res = ValidationMessage(res[0], frm, to, res[1], rule.__name__, None if len(res) == 2 else res[2])
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
                                 'Operation',
                                 None)


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
                                  'Change Mask',
                                  None)]
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
                                      'Software',
                                      None)]
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
                                             'Argument {}'.format(argName),
                                             None))
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
    def check_compare_mask(edge, op, graph, frm, to):
        if op.generateMask in ['audio','meta','frames'] or \
                (graph.getNodeFileType(frm) not in ['video','image'] and \
                graph.getNodeFileType(to) not in ['video', 'image']):
            return []
        if len(getValue(edge,'videomasks',[])) > 0:
            return []

        if getValue(edge,'maskname') is None or \
           getValue(edge,'maskname','') == '' or \
              not os.path.exists(os.path.join(graph.dir, edge['maskname'])):
            return [ValidationMessage(Severity.ERROR,
                                      frm,
                                      to,
                                      'Link mask is missing. Recompute the link mask.',
                                      'Change Mask',
                                      None)]
        return []

    def check_input_mask(edge, op, graph, frm, to):
        inputmaskname = edge['inputmaskname'] if 'inputmaskname' in edge  else None

        if inputmaskname is not None and len(inputmaskname) > 0 and \
                not os.path.exists(os.path.join(graph.dir, inputmaskname)):
            return [ValidationMessage(Severity.ERROR,
                                      frm,
                                      to,
                                      "Input mask file {} is missing".format(inputmaskname),
                                      'Input Mask',
                                      repairMask)]
        if inputmaskname is not None and len(inputmaskname) > 0 and \
                os.path.exists(os.path.join(graph.dir, inputmaskname)):
            ft = fileType(os.path.join(graph.dir, inputmaskname))
            if ft == 'audio':
                return []
            inputmask = openImage(os.path.join(graph.dir, inputmaskname))
            if inputmask is None:
                return [ValidationMessage(Severity.ERROR,
                                          frm,
                                          to,
                                          "Input mask file {} is missing".format(inputmaskname),
                                          'Input Mask',
                                          repairMask if ft == 'image' else None)]
            inputmask = inputmask.to_mask().to_array()
            mask = openImageFile(os.path.join(graph.dir, edge['maskname'])).invert().to_array()
            if inputmask.shape != mask.shape:
                return [ValidationMessage(Severity.ERROR,
                                          frm,
                                          to,
                                          'input mask name parameter has an invalid size',
                                          'Input Mask',
                                          repairMask if ft == 'image' else None)]
        return []

    return check_compare_mask(edge, op, graph, frm, to) + check_input_mask(edge, op, graph, frm, to)


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
                                  'Mandatory',
                                  None)] if opInfo.name != 'Donor' else []
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
                for dep_param_name, dep_param_values in param_definition['rule'].iteritems():
                    if len(dep_param_values) > 0 and \
                         getValue(args, dep_param_name, defaultValue=dep_param_values[0]) in dep_param_values:
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
                              'Mandatory',
                              None) for m in missing]
