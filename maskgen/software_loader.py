from os.path import expanduser
import csv
import platform
import os
from maskgen_loader import MaskGenLoader
from json import JSONEncoder
import json
import logging

class OperationEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__

def getFileName(fileName, path=None):
    import sys
    if (os.path.exists(fileName)):
        logging.getLogger('maskgen').info( 'Loading ' + fileName)
        return fileName
    places = [os.getenv('MASKGEN_RESOURCES', 'resources')]
    places.extend([os.path.join(x,'resources') for x in sys.path if 'maskgen' in x or
                   (path is not None and path in x)])
    for place in places:
        newNanme = os.path.abspath(os.path.join(place, fileName))
        if os.path.exists(newNanme):
            logging.getLogger('maskgen').info( 'Loading ' + newNanme)
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
    optionalparameters = {}
    mandatoryparameters = {}
    rules = []
    analysisOperations = []
    transitions = []
    compareparameters = {}
    generateMask  = True
    groupedOperations = None
    groupedCategories = None
    maskTransformFunction = None
    compareOperations = None

    def __init__(self, name='', category='', includeInMask=False, rules=list(), optionalparameters=dict(),
                 mandatoryparameters=dict(), description=None, analysisOperations=list(), transitions=list(),
                 compareparameters=dict(),generateMask = True,groupedOperations=None, groupedCategories = None,
                 maskTransformFunction=None):
        self.name = name
        self.category = category
        self.includeInMask = includeInMask
        self.rules = rules
        self.mandatoryparameters = mandatoryparameters if mandatoryparameters is not None else {}
        self.optionalparameters = optionalparameters if optionalparameters is not None else {}
        self.description = description
        self.analysisOperations = analysisOperations
        self.transitions = transitions
        self.compareparameters = compareparameters
        self.generateMask  = generateMask
        self.groupedOperations = groupedOperations
        self.groupedCategories = groupedCategories
        self.maskTransformFunction = maskTransformFunction

    def getConvertFunction(self):
        if 'convert_function' in self.compareparameters:
                funcName = self.compareparameters['convert_function']
                return getRule(funcName)
        return None

    def getCompareFunction(self):
        if 'function' in self.compareparameters:
            funcName = self.compareparameters['function']
            return getRule(funcName)
        return None

    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


def getOperation(name, fake = False, warning=True):
    """

    :param name: name of the operation
    :param fake: Set to True to allow fake operations
    :return: Operation
    """
    global metadataLoader
    if name == 'Donor':
        return Operation(name='Donor', category='Donor',maskTransformFunction='maskgen.mask_rules.donor')
    if name not in metadataLoader.operations and warning:
        logging.getLogger('maskgen').warning( 'Requested missing operation ' + str(name))
    return metadataLoader.operations[name] if name in metadataLoader.operations else (Operation(name='name', category='Bad') if fake else None)


def getOperations():
    global metadataLoader
    return metadataLoader.operations


def getOperationsByCategory(sourcetype, targettype):
    global metadataLoader
    result = {}
    transition = sourcetype + '.' + targettype
    for name, op in metadataLoader.operations.iteritems():
        if transition in op.transitions:
            if op.category not in result:
                result[op.category] = []
            result[op.category].append(op.name)
    return result

def getPropertiesBySourceType(source):
    global metadataLoader
    return metadataLoader.node_properties[source]

def getSoftwareSet():
    global metadataLoader
    return metadataLoader.softwareset


def saveJSON(filename):
    global metadataLoader
    opnamelist = list(metadataLoader.operations.keys())
    opnamelist.sort()
    oplist = [metadataLoader.operations[op] for op in opnamelist]
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
    operations = {}
    fileName = getFileName(fileName)
    with open(fileName, 'r') as f:
        ops = json.load(f)
        for op in ops['operations']:
            operations[op['name']] = Operation(name=op['name'], category=op['category'], includeInMask=op['includeInMask'],
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
    return operations, ops['filtergroups'] if 'filtergroups' in ops else {}, ops['version'] if 'version' in ops else '0.4.0308.db2133eadc', \
         ops['node_properties'] if 'node_properties' in ops else {}

customRuleFunc = {}
def loadCustomRules():
    global customRuleFunc
    import pkg_resources
    for p in  pkg_resources.iter_entry_points("maskgen_rules"):
        logging.getLogger('maskgen').info( 'load rule ' + p.name)
        customRuleFunc[p.name] = p.load()

def insertCustomRule(name,func):
    global customRuleFunc
    customRuleFunc[name] = func

def noopFule(*arg,**kwargs):
    return None

def getRule(name, globals={}):
    if name is None:
        return None
    import importlib
    global customRuleFunc
    if name in customRuleFunc:
        return customRuleFunc[name]
    else:
        if '.' not in name:
            return globals.get(name)
        mod_name, func_name = name.rsplit('.', 1)
        try:
            mod = importlib.import_module(mod_name)
            func = getattr(mod, func_name)
            customRuleFunc[name] = func
            return func#globals.get(name)
        except Exception as e:
            logging.getLogger('maskgen').error('Unable to load rule {}: {}'.format(name,str(e)))
            return noopFule

def getProjectProperties():
    """

    :return:
    @rtype: list of ProjectProperty
    """
    global metadataLoader
    return metadataLoader.projectProperties


def getSemanticGroups():
    return [prop.description for prop in getProjectProperties() if prop.semanticgroup]

def getFilters(filtertype):
    global metadataLoader
    if filtertype == 'filtergroups':
        return metadataLoader.filters
    else:
        return {}


class MetaDataLoader:
    version = ''
    softwareset = {}
    operations = {}
    filters = {}
    operationsByCategory = {}
    projectProperties = {}

    def __init__(self):
        self.operations , self.filters, self.operationsByCategory = self.loadOperations('operations.json')
        self.softwareset = self.loadSoftware('software.csv')
        self.projectProperties = self.loadProjectProperties('project_properties.json')

    def loadSoftware(self, fileName):
        fileName = getFileName(fileName)
        self.softwareset = {'image': {}, 'video': {}, 'audio': {}}
        with open(fileName) as f:
            line_no = 0
            for l in f.readlines():
                line_no += 1
                l = l.strip()
                if len(l) == 0:
                    continue
                columns = l.split(',')
                if len(columns) < 3:
                    logging.getLogger('maskgen').error(
                        'Invalid software description on line ' + str(line_no) + ': ' + l)
                software_type = columns[0].strip()
                software_name = columns[1].strip()
                versions = [x.strip() for x in columns[2:] if len(x) > 0]
                if software_type not in ['both', 'image', 'video', 'audio', 'all']:
                    logging.getLogger('maskgen').error('Invalid software type on line ' + str(line_no) + ': ' + l)
                elif len(software_name) > 0:
                    types = ['image', 'video'] if software_type == 'both' else [software_type]
                    types = ['image', 'video', 'audio'] if software_type == 'all' else types
                    types = ['video', 'audio'] if software_type == 'audio' else types
                    for stype in types:
                        self.softwareset[stype][software_name] = versions
        return self.softwareset

    def loadProjectProperties(self, fileName):
        loadCustomRules()
        self.projectProperties = loadProjectPropertyJSON(fileName)
        return self.projectProperties

    def loadOperations(self,fileName):
        self.operations, self.filters, self.version, self.node_properties = loadOperationJSON(fileName)
        logging.getLogger('maskgen').info('Loaded operation version ' + self.version)
        self.operationsByCategory = {}
        for op, data in self.operations.iteritems():
            category = data.category
            if category not in self.operationsByCategory:
                self.operationsByCategory[category] = []
                self.operationsByCategory[category].append(op)
        return self.operations, self.filters, self.operationsByCategory


global metadataLoader
metadataLoader =  MetaDataLoader()

def toSoftware(columns):
    return [x.strip() for x in columns[1:] if len(x) > 0]

def getOS():
    return platform.system() + ' ' + platform.release() + ' ' + platform.version()


def operationVersion():
    global metadataLoader
    return metadataLoader.version

def validateSoftware(softwareName, softwareVersion):
    global metadataLoader
    for software_type, typed_software_set in metadataLoader.softwareset.iteritems():
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
        global metadataLoader
        return list(metadataLoader.softwareset[software_type].keys())

    def get_versions(self, name, software_type=None, version=None):
        global metadataLoader
        types_to_check = ['image', 'video', 'audio'] if software_type is None else [software_type]
        for type_to_check in types_to_check:
            versions = metadataLoader.softwareset[type_to_check][name] if name in metadataLoader.softwareset[type_to_check] else None
            if versions is None:
                continue
            if version is not None and version not in versions:
                versions = list(versions)
                versions.append(version)
                logging.getLogger('maskgen').warning( version + ' not in approved set for software ' + name)
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
