# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================


import json
import logging
import os
from json import JSONEncoder

from maskgen.config import global_config
from maskgen_loader import MaskGenLoader
from maskgen.support import getValue


class OperationEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__

def strip_version(version):
    return '.'.join(version.split('.')[:2]) if version is not None else ''

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


def extract_default_values(operation_arguments):
    """
    given argument definitions, return operation name: default value if default is present
    :param operation_arguments:
    :return:
     @type dict
    """
    return {k:v['defaultvalue'] for k,v in operation_arguments.iteritems() if 'defaultvalue' in v}

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
    defaultvalue = None
    """
    @type operations: list of str
    @type nodetype: str
    """

    def __init__(self, name='', type='', operations=None, parameter=None, description=None,
                 information=None, value=None, values=None, rule=None, node=False, readonly=False,mandatory=True,
                 nodetype=None,semanticgroup=False,defaultvalue = None,includedonors=False):
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
        self.defaultvalue = defaultvalue
        self.includedonors = includedonors


class Operation:
    name = None
    category = None
    includeInMask = {'default':False}
    description = None
    optionalparameters = {}
    mandatoryparameters = {}
    rules = []
    analysisOperations = []
    transitions = []
    compareparameters = {}
    generateMask  = "all"
    groupedOperations = None
    groupedCategories = None
    maskTransformFunction = None
    compareOperations = None
    parameter_dependencies = None
    donor_processor = None
    """
    parameter_dependencies is a dictionary: { 'parameter name' : { 'parameter value' : 'dependenent parameter name'}}
    If the parameter identitied by parameter name has a value if 'parameter value' then the parameter identified by
    'dependent parameter name' is required.

    compareparamaters are used to pick arguments and algorithms for link comparison and analysis functions.
    Examples:
         "function" :"maskgen.tool_set.cropCompare",
         "video_function": "maskgen.video_tools.cropCompare"
         "tolerance" : 0.0001

    maskTransformFunction is a dictionary of functions associated with type of media which determines the
    transformation function applied to a mask as it is re-alligned to the final or base image for composite or
    donor mask construction, respectively.  Examples:
        "image": "maskgen.mask_rules.crop_transform",
        "video":"maskgen.mask_rules.video_crop_transform"

    rules is a list of functions to apply to each link during validation.  The signature of each of function
    is  (op, graph, frm, to)
      op = Operation
      graph = maskgen.image_graph.ImageGraph
      frm = str source node id
      to = str targe node id

    transitions is a list of string of the format source type '.' target type.
    The types identify media types (e.g. audio, video ,zip and image).    The transition identifies
    allowed transitions supported by the specific operation.  For example, 'video.image' states that the
    associated operation can convert a video to an image.

    generateMask states whether an operation analysis requires mask generation for 'all', 'frames', 'meta' or None.
    For the moment, all and frames are the same thing: frames and meta data is collected for each link comparing source
    and target media.  generateMask currently only applies to video and audio.

    analysisOperations is a list of function names that are used to populate the analysis dictionary collected at link
     comparison time. Analysis can find transform matrices, shape changes, location identification, etc.
     The results of analysis are often used by maskTransformFunction functions to construct composite and donor masks,
     acting as the transform parameters.

    groupedOperations and groupedCategories are lists of operations and categories represented by an agglomerative/composite
    operation.

    @type category: str
    @type generateMask: tr
    @type name: str
    @type rules: list
    @type transitions : list
    @type description: str
    @type analysisOperations: list
    @type mandatoryparameters: dict
    @type optionalparameters: dict
    @type compareparameters: dict
    @type parameter_dependencies: dict
    @type maskTransformFunction:dict
    @type donor_processor: str
    """

    def __init__(self, name='', category='', includeInMask={"default": False}, rules=list(), optionalparameters=dict(),
                 mandatoryparameters=dict(), description=None, analysisOperations=list(), transitions=list(),
                 compareparameters=dict(),generateMask = "all",groupedOperations=None, groupedCategories = None,
                 maskTransformFunction=None,parameter_dependencies = None, qaList=None,donor_processor=None):
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
        self.parameter_dependencies = parameter_dependencies
        self.qaList = qaList
        self.donor_processor = donor_processor
        self.trigger_arguments = self._getTriggerUpdateArguments()

    def _getTriggerUpdateArguments(self):
        names = set()
        for k,v in self.mandatoryparameters.iteritems():
            if getValue(v,'trigger mask',False):
                names.add(k)
        for k,v in self.optionalparameters.iteritems():
            if getValue(v,'trigger mask',False):
                names.add(k)
        return names

    def getTriggerUpdateArguments(self):
        return self.trigger_arguments

    def recordMaskInComposite(self,filetype):
        if filetype in self.includeInMask :
            return 'yes' if self.includeInMask [filetype] else 'no'
        if 'default' in self.includeInMask :
            return 'yes' if self.includeInMask ['default'] else 'no'
        return 'no'

    def getParameterValuesForType(self, param_name, type):
        param = getValue(self.mandatoryparameters,param_name, getValue(self.optionalparameters,param_name,{}))
        return getValue(param,type +':values', getValue(param,'values'),[] )

    def getDonorProcessor(self, default_processor = None):
        if  self.donor_processor is not None:
            return getRule(self.donor_processor)
        return getRule(default_processor)

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

    def getVideoCompareFunction(self):
        if 'video_function' in self.compareparameters:
            funcName = self.compareparameters['video_function']
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
    if name == 'Donor':
        return Operation(name='Donor', category='Donor',maskTransformFunction=
        {'image':'maskgen.mask_rules.donor',
         'video':'maskgen.mask_rules.video_donor',
         'audio': 'maskgen.mask_rules.audio_donor',
         })
    if name not in getMetDataLoader().operations:
        root_name = name.split('::')[0]
        if root_name == name:
            if warning:
                logging.getLogger('maskgen').warning( 'Requested missing operation ' + str(name))
        else:
            return getOperation(root_name,fake=fake,warning=warning)

    return getMetDataLoader().operations[name] if name in getMetDataLoader().operations else (Operation(name='name', category='Bad') if fake else None)


def getOperations():
    return getMetDataLoader().operations


def getOperationsByCategory(sourcetype, targettype):
    result = {}
    transition = sourcetype + '.' + targettype
    for name, op in getMetDataLoader().operations.iteritems():
        if transition in op.transitions:
            if op.category not in result:
                result[op.category] = []
            result[op.category].append(op.name)
    return result

def getPropertiesBySourceType(source):
    return getMetDataLoader().node_properties[source]

def getSoftwareSet():
    return getMetDataLoader().software_set


def saveJSON(filename):
    opnamelist = list(getMetDataLoader().operations.keys())
    opnamelist.sort()
    oplist = [getMetDataLoader().operations[op] for op in opnamelist]
    with open(filename, 'w') as f:
        json.dump({'operations': oplist}, f, indent=2, cls=OperationEncoder)


def loadProjectPropertyJSON(fileName):
    """

    :param fileName:
    :return:
    @rtype: list of ProjectProperty
    """
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
                                                nodetype=prop['nodetype'] if 'nodetype' in prop else None,
                                                defaultvalue=prop['defaultvalue'] if 'defaultvalue' in prop else None,
                                                includedonors=prop['includedonors'] if 'includedonors' in prop else False))
    return res


def loadOperationJSON(fileName):
    """

    :param fileName:
    :return:
    @rtype: dict of str:Operation
    """
    from collections import OrderedDict
    operations = OrderedDict()
    fileName = getFileName(fileName)
    with open(fileName, 'r') as f:
        ops = json.load(f)
        for op in ops['operations']:
            operations[op['name']] = Operation(name=op['name'], category=op['category'], includeInMask=op['includeInMask'],
                                        rules=op['rules'], optionalparameters=op['optionalparameters'] if 'optionalparameters' in op else {},
                                        mandatoryparameters=op['mandatoryparameters'],
                                        description=op['description'] if 'description' in op else None,
                                        generateMask=op['generateMask'] if 'generateMask' in op else "all",
                                        analysisOperations=op[
                                            'analysisOperations'] if 'analysisOperations' in op else [],
                                        transitions=op['transitions'] if 'transitions' in op else [],
                                        compareparameters=op[
                                            'compareparameters'] if 'compareparameters' in op else dict(),
                                        maskTransformFunction=op['maskTransformFunction'] if 'maskTransformFunction' in op else None,
                                        parameter_dependencies=op['parameter_dependencies'] if 'parameter_dependencies' in op else None,
                                        qaList=op['qaList'] if 'qaList' in op else None,
                                        donor_processor=op['donor_processor'] if 'donor_processor' in op else None)
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

def returnNoneFunction(*arg,**kwargs):
    return None

def getRule(name, globals={}, noopRule=returnNoneFunction, default_module=None):
    if name is None:
        return noopRule
    import importlib
    global customRuleFunc
    if name in customRuleFunc:
        return customRuleFunc[name]
    else:
        if '.' not in name:
            mod_name = default_module
            func_name = name
            func = globals.get(name)
            if func is None:
                if default_module is None:
                    logging.getLogger('maskgen').error('Rule Function {} not found'.format(name))
                    return noopRule
            else:
                return func
        else:
            mod_name, func_name = name.rsplit('.', 1)
        try:
            mod = importlib.import_module(mod_name)
            func = getattr(mod, func_name)
            customRuleFunc[name] = func
            return func#globals.get(name)
        except Exception as e:
            logging.getLogger('maskgen').error('Unable to load rule {}: {}'.format(name,str(e)))
            return noopRule

def getProjectProperties():
    """

    :return:
    @rtype: list of ProjectProperty
    """
    return getMetDataLoader().projectProperties


def getSemanticGroups():
    return [prop.description for prop in getProjectProperties() if prop.semanticgroup]

def getFilters(filtertype):
    if filtertype == 'filtergroups':
        return getMetDataLoader().filters
    else:
        return {}

def _load_software_from_resource(fileName):
    fileName = getFileName(fileName)
    software_set = {'image': {}, 'video': {}, 'audio': {},'zip': {}, 'collection':{}}
    category_set = {'gan': [], 'other': []}
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
            software_name = columns[2].strip()
            software_category = columns[1].strip().lower()
            versions = [strip_version(x.strip()) for x in columns[3:] if len(x) > 0]
            if software_type not in ['both', 'image', 'video', 'audio', 'all', 'collection']:
                logging.getLogger('maskgen').error('Invalid software type on line ' + str(line_no) + ': ' + l)
            elif len(software_name) > 0:
                types = ['image', 'video', 'zip'] if software_type == 'both' else [software_type]
                types = ['image', 'video', 'audio', 'zip'] if software_type == 'all' else types
                types = ['video', 'audio'] if software_type == 'audio' else types
                types = ['zip'] if software_type == 'zip' else types
                types = ['collection'] if software_type == 'collection' else types
                for stype in types:
                    software_set[stype][software_name] = versions
            category_set[software_category].append(software_name)
    return {'software_set': software_set, 'category_set': category_set}

class MetaDataLoader:
    version = ''
    software_set = {}
    software_category_set = {}
    operations = {}
    filters = {}
    operationsByCategory = {}
    node_properties = {}

    def __init__(self):
        self.reload()

    def reload(self):
        self.operations, self.filters, self.operationsByCategory, self.node_properties, self.operation_version = self._load_operations('operations.json')
        self.software_set, self.software_category_set = self._load_software('software.csv')
        self.projectProperties = self._load_project_properties('project_properties.json')
        self.manipulator_names = self._load_manipulators('ManipulatorCodeNames.txt')

    def _load_software(self, fileName):
        sets = _load_software_from_resource(fileName)
        softwareset = sets['software_set']
        categoryset = sets['category_set']
        return softwareset, categoryset

    def merge(self,fileName):
        softwareset = _load_software_from_resource(fileName)['software_set']
        bytesOne = {}
        bytesTwo = {}
        namesOne = {}
        namesTwo = {}
        for atype,names in self.software_set.iteritems():
            for name in names:
                bytesOne[name] = atype
            for name,versions in names.iteritems():
                namesOne[name] = versions
        for atype,names in softwareset.iteritems():
            for name in names:
                bytesTwo[name] = atype
            for name,versions in names.iteritems():
                namesTwo[name] = versions
        for name,versions in namesTwo.iteritems():
            if name not in namesOne:
                logging.getLogger('maskgen').warn( 'missing ' + name)
            else:
                for version in versions:
                    if version not in namesOne[name]:
                        logging.getLogger('maskgen').warn( 'missing ' + str(version) + ' in ' + name)
        for name, atype in bytesTwo.iteritems():
            if name  in bytesOne and atype != bytesOne[name]:
                logging.getLogger('maskgen').warn( 'missing ' + str(atype) + ' in ' + name)


    def _load_manipulators(self, filename):
        file = getFileName(filename)
        if file is not None:
            if os.path.exists(file):
                with open(file, 'r') as fp:
                    return [name.strip() for name in fp.readlines() if len(name) > 1]

    def _load_project_properties(self, fileName):
        """

        :param fileName:
        :return:
        @rtype: list ProjectProperty
        """
        loadCustomRules()
        projectProperties = loadProjectPropertyJSON(fileName)
        return projectProperties

    def _load_operations(self, fileName):
        operations, filters, version, node_properties = loadOperationJSON(fileName)
        logging.getLogger('maskgen').info('Loaded operation version ' + version)
        operationsByCategory = {}
        for op, data in operations.iteritems():
            category = data.category
            if category not in operationsByCategory:
                operationsByCategory[category] = []
            operationsByCategory[category].append(op)
        return operations, filters, operationsByCategory, node_properties, version

    def propertiesToCSV(self, filename):
        import csv
        csv.register_dialect('unixpwd', delimiter=',', quoting=csv.QUOTE_MINIMAL)
        with open(filename, 'w') as fp:
            fp_writer = csv.writer(fp)
            fp_writer.writerow(['JSON Name', 'Full Name', 'level', 'description', 'type', 'operations'])
            for property in self.projectProperties:
                opdata = [
                    property.name,
                    property.description,
                    'semantic group' if property.semanticgroup else 'node' if property.node else 'project',
                    property.information,
                    property.type,
                    ' '.join(property.operations) if property.operations is not None else ''
                ]
                try:
                    fp_writer.writerow(opdata)
                except:
                    print ' '.join(opdata)

    def operationsToCSV(self,filename):
        import csv
        csv.register_dialect('unixpwd', delimiter=',', quoting=csv.QUOTE_MINIMAL)
        with open(filename,'w') as fp:
            fp_writer = csv.writer(fp)
            fp_writer.writerow(['category','operation','description','transitions','argument1','argument1 description'])
            for cat, ops in self.operationsByCategory.iteritems():
                for opname in ops:
                    op = self.operations[opname]
                    opdata = [
                        cat,
                        op.name,
                        op.description,
                        ' '.join(op.transitions),
                    ]
                    for name, val in op.mandatoryparameters.iteritems():
                        opdata.extend([name, val['description']])
                    for name, val in op.optionalparameters.iteritems():
                        opdata.extend([name, val['description']])
                    try:
                        fp_writer.writerow(opdata)
                    except:
                        print ' '.join(opdata)

    def getProperty(self, propertyname):
        for prop in self.projectProperties:
            if propertyname == prop.name:
                return prop

def getProjectProperty(name, prop_type):
    """

    :param name: name of property
    :param prop_type: one of 'semanticgroup' or 'node' or 'project'
    :return: ProjectProperty
    @type name: str
    @type prop_type: str
    @rtype: list of ProjectProperty
    """
    for prop in getProjectProperties():
        if (prop.description == name or prop.name == name) and \
                ((prop.semanticgroup and prop_type == 'semanticgroup') or
                 (prop.node and prop_type == 'node') or (prop_type == 'project'
                 and not (prop.node or prop.semanticgroup))):
            return prop
    return None


def toSoftware(columns):
    return [x.strip() for x in columns[1:] if len(x) > 0]

def getMetDataLoader():
    """
    :return:
    @rtype: MetaDataLoader
    """
    if 'metadataLoader' not in global_config:
        global_config['metadataLoader'] = MetaDataLoader()
    return global_config['metadataLoader']

def operationVersion():
    return getMetDataLoader().version

def validateSoftware(softwareName, softwareVersion):
    for software_type, typed_software_set in getMetDataLoader().software_set.iteritems():
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
        if software_type is None:
            return []
        return list(getMetDataLoader().software_set[software_type].keys())

    def get_versions(self, name, software_type=None, version=None):
        types_to_check = getMetDataLoader().software_set.keys() if software_type is None else [software_type]
        for type_to_check in types_to_check:
            versions = getMetDataLoader().software_set[type_to_check][name] if name in getMetDataLoader().software_set[type_to_check] else None
            if versions is None:
                continue
            if version is not None and strip_version(version) not in versions:
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
