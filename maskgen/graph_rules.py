from software_loader import getOperations, SoftwareLoader, getProjectProperties
from tool_set import validateAndConvertTypedValue, fileTypeChanged, fileType,getMilliSeconds
import new
from types import MethodType
from group_filter import getOperationWithGroups

rules = {}
global_loader = SoftwareLoader()
project_property_rules = {}


class Proxy(object):

    def __init__(self, target):
        self._target = target

    def __getattr__(self, name):
        target = self._target
        f = getattr(target, name)
        if isinstance(f, MethodType):
            # Rebind the method to the target.
            return new.instancemethod(f.im_func, self, target.__class__)
        else:
            return f

class GraphProxy(Proxy):
    results = dict()
    "Caching Proxy"
    def get_image(self, name, metadata=dict()):
        if name not in self.results:
            self.results[name] = self._target.get_image(name, metadata=metadata)
        return self.results[name]

def run_rules(op, graph, frm, to):
    global rules
    if len(rules) == 0:
        setup()
    graph = GraphProxy(graph)
    results = initial_check(op, graph, frm, to)
    for rule in (rules[op] if op in rules else []):
        res = rule(graph, frm, to)
        if res is not None:
            results.append(res)
    return results


def initial_check(op, graph, frm, to):
    edge = graph.get_edge(frm, to)
    operationResult = check_operation(edge, op, graph, frm, to)
    if operationResult is not None:
        return operationResult
    versionResult = check_version(edge, op, graph, frm, to)
    errorsResult = check_errors(edge, op, graph, frm, to)
    mandatoryResult = check_mandatory(edge, op, graph, frm, to)
    argResult = check_arguments(edge, op, graph, frm, to)
    result = []
    if versionResult is not None:
        result.append(versionResult)
    if argResult is not None:
        result.extend(argResult)
    if mandatoryResult is not None:
        result.extend(mandatoryResult)
    if errorsResult is not None:
        result.extend(errorsResult)
    return result


def check_operation(edge, op, graph, frm, to):
    if op == 'Donor':
        return None
    opObj = getOperationWithGroups(op)
    if opObj is None:
        return ['Operation ' + op + ' is invalid']

def check_errors(edge, op, graph, frm, to):
    if 'errors' in edge and edge['errors'] and len(edge['errors']) > 0:
        return [('Link has mask processing errors')]

def check_mandatory(edge, op, graph, frm, to):
    if op == 'Donor':
        return None
    opObj = getOperationWithGroups(op)
    if opObj is None:
        return [op + ' is not a valid operation'] if op != 'Donor' else []
    args = edge['arguments'] if 'arguments' in edge  else []
    frm_file = graph.get_image(frm)[1]
    frm_file_type = fileType(frm_file)
    missing = [param for param in opObj.mandatoryparameters.keys() if
               (param not in args or len(str(args[param])) == 0) and param != 'inputmaskname'
               and ('source' not in opObj.mandatoryparameters[param] or opObj.mandatoryparameters[param]['source'] == frm_file_type)]
    if 'inputmaskname' in opObj.mandatoryparameters.keys() and (
            'inputmaskname' not in edge or edge['inputmaskname'] is None or len(edge['inputmaskname']) == 0):
        missing.append('inputmaskname')
    return [('Mandatory parameter ' + m + ' is missing') for m in missing]


def check_version(edge, op, graph, frm, to):
    global global_loader
    if op == 'Donor':
        return None
    if 'softwareName' in edge and 'softwareVersion' in edge:
        sname = edge['softwareName']
        sversion = edge['softwareVersion']
        if sversion not in global_loader.get_versions(sname):
            return sversion + ' not in approved set for software ' + sname
    return None


def check_arguments(edge, op, graph, frm, to):
    if op == 'Donor':
        return None
    opObj = getOperationWithGroups(op,fake=True)
    args = [(k, v) for k, v in opObj.mandatoryparameters.iteritems()]
    args.extend([(k, v) for k, v in opObj.optionalparameters.iteritems()])
    results = []
    for argName, argDef in args:
        try:
            argValue = getValue(edge, 'arguments.' + argName)
            if argValue:
                validateAndConvertTypedValue(argName, argValue, opObj)
        except ValueError as e:
            results.append(argName + str(e))
    return results


def setup():
    ops = getOperations()
    for op, data in ops.iteritems():
        set_rules(op, data.rules)


def set_rules(op, ruleNames):
    global rules
    rules[op] = [globals().get(name) for name in ruleNames if len(name) > 0]


def findOp(graph, node_id, op):
    preds = graph.predecessors(node_id)
    if preds is None or len(preds) == 0:
        return False
    for pred in preds:
        if graph.get_edge(pred, node_id)['op'] == op:
            return True
        elif findOp(graph, pred, op):
            return True
    return False


def rotationCheck(graph, frm, to):
    edge = graph.get_edge(frm, to)
    args = edge['arguments'] if 'arguments' in edge  else {}
    frm_img = graph.get_image(frm)[0]
    to_img = graph.get_image(to)[0]
    if 'Image Rotated' not in args:
        args['Image Rotated'] = ('yes' if frm_img.size[0] != frm_img.size[1] else 'no')
        return
    rotated = args['Image Rotated'] == 'yes'
    if rotated and frm_img.size == to_img.size and frm_img.size[0] != frm_img.size[1]:
        return 'Image was not rotated as stated by the parameter Image Rotated'
    elif not rotated and frm_img.size != to_img.size:
        return 'Image was rotated. Parameter Image Rotated is set to "no"'
    return None


def checkFileTypeChange(graph, frm, to):
    frm_file = graph.get_image(frm)[1]
    to_file = graph.get_image(to)[1]
    if fileTypeChanged(to_file, frm_file):
        return 'operation not permitted to change the type of image or video file'
    return None


def check_eight_bit(graph, frm, to):
    img, to_file = graph.get_image(to)
    if to_file.lower().endswith('jpg') and (img.size[0] % 8 > 0  or img.size[1] % 8 > 0):
        return '(Warning) JPEG image size is not aligned to 8x8 pixels'
    return None

def checkForDonorWithRegion(graph, frm, to):
    pred = graph.predecessors(to)
    if len(pred) < 2:
        return 'donor image missing'
    donor = pred[0] if pred[1] == frm else pred[1]
    if not findOp(graph, donor, 'SelectRegion'):
        return 'SelectRegion missing on path to donor'
    return None

def checkForDonor(graph, frm, to):
    pred = graph.predecessors(to)
    if len(pred) < 2:
        return 'donor image/video missing'
    return None


def checkLengthSame(graph, frm, to):
    """ the length of video should not change
    """
    edge = graph.get_edge(frm, to)
    durationChangeTuple = getValue(edge, 'metadatadiff[0].duration')
    if durationChangeTuple is not None and durationChangeTuple[0] == 'change':
        return "Length of video has changed"


def checkLengthSmaller(graph, frm, to):
    edge = graph.get_edge(frm, to)
    durationChangeTuple = getValue(edge, 'metadatadiff[0].duration')
    if durationChangeTuple is None or \
            (durationChangeTuple[0] == 'change' and \
                         getMilliSeconds(durationChangeTuple[1])[0] < getMilliSeconds(durationChangeTuple[2])[0]):
        return "Length of video is not shorter"


def checkLengthBigger(graph, frm, to):
    edge = graph.get_edge(frm, to)
    durationChangeTuple = getValue(edge, 'metadatadiff[0].duration')
    if durationChangeTuple is None or \
            (durationChangeTuple[0] == 'change' and \
                         getMilliSeconds(durationChangeTuple[1])[0] > getMilliSeconds(durationChangeTuple[2])[0]):
        return "Length of video is not longer"

def seamCarvingCheck(graph, frm, to):
    change = getSizeChange(graph, frm, to)
    if change is not None and change[0] != 0 and change[1] != 0:
        return 'seam carving should not alter both dimensions of an image'
    return None

def checkSIFT(graph, frm, to):
    """
    Currently a marker for SIFT.
    TODO: This operation should check SIFT transform matrix for images and video in the edge
    :param graph:
    :param frm:
    :param to:
    :return:
    """
    return None

def sizeChanged(graph, frm, to):
    change = getSizeChange(graph, frm, to)
    if change is not None and (change[0] == 0 and change[1] == 0):
        return 'operation should change the size of the image'
    return None


def checkSizeAndExif(graph, frm, to):
    change = getSizeChange(graph, frm, to)
    if change is not None and (change[0] != 0 or change[1] != 0):
        edge = graph.get_edge(frm, to)
        orientation = getValue(edge, 'exifdiff.Orientation')
        if orientation is not None:
            if type(orientation) is list or type(orientation) is tuple:
                orientation = orientation[-1]
            if '270' in orientation or '90' in orientation:
                frm_shape = graph.get_image(frm)[0].size
                to_shape = graph.get_image(to)[0].size
                if frm_shape[0] == to_shape[1] and frm_shape[1] == to_shape[0]:
                    return None
        return 'operation is not permitted to change the size of the image'
    return None

def checkSize(graph, frm, to):
    change = getSizeChange(graph, frm, to)
    if change is not None and (change[0] != 0 or change[1] != 0):
        return 'operation is not permitted to change the size of the image'
    return None


def getSizeChange(graph, frm, to):
    edge = graph.get_edge(frm, to)
    change = edge['shape change'] if edge is not None and 'shape change' in edge else None
    if change is not None:
        xyparts = change[1:-1].split(',')
        x = int(xyparts[0].strip())
        y = int(xyparts[1].strip())
        return (x, y)
    return None


def getValue(obj, path, convertFunction=None):
    """"Return the value as referenced by the path in the embedded set of dictionaries as referenced by an object
        obj is a node or edge
        path is a dictionary path: a.b.c
        convertFunction converts the value

        This function recurses
    """
    if not path:
        return convertFunction(obj) if convertFunction and obj else obj

    current = obj
    part = path
    splitpos = path.find(".")

    if splitpos > 0:
        part = path[0:splitpos]
        path = path[splitpos + 1:]
    else:
        path = None

    bpos = part.find('[')
    pos = 0
    if bpos > 0:
        pos = int(part[bpos + 1:-1])
        part = part[0:bpos]

    if part in current:
        current = current[part]
        if type(current) is list or type(current) is tuple:
            if bpos > 0:
                current = current[pos]
            else:
                result = []
                for item in current:
                    v = getValue(item, path, convertFunction)
                    if v:
                        result.append(v)
                return result
        return getValue(current, path, convertFunction)
    return None

def _setupPropertyRules():
    global project_property_rules
    if len(project_property_rules) == 0:
        for prop in getProjectProperties():
            if prop.rule is not None:
                project_property_rules[prop.name] = globals().get(prop.rule)

def blurLocalRule( edges):
    found = False
    for edge in edges:
        if edge['op'] == 'AdditionalEffectFilterBlur':
            found = 'global' not in edge or edge['global'] == 'no'
        if found:
            break
    return 'yes' if found else 'no'

def histogramGlobalRule( edges):
    found = False
    for edge in edges:
        if edge['op'] == 'IntensityNormalization':
            found = 'global' not in edge or edge['global'] == 'yes'
        if found:
            break
    return 'yes' if found else 'no'

def contrastGlobalRule(edges):
    found = False
    for edge in edges:
        if edge['op'] == 'IntensityContrast':
            found = 'global' not in edge or edge['global'] == 'yes'
        if found:
            break
    return 'yes' if found else 'no'

def colorGlobalRule(edges):
    found = False
    for edge in edges:
        op = getOperationWithGroups(edge['op'], fake=True)
        if op.category == 'Color' or (op.groupedCategories is not None and 'Color' in op.groupedCategories):
            found = True
            break
    return 'yes' if found else 'no'

def compositeSizeRule( edges):
    value = 0
    composite_rank = ['small', 'medium', 'large']
    for edge in edges:
        if 'change size category' in edge and 'recordMaskInComposite' in edge and \
           edge['recordMaskInComposite'] == 'yes':
           value = max(composite_rank.index(edge['change size category']),value)
    return composite_rank[value]

def _checkOpOther(op):
    if op.category in ['AdditionalEffect', 'Fill', 'Transform', 'Intensity']:
        if op.name not in ['AdditionalEffectFilterBlur', 'AdditionalEffectFilterSharpening', 'TransformResize',
                           'TransformCrop', 'TransformRotate', 'TransformSeamCarving',
                           'TransformWarp', 'IntensityNormalization', 'IntensityContrast']:
            return True
    return False

def otherEnhancementRule( edges):
    found = False
    for edge in edges:
        op = getOperationWithGroups( edge['op'] ,fake=True )
        found = _checkOpOther(op)
        if not found and  op.groupedOperations is not None:
            for imbedded_op in op.groupedOperations:
                found |= _checkOpOther(getOperationWithGroups(imbedded_op,fake=True))
        if found:
            break
    return 'yes' if found else 'no'

def _filterEdgesByOperatioName(edges,opName):
    return [ edge for edge in edges if edge['op'] == opName]

def _cleanEdges(scModel, edges):
    for edgeTuple in edges:
        node = scModel.getGraph().get_node(edgeTuple[1])
        if "pathanalysis" in node:
            node.pop("pathanalysis")
    return [edgeTuple[2] for edgeTuple in edges]

def setFinalNodeProperties(scModel, finalNode):
    _setupPropertyRules()
    edges =_cleanEdges(scModel,scModel.getEdges(finalNode))
    analysis = dict()
    for prop in getProjectProperties():
        if not prop.node:
            continue
        if prop.operation is not None:
            filtered_edges = _filterEdgesByOperatioName(edges, prop.operation)
            if len(filtered_edges) == 0:
                analysis[prop.name] = 'no'
            elif prop.parameter is None or len([edge for edge in filtered_edges if 'arguments' in edge and prop.parameter in edge['arguments'] and edge['arguments'][prop.parameter] == prop.value]) > 0:
                analysis[prop.name] = 'yes'
            else:
                analysis[prop.name] = 'no'
        if prop.rule is not None:
            analysis[prop.name] = project_property_rules[prop.name](edges)
    scModel.getGraph().update_node(finalNode, pathanalysis=analysis)

def processProjectProperties(scModel, rule=None):
    """
    Update the model's project properties inspecting the rules associated with project properties
    :param scModel: ScenarioModel
    :return:
    """
    _setupPropertyRules()
    for prop in getProjectProperties():
        edges = None
        if (rule is not None and prop.rule is None or prop.rule != rule) or prop.node:
            continue
        if prop.operation is not None:
            edges = scModel.findEdgesByOperationName(prop.operation)
            if edges is None or len(edges) == 0:
                scModel.setProjectData(prop.name,'no')
            elif prop.parameter is None or len([edge for edge in edges if edge['arguments'][prop.parameter] == prop.value]) > 0:
                scModel.setProjectData(prop.name, 'yes')
            else:
                 scModel.setProjectData(prop.name, 'no')
        if prop.rule is not None:
            scModel.setProjectData(prop.name,project_property_rules[prop.name](scModel, edges))

