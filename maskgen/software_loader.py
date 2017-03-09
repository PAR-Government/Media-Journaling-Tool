from os.path import expanduser
import csv
import platform
import os
from maskgen_loader import MaskGenLoader
from json import JSONEncoder
import json


class OperationEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__


softwareset = {}
operations = {}
operationsByCategory = {}
projectProperties = {}


def getFileName(fileName):
    import sys
    if (os.path.exists(fileName)):
        print 'Loading ' + fileName
        return fileName
    places = [os.getenv('MASKGEN_RESOURCES', 'resources')]
    places.extend([os.path.join(x,'resources') for x in sys.path if 'maskgen' in x])
    for place in places:
        newNanme = os.path.abspath(os.path.join(place, fileName))
        if os.path.exists(newNanme):
            print 'Loading ' + newNanme
            return newNanme

class ProjectProperty:
    description = None
    name = None
    type = None
    operations = None
    parameter = None
    rule = None
    values = None
    value = None
    information = None
    semanticgroup = False
    node = False
    readonly = False
    mandatory= False
    nodetype = None
    """
    @type operations: list of str
    @type nodetype: str
    """

    def __init__(self, name='', type='', operations=None, parameter=None, description=None,
                 information=None, value=None, values=None, rule=None, node=False, readonly=False,mandatory=True,
                 nodetype=None,semanticgroup=False):
        self.name = name
        self.type = type
        self.operations = operations
        self.parameter = parameter
        self.description = description
        self.rule = rule
        self.values = values
        self.value = value
        self.information = information
        self.node = node
        self.readonly = readonly
        self.mandatory = mandatory
        self.nodetype = nodetype
        self.semanticgroup = semanticgroup


class Operation:
    name = None
    category = None
    includeInMask = False
    description = None
    optionalparameters = []
    mandatoryparameters = []
    rules = []
    analysisOperations = []
    transitions = []
    compareparameters = {}
    generateMask  = True
    groupedOperations = None
    groupedCategories = None
    maskTransformFunction = None

    def __init__(self, name='', category='', includeInMask=False, rules=list(), optionalparameters=list(),
                 mandatoryparameters=list(), description=None, analysisOperations=list(), transitions=list(),
                 compareparameters=dict(),generateMask = True,groupedOperations=None, groupedCategories = None,
                 maskTransformFunction=maskTransformFunction):
        self.name = name
        self.category = category
        self.includeInMask = includeInMask
        self.rules = rules
        self.mandatoryparameters = mandatoryparameters if mandatoryparameters is not None else []
        self.optionalparameters = optionalparameters if optionalparameters is not None else []
        self.description = description
        self.analysisOperations = analysisOperations
        self.transitions = transitions
        self.compareparameters = compareparameters
        self.generateMask  = generateMask
        self.groupedOperations = groupedOperations
        self.groupedCategories = groupedCategories
        self.maskTransformFunction = maskTransformFunction

    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


def getOperation(name, fake = False):
    """

    :param name: name of the operation
    :param fake: Set to True to allow fake operations
    :return: Operation
    """
    global operations
    if name == 'Donor':
        return Operation(name='Donor', category='Donor')
    if name not in operations:
        print 'Requested missing operation ' + str(name)
    return operations[name] if name in operations else (Operation(name='name', category='Bad') if fake else None)


def getOperations():
    global operations
    return operations


def getOperationsByCategory(sourcetype, targettype):
    global operationsByCategory
    result = {}
    transition = sourcetype + '.' + targettype
    for name, op in operations.iteritems():
        if transition in op.transitions:
            if op.category not in result:
                result[op.category] = []
            result[op.category].append(op.name)
    return result


def getSoftwareSet():
    global softwareset
    return softwareset


def saveJSON(filename):
    global operations
    opnamelist = list(operations.keys())
    opnamelist.sort()
    oplist = [operations[op] for op in opnamelist]
    with open(filename, 'w') as f:
        json.dump({'operations': oplist}, f, indent=2, cls=OperationEncoder)


def loadProjectPropertyJSON(fileName):
    res = list()
    fileName = getFileName(fileName)
    with open(fileName, 'r') as f:
        props = json.load(f)
        for prop in props['properties']:
            res.append( ProjectProperty(name=prop['name'], type=prop['type'], description=prop['description'],
                                                parameter=prop['parameter'] if 'parameter' in prop else None,
                                                rule=prop['rule'] if 'rule' in prop else None,
                                                values=prop['values'] if 'values' in prop else None,
                                                value=prop['value'] if 'value' in prop else None,
                                                node=prop['node'] if 'node' in prop else False,
                                                information=prop['information'] if 'information' in prop else None,
                                                operations=[prop['operation']] if 'operation' in prop else
                                                (prop['operations'] if 'operations' in prop else []),
                                                readonly=prop['readonly'] if 'readonly' in prop else None,
                                                mandatory=prop['mandatory'] if 'mandatory' in prop else False,
                                                semanticgroup=prop['semanticgroup'] if 'semanticgroup' in prop else False,
                                                nodetype=prop['nodetype'] if 'nodetype' in prop else None))
    return res


def loadOperationJSON(fileName):
    res = {}
    fileName = getFileName(fileName)
    with open(fileName, 'r') as f:
        ops = json.load(f)
        for op in ops['operations']:
            res[op['name']] = Operation(name=op['name'], category=op['category'], includeInMask=op['includeInMask'],
                                        rules=op['rules'], optionalparameters=op['optionalparameters'],
                                        mandatoryparameters=op['mandatoryparameters'],
                                        description=op['description'] if 'description' in op else None,
                                        generateMask=op['generateMask'] if 'generateMask' in op else True,
                                        analysisOperations=op[
                                            'analysisOperations'] if 'analysisOperations' in op else [],
                                        transitions=op['transitions'] if 'transitions' in op else [],
                                        compareparameters=op[
                                            'compareparameters'] if 'compareparameters' in op else dict(),
                                        maskTransformFunction=op['maskTransformFunction'] if 'maskTransformFunction' in op else None)
    return res

customRuleFunc = {}
def loadCustomRules():
    global customRuleFunc
    import pkg_resources
    for p in  pkg_resources.iter_entry_points("maskgen_rules"):
        print 'load rule ' + p.name
        customRuleFunc[p.name] = p.load()

def getRule(name, globals={}):
    import importlib
    global customRuleFunc
    if name in customRuleFunc:
        return customRuleFunc[name]
    else:
        if '.' not in name:
            return globals.get(name)
        mod_name, func_name = name.rsplit('.', 1)
        mod = importlib.import_module(mod_name)
        func = getattr(mod, func_name)
        return func#globals.get(name)

def loadProjectProperties(fileName):
    global projectProperties
    loadCustomRules()
    projectProperties = loadProjectPropertyJSON(fileName)
    return projectProperties


def getProjectProperties():
    """

    :return:
    @rtype: list of ProjectProperty
    """
    global projectProperties
    return projectProperties


def getSemanticGroups():
    return [prop.description for prop in getProjectProperties() if prop.semanticgroup]

def loadOperations(fileName):
    global operations
    global operationsByCategory
    operations = loadOperationJSON(fileName)
    operationsByCategory = {}
    for op, data in operations.iteritems():
        category = data.category
        if category not in operationsByCategory:
            operationsByCategory[category] = []
        operationsByCategory[category].append(op)
    return operations


def toSoftware(columns):
    return [x.strip() for x in columns[1:] if len(x) > 0]


def loadSoftware(fileName):
    global softwareset
    fileName = getFileName(fileName)
    softwareset = {'image': {}, 'video': {},'audio': {}}
    with open(fileName) as f:
        line_no = 0
        for l in f.readlines():
            line_no += 1
            l = l.strip()
            if len(l) == 0:
                continue
            columns = l.split(',')
            if len(columns) < 3:
                print 'Invalid software description on line ' + str(line_no) + ': ' + l
            software_type = columns[0].strip()
            software_name = columns[1].strip()
            versions = [x.strip() for x in columns[2:] if len(x) > 0]
            if software_type not in ['both', 'image', 'video', 'audio', 'all']:
                print 'Invalid software type on line ' + str(line_no) + ': ' + l
            elif len(software_name) > 0:
                types = ['image', 'video'] if software_type == 'both' else [software_type]
                types = ['image', 'video', 'audio'] if software_type == 'all' else types
                types = ['video', 'audio'] if software_type == 'audio' else types
                for stype in types:
                    softwareset[stype][software_name] = versions
    return softwareset


def getOS():
    return platform.system() + ' ' + platform.release() + ' ' + platform.version()


def validateSoftware(softwareName, softwareVersion):
    global softwareset
    for software_type, typed_software_set in softwareset.iteritems():
        if softwareName in typed_software_set and softwareVersion in typed_software_set[softwareName]:
            return True
    return False


class Software:
    name = None
    version = None
    internal = False

    def __init__(self, name, version, internal=False):
        self.name = name
        self.version = version
        self.internal = internal




class SoftwareLoader:
    software = {}
    preference = None
    loader = MaskGenLoader()

    def __init__(self):
        self.load()

    def load(self):
        res = {}
        self.preference = self.loader.get_key('software_pref')
        newset = self.loader.get_key('software')
        if newset is not None:
            if type(newset) == list:
                for item in newset:
                    if validateSoftware(item[0], item[1]):
                        res[item[0]] = item[1]
            else:
                for name, version in newset.iteritems():
                    if validateSoftware(name, version):
                        res[name] = version
        self.software = res

    def get_preferred_version(self, name=None):
        if self.preference is not None and (name is None or name == self.preference[0]):
            return self.preference[1]
        if len(self.software) > 0:
            if name in self.software:
                return self.software[name]
            elif name is None:
                return self.software[self.software.keys()[0]]
        return None

    def get_preferred_name(self):
        if self.preference is not None:
            return self.preference[0]
        if len(self.software) > 0:
            return self.software.keys()[0]
        return None

    def get_names(self, software_type):
        global softwareset
        return list(softwareset[software_type].keys())

    def get_versions(self, name, software_type=None, version=None):
        global softwareset
        types_to_check = ['image', 'video', 'audio'] if software_type is None else [software_type]
        for type_to_check in types_to_check:
            versions = softwareset[type_to_check][name] if name in softwareset[type_to_check] else None
            if versions is None:
                continue
            if version is not None and version not in versions:
                versions = list(versions)
                versions.append(version)
                print version + ' not in approved set for software ' + name
            return versions
        return []

    def add(self, software):
        isChanged = False
        if validateSoftware(software.name, software.version):
            if not software.name in self.software or self.software[software.name] != software.version:
                self.software[software.name] = software.version
                isChanged = True
            pref = self.preference
            if pref is None or pref[0] != software.name or pref[1] != software.version:
                self.preference = [software.name, software.version]
                isChanged = True
        return isChanged

    def save(self):
        self.loader.saveall([("software", self.software), ("software_pref", self.preference)])
