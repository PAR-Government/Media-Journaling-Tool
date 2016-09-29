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

    def __init__(self, name='', category='', includeInMask=False, rules=list(), optionalparameters=list(),
                 mandatoryparameters=list(), description=None, analysisOperations=list(), transitions=list(),
                 compareparameters=dict()):
        self.name = name
        self.category = category
        self.includeInMask = includeInMask
        self.rules = rules
        self.mandatoryparameters = mandatoryparameters
        self.optionalparameters = optionalparameters
        self.description = description
        self.analysisOperations = analysisOperations
        self.transitions = transitions
        self.compareparameters = compareparameters

    def to_JSON(self):
        return json.dumps(self, default=lambda o: o.__dict__,
                          sort_keys=True, indent=4)


def getOperation(name):
    global operations
    return operations[name] if name in operations else None


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


def loadJSON(fileName):
    res = {}
    if not (os.path.exists(fileName)):
        fileName = os.path.join('resources', fileName)
    with open(fileName, 'r') as f:
        ops = json.load(f)
        for op in ops['operations']:
            res[op['name']] = Operation(name=op['name'], category=op['category'], includeInMask=op['includeInMask'],
                                        rules=op['rules'], optionalparameters=op['optionalparameters'],
                                        mandatoryparameters=op['mandatoryparameters'],
                                        description=op['description'] if 'description' in op else None,
                                        analysisOperations=op[
                                            'analysisOperations'] if 'analysisOperations' in op else [],
                                        transitions=op['transitions'] if 'transitions' in op else [],
                                        compareparameters=op['compareparameters'] if 'compareparameters' in op else dict())
    return res


def loadOperations(fileName):
    global operations
    global operationsByCategory
    operations = loadJSON(fileName)
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
    if not (os.path.exists(fileName)):
        fileName = os.path.join('resources', fileName)
    softwareset = {'image':{},'video':{}}
    with open(fileName) as f:
        line_no = 0
        for l in f.readlines():
            line_no+=1
            l = l.strip()
            if len(l) == 0:
                continue
            columns = l.split(',')
            if len(columns) < 3:
                print 'Invalid software description on line ' + str(line_no) + ': ' + l
            software_type = columns[0].strip()
            software_name = columns[1].strip()
            versions = [x.strip() for x in columns[2:] if len(x) > 0]
            if software_type not in ['both','image','video']:
                print 'Invalid software type on line ' + str(line_no) + ': ' + l
            elif len(software_name) > 0:
                types = ['image', 'video'] if software_type == 'both' else [software_type]
                for stype in types:
                  softwareset[stype][software_name] = versions
    return softwareset


def getOS():
    return platform.system() + ' ' + platform.release() + ' ' + platform.version()


def validateSoftware(softwareName, softwareVersion):
    global softwareset
    for software_type,typed_software_set in softwareset.iteritems():
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
        types_to_check = ['image', 'video'] if software_type is None else [software_type]
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
