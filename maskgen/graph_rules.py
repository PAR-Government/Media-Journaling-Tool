from software_loader import getOperations, SoftwareLoader, getProjectProperties, getRule
from tool_set import validateAndConvertTypedValue,openImageFile, fileTypeChanged, fileType,getMilliSecondsAndFrameCount,toIntTuple
import new
from types import MethodType
from group_filter import getOperationWithGroups
import numpy
from image_wrap import ImageWrapper
from image_graph import ImageGraph
import os
import exif
import logging
import numpy as np

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
        if rule is None:
            continue
        res = rule(graph, frm, to)
        if res is not None:
            results.append(res)
    return results


def missing_donor_inputmask(edge,dir):
    return (('inputmaskname' not in edge or \
            edge['inputmaskname'] is None or \
            len(edge['inputmaskname']) == 0 or
            not os.path.exists(os.path.join(dir,edge['inputmaskname']))) and \
            (edge['op'] == 'PasteSampled' and \
            'arguments' in edge and \
            'purpose' in edge['arguments'] and \
            edge['arguments']['purpose'] == 'clone') or
            edge['op'] == 'TransformMove')

def eligible_donor_inputmask(edge):
    return ('inputmaskname' in edge and \
                         edge['inputmaskname'] is not None and \
                         len(edge['inputmaskname']) > 0 and \
                         edge['op'] == 'PasteSampled' and \
                         'arguments' in edge and \
                         'purpose' in edge['arguments'] and \
                         edge['arguments']['purpose'] == 'clone')



def eligible_for_donor(edge):
    return edge['op'] == 'Donor' or eligible_donor_inputmask(edge)


def initial_check(op, graph, frm, to):
    edge = graph.get_edge(frm, to)
    operationResult = check_operation(edge, op, graph, frm, to)
    if operationResult is not None:
        return operationResult
    versionResult = check_version(edge, op, graph, frm, to)
    errorsResult = check_errors(edge, op, graph, frm, to)
    mandatoryResult = check_mandatory(edge, op, graph, frm, to)
    argResult = check_arguments(edge, op, graph, frm, to)
    maskResult = check_masks(edge, op, graph, frm, to)
    result = []
    if versionResult is not None:
        result.append(versionResult)
    if argResult is not None:
        result.extend(argResult)
    if mandatoryResult is not None:
        result.extend(mandatoryResult)
    if errorsResult is not None:
        result.extend(errorsResult)
    if maskResult is not None:
        result.extend(maskResult)
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

def get_journal(url, apitoken):
    import requests
    import json
    headers = {'Authorization': 'Token ' + apitoken, 'Content-Type': 'application/json'}
    url = url[:-1] if url.endswith('/') else url
    url = url + '?fields=name'
    try:
        response = requests.get(url,  headers=headers)
        if response.status_code == requests.codes.ok:
            r = json.loads(response.content)
            if 'name' in r:
                return r['name']
        else:
            logging.getLogger('maskgen').error("Unable to connect to service: {}".format(response.text))
    except Exception as e:
       logging.getLogger('maskgen').critical("Cannot reach external service " + url)
       logging.getLogger('maskgen').error(str(e))
    return url


def test_api(apitoken, url):
    import requests
    if url is None:
        return "External Service URL undefined"
    baseurl = url
    try:
        url = url[:-1] if url.endswith('/') else url
        headers = {'Authorization': 'Token ' + apitoken, 'Content-Type': 'application/json'}
        url = url + '/images/filters/?fields=manipulation_journal,high_provenance'
        data = '{ "file_name": {"type": "contains", "value": "' + 'test' + '" }}'
        response = requests.post(url, data=data, headers=headers)
        if response.status_code != requests.codes.ok:
            return "Error calling external service {} : {}".format(baseurl,str(response.content))
    except Exception as e:
        return "Error calling external service: {} : {}".format(baseurl,str(e.message))
    return None

def get_fields(filename, apitoken, url):
    import requests
    import json
    if url is None:
        logging.getLogger('maskgen').critical( 'Missing external service URL.  Check settings')
        return []
    try:
        url = url[:-1] if url.endswith('/') else url
        headers = {'Authorization': 'Token ' + apitoken, 'Content-Type':'application/json'}
        url = url + '/images/filters/?fields=manipulation_journal,high_provenance'
        data = '{ "file_name": {"type": "exact", "value": "' + filename + '" }}'
        logging.getLogger('maskgen').info( 'checking external service APIs for ' + filename)
        response = requests.post(url, data=data,headers=headers)
        if response.status_code == requests.codes.ok:
            r = json.loads(response.content)
            if 'results' in r:
                result = []
                for item in r['results']:
                    info = {}
                    result.append(info)
                    if item['manipulation_journal'] is not None and \
                        len(item['manipulation_journal']) > 0:
                        info['manipulation_journal']  = get_journal(item['manipulation_journal'],apitoken)
                    info['high_provenance'] = item['high_provenance']
                return result
        else:
            logging.getLogger('maskgen').error("Unable to connect to service: {}".format(response.text))
    except Exception as e:
        logging.getLogger('maskgen').error("Error calling external service: " + str(e))
        logging.getLogger('maskgen').critical("Cannot reach external service")
    return []

def check_graph_rules(graph,node,external=False, prefLoader=None):
    import re
    import hashlib
    """

    :param graph: ImageGraph
    :param node:
    :param prefLoader:
    :return:
    @type prefLoader: MaskGenLoader
    """
    errors = []
    nodeData = graph.get_node(node)
    category = graph.getDataItem('manipulationcategory')
    multiplebaseok =  category.lower() == 'provenance' if category is not None else False

    if 'file' not in nodeData:
        errors.append('Missing file information.')
    else:
        pattern = re.compile(r'[\|\'\"\(\)\,\$\?]')
        foundItems = pattern.findall(nodeData['file'])
        if foundItems:
            errors.append("Invalid characters {}  used in file name {}.".format(str(foundItems), nodeData['file']))

    if nodeData['nodetype'] == 'final':
        fname = os.path.join(graph.dir, nodeData['file'])
        if os.path.exists(fname):
            with open(fname,'rb') as rp:
                hashname = hashlib.md5(rp.read()).hexdigest()
                if hashname not in nodeData['file']:
                    errors.append("[Warning] Final image {} is not composed of its MD5.".format( nodeData['file']))

    checked_nodes = graph.getDataItem('api_validated_node',[])
    if nodeData['file'] not in checked_nodes:
        if nodeData['nodetype'] == 'base' and external and \
                prefLoader.get_key('apitoken') is not None:
                    fields = get_fields(nodeData['file'], prefLoader.get_key('apitoken'), prefLoader.get_key('apiurl'))
                    if len(fields)  == 0:
                        errors.append("Cannot find base media file {} in the remote system".format(nodeData['file']))
                    elif not fields[0]['high_provenance']:
                        errors.append("{} media is not HP".format(nodeData['file']))
                    else:
                        checked_nodes.append(nodeData['file'])
                        graph.setDataItem('api_validated_node', checked_nodes, excludeUpdate=True)

        if nodeData['nodetype'] == 'final' and external and \
                prefLoader.get_key('apitoken') is not None:
                fields = get_fields(nodeData['file'],prefLoader.get_key('apitoken'),prefLoader.get_key('apiurl'))
                if len(fields) > 0:
                    for journal in fields:
                      if journal['manipulation_journal'] is not None and journal['manipulation_journal']  != graph.G.name:
                           errors.append("Final media node {} used in journal {}".format(nodeData['file'], journal['manipulation_journal']))
                else:
                    checked_nodes.append(nodeData['file'])
                    graph.setDataItem('api_validated_node',checked_nodes,excludeUpdate=True)

    if nodeData['nodetype'] == 'base' and not multiplebaseok:
        for othernode in graph.get_nodes():
            othernodeData = graph.get_node(othernode)
            if node != othernode and othernodeData['nodetype'] == 'base':
                errors.append("Projects should only have one base image")
    if nodeData['nodetype'] in ('base','final','donor'):
            if 'file' not in nodeData:
                errors.append('Missing media file')
            else:
                file = nodeData['file']
                suffix_pos = file.rfind ('.')
                if suffix_pos > 0:
                    if file[suffix_pos:].lower() != file[suffix_pos:]:
                        errors.append(nodeData['file'] + ' suffix (' + file[suffix_pos:] +') is not lower case')
    return errors

def check_mandatory(edge, op, graph, frm, to):
    """

    :param edge:
    :param op:
    :param graph:
    :param frm:
    :param to:
    :return:
    @type graph: ImageGraph
    """
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
    ruleApplies = True #graph.getVersion() > '0.3.1200'
    inputmasks = [param for param in opObj.optionalparameters.keys() if param == 'inputmaskname' and
                  'purpose' in edge and edge['purpose'] == 'clone' and ruleApplies]
    if ('inputmaskname' in opObj.mandatoryparameters.keys() or 'inputmaskname' in inputmasks) and (
            'inputmaskname' not in edge or edge['inputmaskname'] is None or len(edge['inputmaskname']) == 0 or
            not os.path.exists(os.path.join(graph.dir,edge['inputmaskname']))):
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


def check_masks(edge, op, graph, frm, to):
    """
      Validate a typed operation argument
      return the type converted argument if necessary
      raise a ValueError if invalid
    """
    if 'maskname' not in edge or edge['maskname'] is None or \
        len(edge['maskname']) == 0 or not os.path.exists(os.path.join(graph.dir, edge['maskname'])):
        return ['Link mask is missing. Recompute the link mask.']
    inputmasknanme = edge['inputmaskname'] if 'inputmaskname' in edge  else None
    if inputmasknanme is not None and len(inputmasknanme) > 0 and \
            not os.path.exists(os.path.join(graph.dir, inputmasknanme)):
        return ["Input mask file {} is missing".format(inputmasknanme)]
    if  inputmasknanme is not None and len(inputmasknanme) > 0 and \
         os.path.exists(os.path.join(graph.dir, inputmasknanme)):
            inputmask = openImageFile(os.path.join(graph.dir, inputmasknanme))
            if inputmask is None:
                return ["Input mask file {} is missing".format(inputmasknanme)]
            inputmask = inputmask.to_mask().to_array()
            mask = openImageFile(os.path.join(graph.dir, edge['maskname'])).invert().to_array()
            if inputmask.shape != mask.shape:
                return ['input mask name parameter has an invalid size']
            if edge['op'] == 'TransformMove':
                inputmask[inputmask>0] = 1
                mask[mask>0] = 1
                intersection = inputmask*mask
                leftover_mask = mask - intersection
                leftover_inputmask = inputmask - intersection
                masksize = sum(sum(leftover_mask))
                inputmasksize = sum(sum(leftover_inputmask))
                intersectionsize = sum(sum(intersection))
                if inputmasksize == 0 and intersectionsize == 0:
                    return ['input mask does not represent moved pixels. It is empty.']
                ratio_of_intersection = float(intersectionsize)/float(inputmasksize)
                ratio_of_difference = float(masksize) / float(inputmasksize)
                # intersection is too small or difference is too great
                if abs(ratio_of_difference-1.0) > 0.25:
                    return ['input mask does not represent the moved pixels']
def setup():
    ops = getOperations()
    for op, data in ops.iteritems():
        set_rules(op, data.rules)


def set_rules(op, ruleNames):
    global rules
    rules[op] = [getRule(name, globals=globals()) for name in ruleNames if len(name) > 0]


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

def findBase(graph, node_id):
    preds = graph.predecessors(node_id)
    if preds is None or len(preds) == 0:
        return node_id
    for pred in preds:
        edge = graph.get_edge(pred,node_id)
        if edge['op'] == 'Donor':
            continue
        return findBase(graph, pred)
    return node_id

def hasCommonParent(graph, node_id):
    preds = graph.predecessors(node_id)
    if len(preds) == 1:
        return False
    base1 = findBase(graph,preds[0])
    base2 = findBase(graph, preds[1])
    return base1 == base2


def rotationCheck(graph, frm, to):
    edge = graph.get_edge(frm, to)
    args = edge['arguments'] if 'arguments' in edge  else {}
    frm_img = graph.get_image(frm)[0]
    to_img = graph.get_image(to)[0]
    rotated = 'Image Rotated' in args and args['Image Rotated'] == 'yes'
    orientation = getValue(edge, 'exifdiff.Orientation')
    if orientation is not None:
        orientation = str(orientation)
        if '270' in orientation or '90' in orientation:
            if rotated and frm_img.size == to_img.size and frm_img.size[0] != frm_img.size[1]:
                return 'Image was not rotated as stated by the parameter Image Rotated'
    diff_frm = frm_img.size[0] - frm_img.size[1]
    diff_to = to_img.size[0] - to_img.size[1]
    if not rotated and numpy.sign(diff_frm) != numpy.sign(diff_to):
        return 'Image was rotated. Parameter Image Rotated is set to "no"'
    return None

def checkFrameTimes(graph, frm, to):
    edge = graph.get_edge(frm, to)
    args = edge['arguments'] if 'arguments' in edge  else {}
    st = None
    et = None
    for k,v in args.iteritems():
        if k.endswith('End Time'):
            et = getMilliSecondsAndFrameCount(v)
        elif k.endswith('Start Time'):
            st = getMilliSecondsAndFrameCount(v)
    if st is None and et is None:
        return None
    st = st if st is not None else (0,0)
    et = et if et is not None else (0, 0)
    if st[0] > et[0] or (st[0] == et[0] and st[1] >= et[1] and st[1] > 0):
        return 'Start Time occurs after End Time'
    return None

def checkCropSize(graph, frm, to):
    edge = graph.get_edge(frm, to)
    if 'shape change' in edge:
        changeTuple = toIntTuple(edge['shape change'])
        if changeTuple[0] > 0 or changeTuple[1] > 0:
            return 'Crop cannot increase a dimension size of the image'

def checkResizeInterpolation(graph, frm, to):
    edge = graph.get_edge(frm, to)
    interpolation = edge['arguments']['interpolation']
    if 'shape change' in edge:
        changeTuple = toIntTuple(edge['shape change'])
        sizeChange = (changeTuple[0], changeTuple[1])
        if( sizeChange[0] < 0 or sizeChange[1] < 0) and 'none' in interpolation:
            return interpolation + ' interpolation is not permitted with a decrease in size'

def checkFileTypeChange(graph, frm, to):
    frm_file = graph.get_image(frm)[1]
    to_file = graph.get_image(to)[1]
    if fileTypeChanged(to_file, frm_file):
        return 'operation not permitted to change the type of image or video file'
    return None


def serial_corr(wave, lag=1):
    n = len(wave)
    y1 = wave[lag:]
    y2 = wave[:n-lag]
    corr = np.corrcoef(y1, y2, ddof=0)[0, 1]
    return corr

def autocorr(wave):
    lags = range(len(wave)//2)
    corrs = [serial_corr(wave, lag) for lag in lags]
    return lags, corrs


def checkLevelsVsCurves(graph,frm,to):
    edge = graph.get_edge(frm, to)
    frm_file = graph.get_image(frm)[0].convert('L').to_array()
    to_file = graph.get_image(to)[0].convert('L').to_array()
    rangebins = range(257)
    lstart = np.histogram(frm_file,bins=rangebins)
    lfinish = np.histogram(to_file, bins=rangebins)
    diff = lstart[0]-lfinish[0]
    #change = lstart[0]/lfinish[0].astype('float')
    #cor(diff[-len(diff)], diff[-1])
    lags, corrs1 = autocorr(diff)
    #lags, corrs2 = autocorr(change)
    #deviation = np.std(np.diff(change))
    #regr = linear_model.LinearRegression()
    # Train the model using the training sets
    #regr.fit(np.asarray(, )
    #print ("%s %f %f" % (edge['op'], corrs1[1],deviation))
   # np.var(np.diff(x))
    #print("Mean squared error: %.2f" % np.mean( sigmoid(np.asarray(rangebins[:-1]),*popt)- diff.reshape(256, 1) ** 2))

    #The lag-one autocorrelation will serve as a score and has a reasonably straightforward statistical interpretation too.
    if corrs1[1] < 0.9:
        print '[Warning] Verify this operation was performed with Levels rather than Curves'
    return None


def checkForRawFile(graph,frm, to):
    snode = graph.get_node(frm)
    exifdata = exif.getexif(os.path.join(graph.dir, snode['file']))
    if 'File Type'  in exifdata and exifdata['File Type'] in ['AA','AAX','ACR',
                                                              'AI','AIT','AFM','ACFM','AMFM',
                                                              'PDF','PS','AVI',
                                                              'APE','ASF','BMP','DIB'
                                                              'BPG','PNG','JPEG','GIF',
                                                              'DIVX','DOC','DOCX',
                                                              'DV','EXV',
                                                              'F4V','F4A','F4P','F4B',
                                                              'EXR', 'HDR','FLV','FPF','FLAC',
                                                              'FLA','FFF','IDML',
                                                              'J2C','JPC','JP2','JPF',
                                                              'J2K','JPX','JPM',
                                                              'JPE','JPG',
                                                              'LA','LFP',
                                                              'MP4','MP3',
                                                              'M2TS','MTS','M2T','TS',
                                                              'M4A','M4B','M4P','M4V',
                                                              'MAX','MOV','QT',
                                                              'O','PAC','MIFF','MIF',
                                                              'MIE',
                                                              'JNG','MNG','PPT','PPS',
                                                              'QIF','QTI','QTIF',
                                                              'RIF','RIFF','SWF',
                                                              'VOB','TTF','TTC','SWF',
                                                              'SEQ','WEBM','WEBP']:
        return 'Only raw images permitted for this operation'
    return None

def check_pastemask(graph,frm, to):

    edge = graph.get_edge(frm, to)
    if 'arguments' in edge and edge['arguments'] is not None and 'pastemask' in edge['arguments']:
        from_img, from_file = graph.get_image(frm)
        file = os.path.join(graph.dir, edge['arguments']['pastemask'])
        if not os.path.exists(file):
            return 'Pastemask file is missing'
        pasteim = openImageFile(file)
        if pasteim.size != from_img.size:
            return 'Pastemask image does not match the size of the source image'
    return None

def check_local_warn(graph, frm, to):
    edge = graph.get_edge(frm,to)
    included_in_composite = 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] =='yes'
    is_global = 'global' in edge and edge['global'] == 'yes'
    if not is_global and not included_in_composite:
        return '[Warning] Operation link appears affect local area in the image and should be included in the composite mask'
    return None

def sampledInputMask(graph, frm, to):
    edge = graph.get_edge(frm, to)
    if 'arguments' in edge and \
            ('purpose' not in edge['arguments'] or \
              edge['arguments']['purpose'] != 'clone') and \
        'inputmaskname' in edge and \
        edge['inputmaskname'] is not None:
          edge.pop('inputmaskname')
          return 'Unneeded input mask. Auto-removal executed.'
    return None

def check_local(graph, frm, to):
    edge = graph.get_edge(frm,to)
    included_in_composite = 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] =='yes'
    is_global = 'global' in edge and edge['global'] == 'yes'
    if not is_global and not included_in_composite:
        return 'Operation link appears affect local area in the image and should be included in the composite mask'
    return None

def check_eight_bit(graph, frm, to):
    from_img, from_file = graph.get_image(frm)
    to_img, to_file = graph.get_image(to)
    if from_img.size != to_img.size and \
       to_file.lower().endswith('jpg') and  \
       (to_img.size[0] % 8 > 0  or to_img.size[1] % 8 > 0):
        return '(Warning) JPEG image size is not aligned to 8x8 pixels'
    return None

def getDonor(graph,node):
    predecessors = graph.predecessors(node)
    if len(predecessors) < 2:
        return 'donor image missing'
    for pred in predecessors:
        edge = graph.get_edge(pred, node)
        if edge['op'] == 'Donor':
            return (pred, edge)
    return None


def checkForDonorWithRegion(graph, frm, to):
    pred = graph.predecessors(to)
    if len(pred) < 2:
        return 'donor image missing'
    donor = pred[0] if pred[1] == frm else pred[1]
    edge = graph.get_edge(frm, to)
    if 'arguments' in edge and edge['arguments'] and \
        'purpose' in edge['arguments'] and edge['arguments']['purpose']  == 'blend':
        return None
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
                         getMilliSecondsAndFrameCount(durationChangeTuple[1])[0] < getMilliSecondsAndFrameCount(durationChangeTuple[2])[0]):
        return "Length of video is not shorter"


def checkPasteFrameLength(graph,frm,to):
    edge = graph.get_edge(frm, to)
    addType = getValue(edge, 'arguments.add type')
    from_node = graph.get_node(frm)
    to_node = graph.get_node(to)
    diff = 0
    duration = 0
    if 'duration' in from_node and 'duration' in to_node:
        from_duration = getMilliSecondsAndFrameCount(from_node['duration'])[0]
        to_duration = getMilliSecondsAndFrameCount(to_node['duration'])[0]
        donor_tuple = getDonor(graph, to)
        if donor_tuple is None:
            return "Missing donor"
        else:
            donor_node = graph.get_node(donor_tuple[0])
            if donor_node is not None and 'duration' in donor_node:
                duration = getMilliSecondsAndFrameCount(donor_node['duration'])[0]
                diff = (to_duration - from_duration) - duration
            else:
                return "Missing duration in donor node's meta-data"
    #if addType == 'replace' and  diff < 0:
    #    return "Replacement should maintain or increase the size"
    if addType == 'replace' and  diff > duration:
       return "Replacement contain not increase the size of video beyond the size of the donor"
    if addType != 'replace':
        return checkLengthBigger(graph,frm,to)

def checkLengthBigger(graph, frm, to):
    edge = graph.get_edge(frm, to)

    durationChangeTuple = getValue(edge, 'metadatadiff[0].duration')
    if durationChangeTuple is None or \
            (durationChangeTuple[0] == 'change' and \
                         getMilliSecondsAndFrameCount(durationChangeTuple[1])[0] > getMilliSecondsAndFrameCount(durationChangeTuple[2])[0]):
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
            orientation = str(orientation)
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


def _getSizeChange(edge):
    change = edge['shape change'] if edge is not None and 'shape change' in edge else None
    if change is not None:
        xyparts = change[1:-1].split(',')
        x = int(xyparts[0].strip())
        y = int(xyparts[1].strip())
        return (x, y)
    return None

def getSizeChange(graph, frm, to):
    return _getSizeChange(graph.get_edge(frm, to))


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


def blurLocalRule( scModel,edgeTuples):
    found = False
    for edgeTuple in edgeTuples:
        if edgeTuple.edge['op'] == 'Blur':
            found = 'global' not in edgeTuple.edge or edgeTuple.edge['global'] == 'no'
        if found:
            break
    return 'yes' if found else 'no'

def histogramGlobalRule(scModel, edgeTuples):
    found = False
    for edgeTuple in edgeTuples:
        if edgeTuple.edge['op'] == 'Normalization':
            found = 'global' not in edgeTuple.edge or edgeTuple.edge['global'] == 'yes'
        if found:
            break
    return 'yes' if found else 'no'

def contrastGlobalRule(scModel,edgeTuples):
    found = False
    for edgeTuple in edgeTuples:
        if edgeTuple.edge['op'] == 'Contrast':
            found = 'global' not in edgeTuple.edge or edgeTuple.edge['global'] == 'yes'
        if found:
            break
    return 'yes' if found else 'no'

def colorGlobalRule(scModel,edgeTuples):
    found = False
    for edgeTuple in edgeTuples:
        op = getOperationWithGroups(edgeTuple.edge['op'], fake=True)
        if op.category == 'Color' or (op.groupedCategories is not None and 'Color' in op.groupedCategories):
            found = True
            break
    return 'yes' if found else 'no'


def cloneRule(scModel,edgeTuples):
    for edgeTuple in edgeTuples:
        if ((edgeTuple.edge['op'] == 'PasteSplice' and hasCommonParent(scModel.getGraph(), edgeTuple.end)) or \
        (edgeTuple.edge['op'] == 'PasteSampled' and \
                     edgeTuple.edge['arguments']['purpose'] == 'clone')):
            return 'yes'
    return 'no'

def unitCountRule(scModel,edgeTuples):
    setofops = set()
    count = 0
    for edgeTuple in edgeTuples:
        op = getOperationWithGroups( edgeTuple.edge['op'] ,fake=True )
        count += 1 if op.category not in ['Filter','Output','Select','Donor'] and edgeTuple.edge['op'] not in setofops else 0
        setofops.add(edgeTuple.edge['op'])
    return str(count) + '-Unit'

def voiceOverlay(scModel,edgeTuples):
    for edgeTuple in edgeTuples:
        if 'arguments' in edgeTuple.edge and \
                'voice' in edgeTuple.edge['arguments'] and \
                edgeTuple.edge['arguments']['voice'] == 'yes' and \
                'add type' in edgeTuple.edge['arguments'] and \
                edgeTuple.edge['arguments']['add type'] == 'overlay':
            return 'yes'
    return 'no'

def spatialClone(scModel,edgeTuples):
    for edgeTuple in edgeTuples:
        if scModel.getNodeFileType(edgeTuple.start) != 'video':
            continue
        if edgeTuple.edge['op'] == 'PasteOverlay' and \
                hasCommonParent(scModel.getGraph(),edgeTuple.end) and \
                ('arguments' not in edgeTuple.edge or \
                         ('purpose' in edgeTuple.edge['arguments'] and \
                                      edgeTuple.edge['arguments']['purpose'] == 'add')) :
            return 'yes'
        if edgeTuple.edge['op'] == 'PasteSampled' and \
                'arguments' in edgeTuple.edge and \
                'purpose' in edgeTuple.edge['arguments'] and \
                edgeTuple.edge['arguments']['purpose'] == 'clone':
            return 'yes'
    return 'no'

def spatialSplice(scModel,edgeTuples):
    for edgeTuple in edgeTuples:
        if scModel.getNodeFileType(edgeTuple.start) != 'video':
            continue
        if edgeTuple.edge['op'] == 'PasteOverlay' and \
                not hasCommonParent(scModel.getGraph(),edgeTuple.end) and \
                ('arguments' not in edgeTuple.edge or \
                         ('purpose' in edgeTuple.edge['arguments'] and \
                          edgeTuple.edge['arguments']['purpose'] == 'add')):
            return 'yes'
        if edgeTuple.edge['op'] == 'PasteImageSpliceToFrame' and \
                'arguments' in edgeTuple.edge and \
                'purpose' in edgeTuple.edge['arguments'] and \
                edgeTuple.edge['arguments']['purpose'] == 'clone':
            return 'yes'
    return 'no'

def spatialRemove(scModel,edgeTuples):
    for edgeTuple in edgeTuples:
        if scModel.getNodeFileType(edgeTuple.start) != 'video':
            continue
        if edgeTuple.edge['op'] in ['PasteSampled','PasteOverlay','PasteImageSpliceToFrame'] and \
                'arguments' in edgeTuple.edge and \
                'purpose' in edgeTuple.edge['arguments'] and \
                edgeTuple.edge['arguments']['purpose'] == 'remove':
            return 'yes'
    return 'no'

def spatialMovingObject(scModel,edgeTuples):
    for edgeTuple in edgeTuples:
        if scModel.getNodeFileType(edgeTuple.start) != 'video':
            continue
        if edgeTuple.edge['op'] in ['PasteSampled','PasteOverlay','PasteImageSpliceToFrame'] and \
                'arguments' in edgeTuple.edge and \
                'motion mapping' in edgeTuple.edge['arguments'] and \
                edgeTuple.edge['arguments']['motion mapping'] == 'yes':
            return 'yes'
    return 'no'

def voiceSwap(scModel,edgeTuples):
    for edgeTuple in edgeTuples:
        if 'arguments' in edgeTuple.edge and \
                'voice' in edgeTuple.edge['arguments'] and \
                edgeTuple.edge['arguments']['voice'] == 'yes' and \
                'add type' in edgeTuple.edge['arguments'] and \
                edgeTuple.edge['arguments']['add type'] == 'replace':
            return 'yes'
    return 'no'

def imageReformatRule(scModel, edgeTuples):
    """
       :param scModel:
       :param edgeTuples:
       :return:
       @type scModel: ImageProjectModel
       """
    start = end = None
    for edgeTuple in edgeTuples:
        if len(scModel.getGraph().predecessors(edgeTuple.start)) == 0:
            start = edgeTuple.start
        elif len(scModel.getGraph().successors(edgeTuple.end)) == 0:
            end = edgeTuple.end
    if end and start:
        snode = scModel.getGraph().get_node(start)
        enode = scModel.getGraph().get_node(end)
        startexif = exif.getexif(os.path.join(scModel.get_dir(),snode['file']))
        endexif = exif.getexif(os.path.join(scModel.get_dir(),enode['file']))
        if 'MIME Type' in startexif and 'MIME Type' in endexif and \
            startexif['MIME Type'] != endexif['MIME Type']:
            return 'yes'
        elif 'File Type' in startexif and 'File Type' in endexif and \
            startexif['File Type'] != endexif['File Type']:
            return 'yes'
    return 'no'

def medianSmoothingRule(scModel, edgeTuples):
    for edgeTuple in edgeTuples:
        if edgeTuple.edge['op'] == 'Blur' and \
            'arguments' in edgeTuple.edge and \
            'Blur Type' in edgeTuple.edge['arguments'] and \
            edgeTuple.edge['arguments']['Blur Type'] == 'Median Smoothing':
            return 'yes'
    return 'no'

def imageCompressionRule(scModel, edgeTuples):
    """

    :param scModel:
    :param edgeTuples:
    :return:
    @type scModel: ImageProjectModel
    """
    for edgeTuple in edgeTuples:
        if len(scModel.getGraph().successors(edgeTuple.end)) == 0:
            node = scModel.getGraph().get_node(edgeTuple.end)
            result = exif.getexif(os.path.join(scModel.get_dir(),node['file']))
            compression = result['Compression'].strip() if 'Compression' in result else None
            jpeg = result['File Type'].lower() == 'jpeg' if 'File Type' in result else False
            return 'yes' if  jpeg or (compression and len(compression) > 0 and not compression.lower().startswith('uncompressed')) else 'no'
    return 'no'

def semanticEventFabricationRule(scModel, edgeTuples):
    return scModel.getProjectData('semanticrefabrication')

def semanticRepurposeRule(scModel, edgeTuples):
    return scModel.getProjectData('semanticrepurposing')

def semanticRestageRule(scModel, edgeTuples):
    return scModel.getProjectData('semanticrestaging')

def audioactivityRule(scModel,edgeTuples):
    for edgeTuple in edgeTuples:
        op = getOperationWithGroups(edgeTuple.edge['op'], fake=True )
        found = (op.category == 'Audio')
        if not found and  op.groupedOperations is not None:
            for imbedded_op in op.groupedOperations:
                found |= imbedded_op.category == 'Audio'
    return 'yes' if found else 'no'

def compositeSizeRule(scModel, edgeTuples):
    value = 0
    composite_rank = ['small', 'medium', 'large']
    for edgeTuple in edgeTuples:
        if 'change size category' in edgeTuple.edge and 'recordMaskInComposite' in edgeTuple.edge and \
            edgeTuple.edge['recordMaskInComposite'] == 'yes':
           value = max(composite_rank.index(edgeTuple.edge['change size category']),value)
    return composite_rank[value]

def _checkOpOther(op):
    if op.category in ['AdditionalEffect', 'Fill', 'Transform', 'Intensity', 'Layer', 'Filter', 'CGI']:
        if op.name not in ['Blur', 'Sharpening', 'TransformResize',
                           'TransformCrop', 'TransformRotate', 'TransformSeamCarving',
                           'TransformWarp', 'Normalization', 'Contrast']:
            return True
    return False

def provenanceRule(scModel, edgeTuples):
    """

    :param scModel:
    :param edgeTuples:
    :return:
    @type scModel: ImageProjectModel
    """
    bases = set()
    for node in scModel.getNodeNames():
        nodedata = scModel.getGraph().get_node(node)
        if nodedata['nodetype'] == 'final':
            bases.add(scModel.getBaseImage(node))
    return 'yes' if len(bases) > 1 else 'no'


def manipulationCategoryRule(scModel, edgeTuples):
    best = ''
    for node in scModel.getNodeNames():
        nodedata = scModel.getGraph().get_node(node)
        if 'pathanalysis' in nodedata and \
                'manipulationcategory' in nodedata['pathanalysis'] and \
                nodedata['pathanalysis']['manipulationcategory'] > best:
            best = nodedata['pathanalysis']['manipulationcategory']
    return best

def otherEnhancementRule(scModel, edgeTuples):
    found = False
    for edgeTuple in edgeTuples:
        if scModel.getNodeFileType(edgeTuple.start) != 'image':
            continue
        op = getOperationWithGroups(edgeTuple.edge['op'], fake=True )
        found = _checkOpOther(op)
        if not found and  op.groupedOperations is not None:
            for imbedded_op in op.groupedOperations:
                found |= _checkOpOther(getOperationWithGroups(imbedded_op,fake=True))
        if found:
            break
    return 'yes' if found else 'no'

def videoOtherEnhancementRule(scModel, edgeTuples):
    found = False
    for edgeTuple in edgeTuples:
        if scModel.getNodeFileType(edgeTuple.start) != 'video':
            continue
        op = getOperationWithGroups( edgeTuple.edge['op'] ,fake=True )
        found = _checkOpOther(op)
        if not found and  op.groupedOperations is not None:
            for imbedded_op in op.groupedOperations:
                found |= _checkOpOther(getOperationWithGroups(imbedded_op,fake=True))
        if found:
            break
    return 'yes' if found else 'no'

def _filterEdgesByOperatioName(edges,opName):
    return [ edgeTuple for edgeTuple in edges if edgeTuple.edge['op'] == opName]

def _filterEdgesByNodeType(scModel, edges, nodetype):
    return [ edgeTuple for edgeTuple in edges if scModel.getNodeFileType(edgeTuple.start) == nodetype]

def _cleanEdges(scModel, edges):
    for edgeTuple in edges:
        node = scModel.getGraph().get_node(edgeTuple.end)
        if "pathanalysis" in node:
            node.pop("pathanalysis")
    return [edgeTuple for edgeTuple in edges]

def setProjectSummary(scModel):
    """
    :param scModel:
    :return:
    @type scModel: ImageProjectModel
    """
    groups = []
    for edgeTuple in scModel.getGraph().get_edges():
        edge = scModel.getGraph().get_edge(edgeTuple[0],edgeTuple[1])
        if 'semanticGroups' in edge and edge['semanticGroups'] is not None:
            groups.extend(edge['semanticGroups'])
    scModel.setProjectData('semanticgroups',groups)

def setFinalNodeProperties(scModel, finalNode):
    """

    :param scModel: ImageProjectModel
    :param finalNode:
    :return:
    @type: ImageProjectModel
    @rtype: dict
    """
    _setupPropertyRules()
    edges =_cleanEdges(scModel,scModel.getEdges(finalNode))
    analysis = dict()
    for prop in getProjectProperties():
        if not prop.node and not prop.semanticgroup:
            continue
        filtered_edges= edges
        if prop.nodetype is not None:
            filtered_edges = _filterEdgesByNodeType(scModel, filtered_edges,prop.nodetype)
        if prop.semanticgroup:
            foundOne = False
            for edgeTuple in filtered_edges:
                if 'semanticGroups' in edgeTuple.edge and edgeTuple.edge['semanticGroups'] is not None and \
                                prop.description in edgeTuple.edge['semanticGroups']:
                    foundOne = True
                    break
            analysis[prop.name] = 'yes' if foundOne else 'no'
        if prop.operations is not None and len(prop.operations) > 0:
            foundOne = False
            for op in prop.operations:
                filtered_edges = _filterEdgesByOperatioName(filtered_edges, op)
                foundOne |= ((prop.parameter is None and len(filtered_edges) > 0) or len(
                    [edgeTuple for edgeTuple in filtered_edges
                     if 'arguments' in edgeTuple.edge and \
                         prop.parameter in edgeTuple.edge['arguments'] and \
                         edgeTuple.edge['arguments'][prop.parameter] == prop.value]) > 0)
            analysis[prop.name] = 'yes' if foundOne else 'no'
        if prop.rule is not None:
            analysis[prop.name] = project_property_rules[propertyRuleIndexKey(prop)](scModel,edges)
    scModel.getGraph().update_node(finalNode, pathanalysis=analysis)
    return analysis

def processProjectProperties(scModel, rule=None):
    """
    Update the model's project properties inspecting the rules associated with project properties
    :param scModel: ScenarioModel
    :return:
    """
    _setupPropertyRules()
    for prop in getProjectProperties():
        edges = None
        if (rule is not None and (prop.rule is None or prop.rule != rule)) or prop.node:
            continue
        if prop.operations is not None and len(prop.operations) > 0:
            foundOne = False
            for op in prop.operations:
                edges = scModel.findEdgesByOperationName(op)
                foundOne |= (prop.parameter is None or len([edge for edge in edges if 'arguments' in edge and \
                                                            edge['arguments'][prop.parameter] == prop.value]) > 0)
            scModel.setProjectData(prop.name, 'yes' if foundOne else 'no')
        if prop.rule is not None:
            scModel.setProjectData(prop.name,project_property_rules[propertyRuleIndexKey(prop)](scModel, edges))

def propertyRuleIndexKey(prop):
    """
    Since node and project properties can have the same name, a index into the single rule function list
    must differentiate.
    :param prop:
    :return:
    @type prop : ProjectProperty
    @rtype string
    """
    return ('n' if prop.node else 'p') + prop.name

def _setupPropertyRules():
    global project_property_rules
    if len(project_property_rules) == 0:
        for prop in getProjectProperties():
            if prop.rule is not None:
                project_property_rules[propertyRuleIndexKey(prop)] = getRule(prop.rule, globals=globals())

def getNodeSummary(scModel, node_id):
    """
    Return path analysis.  This only applicable after running processProjectProperties()
    :param scModel:
    :param node_id:
    :return:  None if not found
    @type scModel: ImageProjectModel
    @type node_id: str
    @rtype: dict
    """
    node = scModel.getGraph().get_node(node_id)
    return node['pathanalysis'] if node is not None and 'pathanalysis' in node else None

