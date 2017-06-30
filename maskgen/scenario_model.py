from image_graph import createGraph, current_version, getPathValues
import exif
import os
import numpy as np
import logging
from tool_set import *
import video_tools
from software_loader import Software, getProjectProperties, ProjectProperty, MaskGenLoader,getRule
import tempfile
import plugins
import graph_rules
from image_wrap import ImageWrapper
from PIL import Image
from group_filter import getOperationWithGroups, buildFilterOperation,GroupFilterLoader, injectGroup
from graph_auto_updates import updateJournal
import hashlib
import shutil
import collections
from threading import Lock
import mask_rules
from maskgen.image_graph import ImageGraph
import copy

def formatStat(val):
   if type(val) == float:
      return "{:5.3f}".format(val)
   return str(val)

prefLoader = MaskGenLoader()


def imageProjectModelFactory(name, **kwargs):
    return ImageProjectModel(name, **kwargs)

def loadProject(projectFileName):
    """
      Given JSON file name, open then the appropriate type of project
      @rtype: ImageProjectModel
    """
    graph = createGraph(projectFileName)
    return ImageProjectModel(projectFileName, graph=graph)

def consolidate(dict1, dict2):
    """
    :param dict1:
    :param dict2:
    :return:
    @rtype dict
    """
    d = dict(dict1)
    d.update(dict2)
    return d


EdgeTuple = collections.namedtuple('EdgeTuple', ['start','end','edge'])

def createProject(path, notify=None, base=None, suffixes=[], projectModelFactory=imageProjectModelFactory,
                  organization=None):
    """
        This utility function creates a ProjectModel given a directory.
        If the directory contains a JSON file, then that file is used as the project file.
        Otherwise, the directory is inspected for images.
        All images found in the directory are imported into the project.
        If the 'base' parameter is provided, the project is named based on that image name.
        If the 'base' parameter is not provided, the project name is set based on finding the
        first image in the list of found images, sorted in lexicographic order, starting with JPG, then PNG and then TIFF.
    :param path: directory name or JSON file
    :param notify: function pointer receiving the image (node) id and the event type
    :param base:  image name
    :param suffixes:
    :param projectModelFactory:
    :param organization:
    :return:  a tuple=> a project if found or created, returns True if created. Returns None if a project cannot be found or created.
     @type path: str
     @type notify: (str, str) -> None
     @rtype (ImageProjectModel, bool)
    """

    if path is None:
        path = '.'
        selectionSet = [filename for filename in os.listdir(path) if filename.endswith(".json") and \
                        filename != 'operations.json' and filename != 'project_properties.json']
        if len(selectionSet) == 0:
            return projectModelFactory(os.path.join('.', 'Untitled.json'), notify=notify), True
    else:
        if (path.endswith(".json")):
         return projectModelFactory(os.path.abspath(path), notify=notify), False
        selectionSet = [filename for filename in os.listdir(path) if filename.endswith(".json")]
    if  len(selectionSet) != 0 and base is not None:
        logging.getLogger('maskgen').warning('Cannot add base image/video to an existing project')
        return None
    if len(selectionSet) == 0 and base is None:
        logging.getLogger('maskgen').info( 'No project found and base image/video not provided; Searching for a base image/video')
        suffixPos = 0
        while len(selectionSet) == 0 and suffixPos < len(suffixes):
            suffix = suffixes[suffixPos]
            selectionSet = [filename for filename in os.listdir(path) if filename.lower().endswith(suffix)]
            selectionSet.sort()
            suffixPos += 1
        projectFile = selectionSet[0] if len(selectionSet) > 0 else None
        if projectFile is None:
            logging.getLogger('maskgen').warning( 'Could not find a base image/video')
            return None
    # add base is not None
    elif len(selectionSet) == 0:
        projectFile = os.path.split(base)[1]
    else:
        projectFile = selectionSet[0]
    projectFile = os.path.abspath(os.path.join(path, projectFile))
    if not os.path.exists(projectFile):
        logging.getLogger('maskgen').warning( 'Base project file ' + projectFile + ' not found')
        return None
    image = None
    existingProject = projectFile.endswith(".json")
    if not existingProject:
        image = projectFile
        projectFile = projectFile[0:projectFile.rfind(".")] + ".json"
    model = projectModelFactory(projectFile, notify=notify, baseImageFileName=image)
    if organization is not None:
        model.setProjectData('organization', organization)
    if image is not None:
        model.addImagesFromDir(path, baseImageFileName=os.path.split(image)[1], suffixes=suffixes, \
                               sortalg=lambda f: os.stat(os.path.join(path, f)).st_mtime)
    return model, not existingProject


class Probe:
    edgeId = None
    targetBaseNodeId = None
    finalNodeId = None
    targetMaskImage = None
    targetMaskFileName = None
    targetColorMaskImage = None
    targetColorMaskFileName = None
    targetChangeSizeInPixels = 0
    donorBaseNodeId = None
    donorMaskImage = None
    donorMaskFileName = None
    level = 0

    """
    @type edgeId: tuple
    @type targetBaseNodeId: str
    @type targetMaskFileName: str
    @type targetMaskImage: ImageWrapper
    @type targetChangeSizeInPixels: int
    @type targetColorMaskFileName: str
    @type targetColorMaskImage: ImageWrapper
    @type finalNodeId: str
    @type donorBaseNodeId: str
    @type donorMaskImage : ImageWrapper
    @type donorMaskFileName: str
    @type level: int

    The target is the node edgeId's target node (edgeId[1])--the image after the manipulation.
    The targetBaseNodeId is the id of the base node that supplies the base image for the target.
    The level is level from top to bottom in the tree.  Top is level 0
    """


    def __init__(self,edgeId,finalNodeId,targetBaseNodeId,targetMaskImage,targetMaskFileName,targetChangeSizeInPixels,
                 donorBaseNodeId,donorMaskImage,donorMaskFileName,level=0):
        self.edgeId = edgeId
        self.finalNodeId = finalNodeId
        self.targetBaseNodeId = targetBaseNodeId
        self.targetMaskImage = targetMaskImage
        self.targetMaskFileName = targetMaskFileName
        self.donorBaseNodeId = donorBaseNodeId
        self.donorMaskImage = donorMaskImage
        self.donorMaskFileName = donorMaskFileName
        self.targetChangeSizeInPixels = targetChangeSizeInPixels
        self.level = level


def constructCompositesGivenProbes(probes):
    """

    :param probes:
    :return:
    @type probes: list of Probe
    """

class MetaDiff:
    diffData = None

    def __init__(self, diffData):
        self.diffData = diffData

    def getMetaType(self):
        return 'EXIF'

    def getSections(self):
        return None

    def getColumnNames(self, section):
        return ['Operation', 'Old', 'New']

    def toColumns(self, section):
        d = {}
        for k, v in self.diffData.iteritems():
            old = v[1] if v[0].lower() == 'change' or v[0].lower() == 'delete' else ''
            new = v[2] if v[0].lower() == 'change' else (v[1] if v[0].lower() == 'add' else '')
            old = old.encode('ascii', 'xmlcharrefreplace')
            new = new.encode('ascii', 'xmlcharrefreplace')
            d[k] = {'Operation': v[0], 'Old': old, 'New': new}
        return d


class VideoMetaDiff:
    """
     Video Meta-data changes are represented by section.
     A special section called Global represents meta-data for the entire video.
     Other sections are in the individual streams (e.g. video and audio) of frames.
     A table of columns is produced per section.  The columns are Id, Operation, Old and New.
     Operations are add, delete and change.
     For streams, each row is identified by a time and meta-data name.
     When frames are added, the New column contains the number of frames added followed by the end time in seconds: 30:=434.4343434
     When frames are deleted, the Old column contains the number of frames removed followed by the end time in seconds: 30:=434.4343434
    """
    diffData = None

    def __init__(self, diffData):
        self.diffData = diffData

    def getMetaType(self):
        return 'FRAME'

    def getSections(self):
        return ['Global'] + self.diffData[1].keys()

    def getColumnNames(self, section):
        return ['Operation', 'Old', 'New']

    def toColumns(self, section):
        d = {}
        if section is None:
            section = 'Global'
        if section == 'Global':
            self._sectionChanges(d, self.diffData[0])
        else:
            itemTuple = self.diffData[1][section]
            if itemTuple[0] == 'add':
                d['add'] = {'Operation': '', 'Old': '', 'New': ''}
            elif itemTuple[0] == 'delete':
                d['delete'] = {'Operation': '', 'Old': '', 'New': ''}
            else:
                for changeTuple in itemTuple[1]:
                    if changeTuple[0] == 'add':
                        d[str(changeTuple[1])] = {'Operation': 'add', 'Old': '',
                                                  'New': str(changeTuple[3]) + ':=>' + str(changeTuple[2])}
                    elif changeTuple[0] == 'delete':
                        d[str(changeTuple[1])] = {'Operation': 'delete',
                                                  'Old': str(changeTuple[3]) + ':=>' + str(changeTuple[2]), 'New': ''}
                    else:
                        self._sectionChanges(d, changeTuple[4], prefix=str(changeTuple[3]))
        return d

    def _sectionChanges(self, d, sectionData, prefix=''):
        for k, v in sectionData.iteritems():
            dictKey = k if prefix == '' else prefix + ': ' + str(k)
            old = v[1] if v[0].lower() == 'change' or v[0].lower() == 'delete' else ''
            new = v[2] if v[0].lower() == 'change' else (v[1] if v[0].lower() == 'add' else '')
            if type(old) is not str:
                old = str(old)
            if type(new) is not str:
                new = str(new)
            old = old.encode('ascii', 'xmlcharrefreplace')
            new = new.encode('ascii', 'xmlcharrefreplace')
            d[dictKey] = {'Operation': v[0], 'Old': old, 'New': new}


class Modification:
    """
    Represents a single manipulation to a source node, resulting in the target node
    """
    operationName = None
    additionalInfo = ''
    # for backward compatibility and ease of access, input mask name is both arguments and
    # an instance variable
    inputMaskName = None
    # set of masks used for videos
    maskSet = None
    # Record the link in the composite.  Uses 'no' and 'yes' to mirror JSON read-ability
    recordMaskInComposite = 'no'
    # arguments used by the operation
    arguments = dict()
    # instance of Software
    software = None
    # automated
    automated = 'no'
    # errors
    errors = list()
    #generate mask
    generateMask = True
    username = ''
    ctime = ''
    start = ''
    end = ''
    semanticGroups = None

    def __init__(self, operationName, additionalInfo,
                 start='',
                 end='',
                 arguments={},
                 recordMaskInComposite=None,
                 changeMaskName=None,
                 inputMaskName=None,
                 software=None,
                 maskSet=None,
                 automated=None,
                 username=None,
                 ctime=None,
                 errors=list(),
                 semanticGroups = None):
        self.start = start
        self.end = end
        self.additionalInfo = additionalInfo
        self.maskSet = maskSet
        self.automated = automated if automated else 'no'
        self.errors = errors if errors else list()
        self.setOperationName(operationName)
        self.setArguments(arguments)
        self.semanticGroups = semanticGroups
        if inputMaskName is not None:
            self.setInputMaskName(inputMaskName)
        self.changeMaskName = changeMaskName
        self.username=username if username is not None else ''
        self.ctime =ctime if ctime is not None else datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        self.software = software
        if recordMaskInComposite is not None:
            self.recordMaskInComposite = recordMaskInComposite

    def setSemanticGroups(self, groups):
        self.semanticGroups = groups

    def setErrors(self, val):
        self.errors = val if val else list()

    def setAutomated(self, val):
        self.automated = 'yes' if val == 'yes' else 'no'

    def setMaskSet(self, maskset):
        self.maskSet = maskset

    def getSoftwareName(self):
        return self.software.name if self.software is not None and self.software.name is not None else ''

    def getSoftwareVersion(self):
        return self.software.version if self.software is not None and self.software.version is not None else ''

    def setSoftware(self, software):
        self.software = software

    def setArguments(self, args):
        self.arguments = dict()
        for k, v in args.iteritems():
            self.arguments[k] = v
            if k == 'inputmaskname':
                self.setInputMaskName(v)


    def setInputMaskName(self, inputMaskName):
        self.inputMaskName = inputMaskName
        if 'inputmaskname' not in self.arguments or self.arguments['inputmaskname'] != inputMaskName:
            self.arguments['inputmaskname'] = inputMaskName

    def setAdditionalInfo(self, info):
        self.additionalInfo = info

    def setRecordMaskInComposite(self, recordMaskInComposite):
        self.recordMaskInComposite = recordMaskInComposite

    def setOperationName(self, name):
        self.operationName = name
        if name is None or name == '':
            return
        op = getOperationWithGroups(self.operationName,warning=False)
        self.category = op.category if op is not None else None
        self.recordMaskInComposite = 'yes' if op is not None and op.includeInMask else 'no'
        self.generateMask = op.generateMask if op is not None else True


class LinkTool:
    def __init__(self):
        return

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):
        return None, {}, []

    def _addAnalysis(self, startIm, destIm, op, analysis, mask, linktype=None,
                     arguments={}, start=None, end=None, scModel=None):
        """
        Add analysis to dictionary
        :param startIm:
        :param destIm:
        :param op:
        :param analysis: fill this dictionary
        :param mask:
        :param linktype:
        :param arguments:
        :param start:
        :param end:
        :param scModel:
        :return:
        @type scModel: ImageProjectModel
        """
        import importlib
        directory=scModel.get_dir()
        opData = getOperationWithGroups(op)
        if opData is None:
            return
        arguments = dict(arguments)
        arguments['start_node']  = start
        arguments['end_node'] = end
        arguments['sc_model'] = scModel
        for analysisOp in opData.analysisOperations:
            mod_name, func_name = analysisOp.rsplit('.', 1)
            try:
                mod = importlib.import_module(mod_name)
                func = getattr(mod, func_name)
                func(analysis, startIm, destIm, mask=invertMask(mask),linktype=linktype,
                     arguments=arguments,
                     directory=directory)
            except Exception as e:
                logging.getLogger('maskgen').error('Failed to run analysis {}: {} '.format(analysisOp, str(e)))


class ImageImageLinkTool(LinkTool):
    """
    Supports mask construction and meta-data comparison when linking images to images.
    """
    def __init__(self):
        LinkTool.__init__(self)

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask and the analysis results (a dictionary)
        """
        im1 = scModel.getImage(start)
        im2 = scModel.getImage(end)
        edge = scModel.G.get_edge(start, end)
        compareFunction = None
        if edge is not None:
            operation = getOperationWithGroups(edge['op'] if edge is not None else 'NA', fake=True)
            compareFunction = operation.getCompareFunction()
        mask, analysis = createMask(im1, im2, invert=False, arguments=arguments,
                                    alternativeFunction=compareFunction)
        return im1, im2, mask, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):
        """

        :param start:
        :param destination:
        :param scModel:
        :param op:
        :param invert:
        :param arguments:
        :param skipDonorAnalysis:
        :param analysis_params:
        :return:
        @type scModel: ImageProjectModel
        """
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        errors = list()
        operation = getOperationWithGroups(op)
        if op == 'Donor':
            predecessors = scModel.G.predecessors(destination)
            mask = None
            expect_donor_mask = False
            if not skipDonorAnalysis:
                errors= list()
                for pred in predecessors:
                    pred_edge = scModel.G.get_edge(pred, destination)
                    edge_op = getOperationWithGroups(pred_edge['op'])
                    expect_donor_mask = edge_op is not None and 'checkSIFT' in edge_op.rules
                    if expect_donor_mask:
                        mask = scModel.G.get_edge_image(pred, destination, 'arguments.pastemask')[0]
                        if mask is None:
                            mask = scModel.G.get_edge_image(pred, destination, 'maskname')[0]
                        mask, analysis = interpolateMask(
                            mask, startIm, destIm,
                            arguments=consolidate(arguments,analysis_params), invert=invert)
                        if mask is not None:
                            mask = ImageWrapper(mask)
                        break
            if mask is None:
                analysis = {}
                predecessors = scModel.G.predecessors(start)
                for pred in predecessors:
                    edge = scModel.G.get_edge(pred, start)
                    # probably should change this to == 'SelectRegion'
                    if edge['op'] == 'SelectRegion':
                        mask = invertMask(scModel.G.get_edge_image(pred, start, 'maskname')[0])
                        if mask.size != startIm.size:
                            mask = mask.resize(startIm.size,Image.ANTIALIAS)
                        break
            if mask is None:
                mask = convertToMask(startIm).invert()
                if expect_donor_mask:
                    errors = ["Donor image has insufficient features for SIFT and does not have a predecessor node."]
                analysis = {}
            else:
                mask = startIm.apply_alpha_to_mask(mask)
        else:
            mask, analysis = createMask(startIm, destIm,
                                        invert=invert,
                                        arguments=arguments,
                                        alternativeFunction=operation.getCompareFunction(),
                                        convertFunction=operation.getConvertFunction())
            exifDiff = exif.compareexif(startFileName, destFileName)
            analysis = analysis if analysis is not None else {}
            analysis['exifdiff'] = exifDiff
            self._addAnalysis(startIm, destIm, op, analysis, mask, linktype='image.image',
                              arguments=consolidate(arguments,analysis_params),
                              start=start, end=destination, scModel=scModel)
        return mask, analysis, errors

class VideoImageLinkTool(ImageImageLinkTool):
    """
    Supports mask construction and meta-data comparison when linking video to image.
    """
    def __init__(self):
        ImageImageLinkTool.__init__(self)

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask and the analysis results (a dictionary)
        """
        im1, startFileName = scModel.getImageAndName(start, arguments=arguments)
        im2, destFileName = scModel.getImageAndName(end)
        edge = scModel.G.get_edge(start, end)
        operation = getOperationWithGroups(edge['op'])
        mask, analysis = createMask(im1, im2, invert=False, arguments=arguments,alternativeFunction=operation.getCompareFunction())
        return im1, im2, mask, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):
        args = dict(arguments)
        args['skipSnapshot'] = True
        startIm, startFileName = scModel.getImageAndName(start,arguments=args)
        destIm, destFileName = scModel.getImageAndName(destination)
        errors = list()
        operation = getOperationWithGroups(op)
        if op == 'Donor':
            errors = ["An video cannot directly donate to an image.  First select a frame using an appropriate operation."]
            analysis = {}
        else:
            mask, analysis = createMask(startIm, destIm, invert=invert, arguments=arguments,alternativeFunction=operation.getCompareFunction())
            exifDiff = exif.compareexif(startFileName, destFileName)
            analysis = analysis if analysis is not None else {}
            analysis['exifdiff'] = exifDiff
            self._addAnalysis(startIm, destIm, op, analysis, mask,linktype='video.image',
                              arguments=consolidate(arguments,analysis_params),
                              start=start, end=destination, scModel=scModel)
        return mask, analysis, errors

class VideoVideoLinkTool(LinkTool):
    """
     Supports mask construction and meta-data comparison when linking video to video.
     """
    def __init__(self):
        LinkTool.__init__(self)

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask set and the meta-data diff results
        """
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(end)
        mask, analysis, errors = self.compareImages(start, end, scModel, 'noOp', skipDonorAnalysis=True,
                                                              arguments=arguments,analysis_params={})
        if 'metadatadiff' in analysis:
           analysis['metadatadiff'] = VideoMetaDiff(analysis['metadatadiff'])
        if 'videomasks' in analysis:
           analysis['videomasks'] = VideoMaskSetInfo(analysis['videomasks'])
        if 'errors' in analysis:
            analysis['errors'] = VideoMaskSetInfo(analysis['errors'])
        return startIm, destIm, mask, analysis

    def _constructDonorMask(self, startFileName, destFileName, start, destination, scModel,
                            invert=False, arguments={}):
        """
          Used for Donor video or images, the mask recording a 'donation' is the inversion of the difference
          of the Donor image and its parent, it exists.
          Otherwise, the donor image mask is the donor image (minus alpha channels):
        """
        predecessors = scModel.G.predecessors(destination)
        errors = []
        for pred in predecessors:
            edge = scModel.G.get_edge(pred, destination)
            op = getOperationWithGroups(edge['op'])
            if op is not None and 'checkSIFT' in op.rules:
                return video_tools.interpolateMask(
                    os.path.join(scModel.G.dir,shortenName(start + '_' + destination, '_mask')),
                    scModel.G.dir,
                    edge['videomasks'],
                    startFileName,
                    destFileName,
                    arguments=arguments)
        return [],errors

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):

        """

        :param start:
        :param destination:
        :param scModel:
        :param op:
        :param invert:
        :param arguments:
        :param skipDonorAnalysis:
        :param analysis_params:
        :return:
        @type start: str
        @type destination: str
        @type scModel: ImageProjectModel
        @type op: str
        @type invert: bool
        @type arguments: dict
        """
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        mask, analysis = ImageWrapper(np.zeros((startIm.image_array.shape[0],startIm.image_array.shape[1])).astype('uint8')), {}
        if op != 'Donor' and not getOperationWithGroups(op,fake=True).generateMask:
            maskSet = list()
            errors = list()
        elif op == 'Donor':
            maskSet, errors = self._constructDonorMask(startFileName, destFileName,
                                  start, destination, scModel, invert=invert,
                                                       arguments=consolidate(arguments,analysis_params))
        else:
            maskSet, errors = video_tools.formMaskDiff(startFileName, destFileName,
                                                       os.path.join(scModel.G.dir, start + '_' + destination),
                                                       op,
                                                       startSegment=getMilliSecondsAndFrameCount(arguments[
                                                                                                 'Start Time']) if 'Start Time' in arguments else None,
                                                       endSegment=getMilliSecondsAndFrameCount(arguments[
                                                                                               'End Time']) if 'End Time' in arguments else None,
                                                       analysis=analysis,
                                                       arguments=consolidate(arguments, analysis_params))
        # for now, just save the first mask
        if len(maskSet) > 0:
            mask = ImageWrapper(maskSet[0]['mask'])
            for item in maskSet:
                item.pop('mask')
        analysis['masks count'] = len(maskSet)
        analysis['videomasks'] = maskSet
        metaDataDiff = video_tools.formMetaDataDiff(startFileName, destFileName)
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        self._addAnalysis(startIm, destIm, op, analysis, mask, linktype='video.video',
                          arguments=consolidate(arguments,analysis_params),
                              start=start, end=destination, scModel=scModel)
        return mask, analysis, errors

class AudioVideoLinkTool(LinkTool):
    """
     Supports mask construction and meta-data comparison when linking audio to video.
     """
    def __init__(self):
        LinkTool.__init__(self)

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask set and the meta-data diff results
        """
        analysis = dict()
        if 'metadatadiff' in analysis:
            analysis['metadatadiff'] = VideoMetaDiff(analysis['metadatadiff'])
        if 'errors' in analysis:
            analysis['errors'] = VideoMaskSetInfo(analysis['errors'])
        return None, None, None, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):
        """

        :param start:
        :param destination:
        :param scModel:
        :param op:
        :param invert:
        :param arguments:
        :param skipDonorAnalysis:
        :param analysis_params:
        :return:
        %type scModel: ImageProjectModel
        """
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        mask = ImageWrapper(np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8'))
        analysis =  dict()
        analysis['masks count'] = 0
        analysis['videomasks'] = list()
        metaDataDiff = video_tools.formMetaDataDiff(startFileName, destFileName)
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        self._addAnalysis(startIm, destIm, op, analysis, None,linktype='audio.audio',
                          arguments=consolidate(arguments,analysis_params),
                          start=start, end=destination, scModel=scModel)
        return mask, analysis, list()

class AudioAudioLinkTool(LinkTool):
    """
     Supports mask construction and meta-data comparison when linking audio to audio.
     """
    def __init__(self):
        LinkTool.__init__(self)

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask set and the meta-data diff results
        """
        analysis = dict()
        if 'metadatadiff' in analysis:
            analysis['metadatadiff'] = VideoMetaDiff(analysis['metadatadiff'])
        if 'errors' in analysis:
            analysis['errors'] = VideoMaskSetInfo(analysis['errors'])
        return None, None, None, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        analysis =  dict()
        analysis['masks count'] = 0
        analysis['videomasks'] = list()
        metaDataDiff = video_tools.formMetaDataDiff(startFileName, destFileName)
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        mask = ImageWrapper(np.zeros((startIm.image_array.shape[0],startIm.image_array.shape[1])).astype('uint8'))
        self._addAnalysis(startIm, destIm, op, analysis, None, linktype='audio.audio',
                          arguments=consolidate(arguments,analysis_params),
                          start=start, end=destination, scModel=scModel)
        return mask, analysis, list()

class VideoAudioLinkTool(LinkTool):
    """
     Supports mask construction and meta-data comparison when linking video to audio.
     """
    def __init__(self):
        LinkTool.__init__(self)

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask set and the meta-data diff results
        """
        analysis = dict()
        if 'metadatadiff' in analysis:
            analysis['metadatadiff'] = VideoMetaDiff(analysis['metadatadiff'])
        if 'errors' in analysis:
            analysis['errors'] = VideoMaskSetInfo(analysis['errors'])
        return None, None, None, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,
                      analysis_params={}):
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        mask = ImageWrapper(np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8'))
        analysis =  dict()
        analysis['masks count'] = 0
        analysis['videomasks'] = list()
        metaDataDiff = video_tools.formMetaDataDiff(startFileName, destFileName)
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        self._addAnalysis(startIm, destIm, op, analysis, None, linktype='video.audio',
                          arguments=consolidate(arguments,analysis_params),
                              start=start, end=destination, scModel=scModel)
        return mask, analysis, list()

class ImageVideoLinkTool(VideoVideoLinkTool):
    """
     Supports mask construction and meta-data comparison when linking images to images.
     """
    def __init__(self):
        VideoVideoLinkTool.__init__(self)

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        mask,analysis = ImageWrapper(np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8')),{}
        maskSet =[]
        errors = list()
        if op == 'Donor':
            maskSet, errors = self._constructDonorMask(startFileName,
                                                       destFileName,
                                                       start,
                                                       destination,
                                                       scModel,
                                                       invert=invert,
                                                       arguments=consolidate(arguments,
                                                       analysis_params))
        # for now, just save the first mask
        if len(maskSet) > 0:
            mask = ImageWrapper(maskSet[0]['mask'])
            for item in maskSet:
                item.pop('mask')
        analysis['masks count'] = len(maskSet)
        analysis['videomasks'] = maskSet
        analysis = analysis if analysis is not None else {}
        self._addAnalysis(startIm, destIm, op, analysis, mask,linktype='image.video',
                          arguments=consolidate(arguments,analysis_params),
                              start=start, end=destination, scModel=scModel)
        return mask, analysis, errors

class AddTool:
    def getAdditionalMetaData(self, media):
        return {}

class VideoAddTool(AddTool):

    def getAdditionalMetaData(self, media):
        return video_tools.getMeta(media)[0]

class OtherAddTool(AddTool):

    def getAdditionalMetaData(self, media):
        return {}

addTools = {'video': VideoAddTool(),'audio':OtherAddTool(),'image':OtherAddTool()}
linkTools = {'image.image': ImageImageLinkTool(), 'video.video': VideoVideoLinkTool(),
             'image.video': ImageVideoLinkTool(), 'video.image': VideoImageLinkTool(),
             'video.audio': VideoAudioLinkTool(), 'audio.video': AudioVideoLinkTool(),
             'audio.audio': AudioAudioLinkTool() }



class ImageProjectModel:
    """
       A ProjectModel manages a project.  A project is made up of a directed graph of Image nodes and links.
       Each link is associated with a manipulation between the source image to the target image.
       A link contains a mask(black and white) image file describing the changes.
       A mask's X&Y dimensions match the source image.
       A link contains a description of the manipulation operation, software used to perfrom the manipulation,
       analytic results comparing source to target images, and an input mask path name.  The input mask path name
       describes a mask used by the manipulation software as a parameter describing the manipulation.
       Links may be 'read-only' indicating that they are created through an automated plugin.

       A ProjectModel can be reused to open new projects.   It is designed to represent a view model (MVC).
       A ProjectModel has two state paremeters, 'start' and 'end', containing the name of image nodes in the graph.
       When both set, a link is selected.  When 'start' is set and 'end' is None, only a single image node is selected.
       Several methods on the ProjectModel depend on the state of these parameters.  For example, adding a new link
       to a image node, chooses the source node referenced by 'end' if set, otherwise it chooses the node referenced by 'start'
    """

    G = None
    start = None
    end = None
    notify = None
    """
    @type G: ImageGraph
    @type start: String
    @type end: String
    """
    lock = Lock()

    def __init__(self, projectFileName, graph=None, importImage=False, notify=None,baseImageFileName=None):
        self.notify = notify
        if graph is not None:
            graph.arg_checker_callback = self.__scan_args_callback
        self._setup(projectFileName, graph=graph,baseImageFileName=baseImageFileName)

    def get_dir(self):
        return self.G.dir

    def addImagesFromDir(self, dir, baseImageFileName=None, xpos=100, ypos=30, suffixes=list(),
                         sortalg=lambda s: s.lower()):
        """
          Bulk add all images from a given directory into the project.
          Position the images in a grid, separated by 50 vertically with a maximum height of 520.
          Images are imported in lexicographic order, first importing JPG, then PNG and finally TIFF.
          If baseImageFileName, the name of an image node, is provided, then that node is selected
          upong completion of the operation.  Otherwise, the last not imported is selected"
        """
        initialYpos = ypos
        totalSet = []
        for suffix in suffixes:
            totalSet.extend([filename for filename in os.listdir(dir) if
                             filename.lower().endswith(suffix) and \
                             not filename.endswith('_mask' + suffix) and \
                             not filename.endswith('_proxy' + suffix)])
        totalSet = sorted(totalSet, key=sortalg)
        for filename in totalSet:
            pathname = os.path.abspath(os.path.join(dir, filename))
            additional = self.getAddTool(pathname).getAdditionalMetaData(pathname)
            nname = self.G.add_node(pathname, xpos=xpos, ypos=ypos, nodetype='base',**additional)
            ypos += 50
            if ypos == 450:
                ypos = initialYpos
                xpos += 50
            if filename == baseImageFileName:
                self.start = nname
                self.end = None
        if self.notify is not None:
            self.notify((self.start, None), 'add')

    def addImage(self, pathname,cgi=False):
        maxx = max([self.G.get_node(node)['xpos'] for node in self.G.get_nodes() if 'xpos' in self.G.get_node(node)] + [50])
        maxy = max([self.G.get_node(node)['ypos'] for node in self.G.get_nodes() if 'ypos' in self.G.get_node(node)] + [50])
        additional = self.getAddTool(pathname).getAdditionalMetaData(pathname)
        nname = self.G.add_node(pathname, nodetype='base', cgi='yes' if cgi else 'no', xpos=maxx+75, ypos=maxy,**additional)
        self.start = nname
        self.end = None
        if self.notify is not None:
            self.notify((self.start, None), 'add')
        return nname

    def getEdgesBySemanticGroup(self):
        """
        :return: association of semantics groups to edge id tuples (start,end)
        @rtype: dict of list of tuple
        """
        result = {}
        for edgeid in self.getGraph().get_edges():
            for grp in self.getSemanticGroups(edgeid[0],edgeid[1]):
                if grp not in result:
                    result[grp] = [edgeid]
                else:
                    result[grp].append(edgeid)
        return result

    def add_to_edge(self,**items):
        self.G.update_edge(self.start, self.end, **items)
        self.notify((self.start, self.end),'update_edge')

    def update_edge(self, mod):
        """
        :param mod:
        :return:
        @type mod: Modification
        """
        self.G.update_edge(self.start, self.end,
                           op=mod.operationName,
                           description=mod.additionalInfo,
                           arguments={k: v for k, v in mod.arguments.iteritems() if k != 'inputmaskname'},
                           recordMaskInComposite=mod.recordMaskInComposite,
                           semanticGroups = mod.semanticGroups,
                           editable='no' if (
                                                mod.software is not None and mod.software.internal) or mod.operationName == 'Donor' else 'yes',
                           softwareName=('' if mod.software is None else mod.software.name),
                           softwareVersion=('' if mod.software is None else mod.software.version),
                           inputmaskname=mod.inputMaskName)
        self.notify((self.start, self.end), 'update_edge')
        self._save_group(mod.operationName)

    def compare(self, destination, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask and the analysis results (a dictionary)
        """
        return self.getLinkTool(self.start, destination).compare(self.start, destination, self, arguments=arguments)

    def getMetaDiff(self):
        """ Return the EXIF differences between nodes referenced by 'start' and 'end'
            Return the Frame meta-data differences between nodes referenced by 'start' and 'end'
         """
        e = self.G.get_edge(self.start, self.end)
        if e is None:
            return None
        videodiff = VideoMetaDiff(e['metadatadiff']) if 'metadatadiff' in e else None
        imagediff = MetaDiff(e['exifdiff']) if 'exifdiff' in e and len(e['exifdiff']) > 0 else None
        return imagediff if imagediff is not None else videodiff

    def getDonorAndBaseNodeTuples(self):
        """
        Return a tuple (edge, base node, list of nodes that for the path from edge to base)
        for each valid donor path through the graph
        """
        donorEdges = []
        for edge_id in self.G.get_edges():
            edge = self.G.get_edge(edge_id[0], edge_id[1])
            if graph_rules.eligible_for_donor(edge):
                donorEdges.append(edge_id)
        results = []
        for edge in donorEdges:
            baseSet = self._findBaseNodesAndPaths(edge[0],excludeDonor=True)
            for base in baseSet:
                if (edge, base) not in results:
                    results.append((edge, base[0],base[1]))
            if len(baseSet) == 0:
                results.append((edge, None, list()))
        for result in results:
            result[2].reverse()
        return results


    def getTerminalAndBaseNodeTuples(self):
        """
          Return a tuple (lead node, base node) for each valid (non-donor) path through the graph
        """
        terminalNodes = [node for node in self.G.get_nodes() if
                         len(self.G.successors(node)) == 0 and len(self.G.predecessors(node)) > 0]
        return [(node, self._findBaseNodes(node)) for node in terminalNodes]

    def getEdges(self,endNode):
        """

        :param endNode: (identifier)
        :return: tuple (start, end, edge map) for all edges ending in endNode
        """
        return self._findEdgesWithCycleDetection(endNode, excludeDonor=True, visitSet=list())

    def getNodeNames(self):
        return self.G.get_nodes()

    def isEditableEdge(self, start, end):
        e = self.G.get_edge(start, end)
        return 'editable' not in e or e['editable'] == 'yes'

    def findChild(self, parent, child):
        for suc in self.G.successors(parent):
            if suc == child or self.findChild(suc, child):
                return True
        return False

    def compress(self, all=False):
        if all:
            return [self._compress(node) for node in self.G.get_nodes()]
        else:
            return self._compress(self.start)

    def _compress(self, start, force=False):
        defaults = {'compressor.video': 'maskgen.video_tools.x264',
                    'compressor.audio': None,
                    'compressor.image': None}
        node = self.G.get_node(start)
        ftype = self.getNodeFileType(start)
        # cannot finish the action since the edge analysis was skipped
        for skipped_edge in self.G.getDataItem('skipped_edges', []):
            if skipped_edge['start'] == start:
                    return
        if (len(self.G.successors(start)) == 0 or len(self.G.predecessors(start)) == 0)  and not force:
            return
        func = getRule(prefLoader.get_key('compressor.' + ftype,
                                          default_value=defaults['compressor.' + ftype]))
        newfile = None
        if func is not None:
            newfilename = func(os.path.join(self.get_dir(),node['file']))
            if newfilename is not None:
                newfile = os.path.split(newfilename)[1]
                node['file'] = newfile
        return newfile

    def connect(self, destination, mod=Modification('Donor', ''), invert=False, sendNotifications=True,
                skipDonorAnalysis=False):
        """ Given a image node name, connect the new node to the end of the currently selected node.
             Create the mask, inverting the mask if requested.
             Send a notification to the register caller if requested.
             Return an error message on failure, otherwise return None
        """
        if self.start is None:
            return "Node node selected", False
        if not self.G.has_node(destination):
            return "Canvas out of state from model.  Node Missing.", False
        if self.findChild(destination, self.start):
            return "Cannot connect to ancestor node", False
        for suc in self.G.successors(self.start):
            if suc == destination:
                return "Cannot connect to the same node twice", False
        return self._connectNextImage(destination, mod, invert=invert, sendNotifications=sendNotifications,
                                      skipDonorAnalysis=skipDonorAnalysis)

    def getProbeSetWithoutComposites(self, skipComputation=False, otherCondition=None):
        """
         Calls constructDonors()
        :param skipComputation: If True, will skip computation of masks where possible
        :param otherCondition: filter out edges to not include in the probe set
        :return: The set of probes
        @rtype: list of Probe
        """
        self._executeSkippedComparisons()
        if not skipComputation:
            self.removeCompositesAndDonors()
        self.constructDonors(recompute=not skipComputation)
        probes = list()
        for edge_id in self.G.get_edges():
            edge = self.G.get_edge(edge_id[0], edge_id[1])
            if edge['recordMaskInComposite'] == 'yes' or (otherCondition is not None and otherCondition(edge)):
                baseNodeIdsAndLevels = self._findBaseNodesWithCycleDetection(edge_id[0])
                baseNodeId, level, path = baseNodeIdsAndLevels[0] if len(baseNodeIdsAndLevels) > 0 else (None, None)
                if skipComputation:
                    sample_probes = []
                    for finalNodeId in self._findTerminalNodes(edge_id[1]):
                        target_mask_filename = os.path.join(self.get_dir(),shortenName(
                                                            edge_id[0] + '_' + edge_id[1] + '_' + finalNodeId, '_ps.png'))
                        if os.path.exists(target_mask_filename):
                            target_mask = openImageFile(target_mask_filename)
                            self._add_final_node_with_donors(sample_probes, edge_id, finalNodeId, baseNodeId,
                                                                 target_mask, target_mask_filename,  edge_id[1],level)
                        else:
                            # missing one
                            sample_probes = []
                            break
                    if len(sample_probes) > 0:
                        probes.extend(sample_probes)
                        continue
                edgeMask = self.G.get_edge_image(edge_id[0], edge_id[1], 'maskname')[0]
                # build composite
                selectMasks =  self._getUnresolvedSelectMasksForEdge(edge)
                composite = edgeMask.invert().to_array()
                composite = mask_rules.alterComposite(edge,
                                                      edge_id[0],
                                                      edge_id[1],
                                                      composite,edgeMask.to_array(),
                                                      self.get_dir(),
                                                      graph=self.G,
                                                      top=True)
                for target_mask,finalNodeId in self._constructTransformedMask((edge_id[0],edge_id[1]), composite):
                    target_mask = target_mask.invert()
                    if finalNodeId in selectMasks:
                        try:
                           tm = openImageFile(os.path.join(self.get_dir(),selectMasks[finalNodeId]),isMask=True)
                           target_mask = tm
                        except Exception as e:
                           logging.getLogger('maskgen').error( 'bad replacement file ' + selectMasks[finalNodeId])
                    target_mask_filename = os.path.join(self.get_dir(),
                                                         shortenName(edge_id[0] + '_' + edge_id[1] + '_' + finalNodeId, '_ps.png'))
                    target_mask.save(target_mask_filename, format='PNG')
                    self._add_final_node_with_donors(probes, edge_id, finalNodeId, baseNodeId, target_mask,
                                                     target_mask_filename, edge_id[1],level)
        return probes

    def _to_color_target_name(self,name):
        return name[0:name.rfind('.png')] + '_c.png'

    def _add_final_node_with_donors(self,probes,edge_id, finalNodeId, baseNodeId, target_mask, target_mask_filename, end_node, level):
        donormasks = self.G.get_masks(end_node,'donors')
        if len(donormasks) > 0:
            for donorbase, donortuple in donormasks.iteritems():
                donor_mask_image, donor_mask_file_name = donortuple[0], donortuple[1]
                probes.append(Probe(edge_id,
                                    finalNodeId,
                                    baseNodeId,
                                    target_mask,
                                    target_mask_filename,
                                    sizeOfChange(np.asarray(target_mask).astype('uint8')),
                                    donorbase,
                                    donor_mask_image,
                                    donor_mask_file_name,
                                    level=level))
        else:
            probes.append(Probe(edge_id,
                                finalNodeId,
                                baseNodeId,
                                target_mask,
                                target_mask_filename,
                                sizeOfChange(np.asarray(target_mask).astype('uint8')),
                                None,
                                None,
                                None,
                                level=level))

    def getProbeSet(self,skipComputation=False,operationTypes=None, otherCondition=None, compositeBuilders=[ColorCompositeBuilder]):
        """
        Builds composites and donors.
        :param skipComputation: skip donor and composite construction, updating graph
        :param operationTypes:  list of operation names to include in probes, otherwise all
        :param otherCondition: a function returning True/False that takes an edge as argument
        :return: list if Probe
        @type operationTypes: list of str
        @type otherCondition: (dict) -> bool
        @rtype: list of Probe
        """
        """

        Builds composites
        :otherCondition

        """
        self._executeSkippedComparisons()
        self.__assignColors()
        probes = self.getProbeSetWithoutComposites(skipComputation=skipComputation,otherCondition=otherCondition)
        probes = sorted(probes,key=lambda probe: probe.level)
        localCompositeBuilders = [cb() for cb in compositeBuilders]
        maxpass = max([compositeBuilder.passes for compositeBuilder in localCompositeBuilders])
        composite_bases = dict()
        for passcount in range(maxpass):
            for probe in probes:
                composite_bases[probe.finalNodeId] = probe.targetBaseNodeId
                edge = self.G.get_edge(probe.edgeId[0],probe.edgeId[1])
                if (operationTypes is not None and edge['op'] not in operationTypes) or \
                    (otherCondition is not None and not otherCondition(edge)):
                    continue
                for compositeBuilder in localCompositeBuilders:
                    compositeBuilder.build(passcount,probe,edge,skipComputation)
        for finalNodeId,baseId in composite_bases.iteritems():
            for compositeBuilder in localCompositeBuilders:
                fileName, compositeMask, globalchange, changeCategory, ratio = compositeBuilder.getComposite(finalNodeId)
                self.addCompositeToNode(finalNodeId, baseId, compositeMask,fileName,
                                    changeCategory,composite_type=compositeBuilder.composite_type)
        return probes

    def removeCompositesAndDonors(self):
        """
          Remove a composite image or a donor image associated with any node
        """
        for node in self.G.get_nodes():
            self.removeCompositeFromNode(node)
            self.removeDonorFromNode(node)

    def removeCompositeFromNode(self, nodeName, compositeBuilders=[ColorCompositeBuilder]):
        """
          Remove a composite image associated with a node
        """
        localCompositeBuilders = [cb() for cb in compositeBuilders]
        if self.G.has_node(nodeName):
            for builder in localCompositeBuilders:
                if 'composite ' + builder.composite_type + ' maskname' in self.G.get_node(nodeName):
                    fname = self.G.get_node(nodeName).pop('composite ' + builder.composite_type + ' maskname')
                    if 'compositebase' in self.G.get_node(nodeName):
                        self.G.get_node(nodeName).pop('compositebase')
                    if 'composite ' + builder.composite_type + ' change size category' in self.G.get_node(nodeName):
                        self.G.get_node(nodeName).pop('composite ' + builder.composite_type + ' change size category')
                    if os.path.exists(os.path.abspath(os.path.join(self.get_dir(), fname))):
                        os.remove(os.path.abspath(os.path.join(self.get_dir(), fname)))

    def removeDonorFromNode(self, nodeName):
        """
          Remove a donor image associated with a node
        """
        if self.G.has_node(nodeName):
            if 'donors' in self.G.get_node(nodeName):
                for base,fname in self.G.get_node(nodeName).pop('donors').iteritems():
                    if os.path.exists(os.path.abspath(os.path.join(self.get_dir(), fname))):
                        os.remove(os.path.abspath(os.path.join(self.get_dir(), fname)))


    def addCompositeToNode(self, leafNode, baseNode, image, fname, category, composite_type='color'):
        """
        Add mask to leaf node and save mask to disk
        """
        if self.G.has_node(leafNode):
            try:
                image.save(os.path.abspath(os.path.join(self.get_dir(), fname)))
            except IOError:
                compositeMask = convertToMask(image)
                compositeMask.save(os.path.abspath(os.path.join(self.get_dir(), fname)))

            node = self.G.get_node(leafNode)
            self.G.addNodeFilePath('composite ' + composite_type + ' maskname','')
            node['composite ' + composite_type + ' maskname'] = fname
            node['compositebase'] = baseNode
            node['composite ' + composite_type + ' change size category'] = category

    def addDonorToNode(self, recipientNode, baseNode, mask):
        """
        Add mask to interim node and save mask to disk that has a input mask or
        a donor link
        """
        if self.G.has_node(recipientNode):
            if 'donors' not in self.G.get_node(recipientNode):
                self.G.get_node(recipientNode)['donors'] = {}
            fname = shortenName(recipientNode + '_' + baseNode, '_d_mask.png')
            self.G.get_node(recipientNode)['donors'][baseNode] = fname
            try:
                mask.save(os.path.abspath(os.path.join(self.get_dir(), fname)))
            except IOError:
                donorMask = convertToMask(mask)
                donorMask.save(os.path.abspath(os.path.join(self.get_dir(), fname)))

    def getPredecessorNode(self):
        if self.end is None:
            for pred in self.G.predecessors(self.start):
                edge = self.G.get_edge(pred,self.start)
                if edge['op'] != 'Donor':
                    return pred
        return self.start

    def getComposite(self, composite_type='color'):
        """
         Get the composite image for the selected node.
         If the composite does not exist AND the node is a leaf node, then create the composite
         Return None if the node is not a leaf node
        """
        nodeName = self.start if self.end is None else self.end
        masks = self.G.get_masks(nodeName,'composite ' + composite_type + ' maskname')
        if len(masks)==0:
            # verify the node is a leaf node
            endPointTuples = self.getTerminalAndBaseNodeTuples()
            if nodeName in [x[0] for x in endPointTuples]:
                self.constructCompositesAndDonors()
                masks = self.G.get_masks(nodeName,'composite ' + composite_type + ' maskname')
                if len(masks) == 0:
                    return None
            else:
                return self.constructComposite()
        return masks[nodeName][0]

    def getBaseImage(self,node):
        for pred in self.G.predecessors(node):
            edge = self.G.get_edge(pred, node)
            if edge['op'] != 'Donor':
                return self.getBaseImage(pred)
        return node

    def getDonorAndBaseImages(self,force=False):
        """
         Get the composite image for the selected node.
         If the composite does not exist AND the node is a leaf node, then create the composite
         Return None if the node is not a leaf node
        """
        nodeName = self.start if self.end is None else self.end
        # verify the node is a leaf node
        endPointTuples = self.getDonorAndBaseNodeTuples()
        for x in endPointTuples:
            if nodeName == x[0][1]:
                baseImage,_ = self.G.get_image(x[1])
                masks = self.G.get_masks(nodeName, 'donors')
                if len(masks) == 0 or force:
                    self.constructDonors(nodeOfInterest=nodeName, recompute=force)
                for base, tuple  in self.G.get_masks(nodeName,'donors').iteritems():
                    if base == x[1]:
                        return tuple[0],baseImage
        return None,None

    def _constructComposites(self, nodeAndMasks, stopAtNode=None, colorMap=dict(), level=IntObject(), operationTypes=None):
        """
            Walks up down the tree from base nodes, assemblying composite masks
        :param nodeAndMasks:
        :param stopAtNode: the id of the node to stop inspection
        :param edgeMap:
        :param level:
        :param operationTypes:  restrict operations to include
        :return:
        @type edgeMap: dict of (str,str):(int,[])
        @type nodeAndMasks: (str,str, np.array)
        @type stopAtNode: str
        @type level: IntObject
        @type operationTypes: list of str
        """
        result = list()
        finished = list()
        for nodeAndMask in nodeAndMasks:
            if nodeAndMask[1] == stopAtNode:
                return [nodeAndMask]
            successors = self.G.successors(nodeAndMask[1])
            if len(successors) == 0:
                finished.append(nodeAndMask)
                continue
            for suc in self.G.successors(nodeAndMask[1]):
                edge = self.G.get_edge(nodeAndMask[1], suc)
                if edge['op'] == 'Donor':
                    continue
                compositeMask = self._extendComposite(nodeAndMask[2],
                                                      edge,
                                                      nodeAndMask[1],
                                                      suc,
                                                      level=level,
                                                      colorMap=colorMap,
                                                      operationTypes=operationTypes)
                result.append((nodeAndMask[0], suc, compositeMask))
        if len(result) == 0:
            return nodeAndMasks
        finished.extend(self._constructComposites(result,
                                                  stopAtNode=stopAtNode,
                                                  level=level,
                                                  colorMap=colorMap,
                                                  operationTypes=operationTypes))
        return finished

    def _constructTransformedMask(self, edge_id, mask):
        """
        walks up down the tree from base nodes, assemblying composite masks
        return: list of tuples (transformed mask, final image id)
        @rtype:  list of (ImageWrapper,str))
        """
        results = []
        successors = self.G.successors(edge_id[1])
        for successor in successors:
            source = edge_id[1]
            target = successor
            edge = self.G.get_edge(source, target)
            if edge['op'] == 'Donor':
                continue
            edgeMask = self.G.get_edge_image(source, target, 'maskname', returnNoneOnMissing=True)[0]
            if edgeMask is None:
                raise ValueError('Missing edge mask from ' + source + ' to ' + target)
            edgeMask = edgeMask.to_array()
            newMask = mask_rules.alterComposite(edge, source, target, mask, edgeMask, self.get_dir(),graph=self.G)
            results.extend(self._constructTransformedMask((source, target), newMask))
        return results if len(successors) > 0 else [(ImageWrapper(np.copy(mask)), edge_id[1])]

    def _constructDonor(self, node, mask):
        """
          Walks up  the tree assembling donor masks"
        """
        result = []
        preds = self.G.predecessors(node)
        if len(preds) == 0:
            return [(node, mask)]
        pred_edges = [self.G.get_edge(pred,node) for pred in preds]
        for pred in preds:
            edge = self.G.get_edge(pred,node)
            donorMask = mask_rules.alterDonor(mask,
                                             pred,
                                             node,
                                             edge,
                                             self.G.get_edge_image(pred, node, 'maskname',returnNoneOnMissing=True)[0],
                                             directory=self.get_dir(),
                                             pred_edges=[p for p in pred_edges if p != edge],
                                             graph=self.G)
            result.extend(self._constructDonor(pred, donorMask))
        return result

    def getTransformedMask(self):
        """
        :return: list a mask transfomed to all final image nodes
        """
        selectMask = self.G.get_edge_image(self.start, self.end, 'maskname')[0]
        return self._constructTransformedMask((self.start, self.end), selectMask.to_array())

    def extendCompositeByOne(self,compositeMask,level=None,replacementEdgeMask=None,colorMap={}, override_args={}):
        """

        :param compositeMask:
        :param level:
        :param replacementEdgeMask:
        :param colorMap:
        :param override_args:
        :return:
        @type compositeMask: ImageWrapper
        @type level: IntObject
        @type replacementEdgeMask: ImageWrapper
        @rtype ImageWrapper
        """
        edge = self.G.get_edge(self.start, self.end)
        if len(override_args)> 0 and edge is not None:
            edge = copy.deepcopy(edge)
            dictDeepUpdate(edge,override_args)
        else:
            edge = override_args
        level = IntObject() if level is None else level
        compositeMask = self._extendComposite(compositeMask, edge, self.start, self.end,
                                              level=level,
                                              replacementEdgeMask=replacementEdgeMask,
                                              colorMap=colorMap)

        return ImageWrapper(toColor(compositeMask, intensity_map=colorMap))

    def constructCompositeForNode(self,selectedNode, level=IntObject(), colorMap=dict()):
        """
         Construct the composite mask for the selected node.
         Does not save the composite in the node.
         Returns the composite mask if successful, otherwise None
        """
        self._executeSkippedComparisons()
        baseNodes = self._findBaseNodes(selectedNode)
        if len(baseNodes) > 0:
            baseNode = baseNodes[0]
            self.__assignColors()
            composites = self._constructComposites([(baseNode, baseNode, None)],
                                                   colorMap=colorMap,
                                                   stopAtNode=selectedNode,
                                                   level = level)
            for composite in composites:
                if composite[1] == selectedNode and composite[2] is not None:
                    return composite[2]
        return None

    def constructComposite(self):
        """
         Construct the composite mask for the selected node.
         Does not save the composite in the node.
         Returns the composite mask if successful, otherwise None
        """
        colorMap = dict()
        level = IntObject()
        composite =  \
            self.constructCompositeForNode(self.end if self.end is not None else self.start,
                                           level = level,
                                           colorMap = colorMap)
        if composite is not None:
            return ImageWrapper(toColor(composite, intensity_map=colorMap))
        return None

    def executeFinalNodeRules(self):
        terminalNodes = [node for node in self.G.get_nodes() if
                         len(self.G.successors(node)) == 0 and len(self.G.predecessors(node)) > 0]
        for node in terminalNodes:
            graph_rules.setFinalNodeProperties(self, node)

    def constructCompositesAndDonors(self):
        """
          Remove all prior constructed composites.
          Find all valid base node, leaf node tuples.
          Construct the composite make along the paths from base to lead node.
          Save the composite in the associated leaf nodes.
        """
        self._executeSkippedComparisons()
        self.constructDonors()
        composites = list()
        level = IntObject()
        colorMap = dict()
        endPointTuples = self.getTerminalAndBaseNodeTuples()
        self.__assignColors()
        for baseNode in set([endPointTuple[1][0] for endPointTuple in endPointTuples]):
                composites.extend(self._constructComposites([(baseNode, baseNode, None)], colorMap=colorMap,level=level))
        changes = []
        for composite in composites:
            color_composite = toColor(composite[2], intensity_map=colorMap)
            globalchange, changeCategory, ratio = maskChangeAnalysis(toComposite(composite[2]),
                                                                     globalAnalysis=True)
            changes.append((globalchange, changeCategory, ratio))
            self.addCompositeToNode(composite[1], composite[0], ImageWrapper(
                color_composite),composite[1] + '_composite_mask.png',changeCategory, composite_type='color')
        return composites

    def constructDonors(self, nodeOfInterest=None, recompute=False):

        """
          Construct donor images
          Find all valid base node, leaf node tuples
          :return computed donors
        """
        self._executeSkippedComparisons()
        donors = list()
        for edge_id in self.G.get_edges():
            if nodeOfInterest is not None and nodeOfInterest != edge_id[1]:
                continue
            if self.G.has_mask(edge_id[1],'donors') and not recompute:
                continue
            edge = self.G.get_edge(edge_id[0],edge_id[1])
            startMask = None
            if edge['op'] == 'Donor':
                startMask = self.G.get_edge_image(edge_id[0],edge_id[1], 'maskname',returnNoneOnMissing=True)[0]
                if startMask is None:
                    raise ValueError('Missing donor mask for ' + edge_id[0] + ' to ' + edge_id[1])
            elif 'inputmaskname' in edge and \
                    edge['inputmaskname'] is not None and \
                    len(edge['inputmaskname']) > 0 and \
                    edge['recordMaskInComposite'] == 'yes':
                fullpath = os.path.abspath(os.path.join(self.get_dir(), edge['inputmaskname']))

                if not os.path.exists(fullpath):
                    raise ValueError('Missing input mask for ' + edge_id[0] + ' to ' + edge_id[1])
                #invert because these masks are white=Keep(unchanged), Black=Remove (changed)
                #we want to capture the 'unchanged' part, where as the other type we capture the changed part
                startMask = self.G.openImage(fullpath, mask=False).to_mask().invert()
                if startMask is None:
                    raise ValueError('Missing donor mask for ' + edge_id[0] + ' to ' + edge_id[1])
            if startMask is not None:
                startMask = startMask.invert().to_array()
                donorsToNodes = {}
                donor_masks = self._constructDonor(edge_id[0], np.asarray(startMask))
                for donor_mask_tuple in donor_masks:
                    donor_mask = donor_mask_tuple[1].astype('uint8')
                    if sum(sum(donor_mask > 1)) == 0:
                        continue
                    key =  donor_mask_tuple[0]
                    if key in donorsToNodes:
                        # same donor image, multiple paths to the image.
                        donorsToNodes[key][donor_mask > 1] = 255
                    else:
                       donorsToNodes[key] = donor_mask.astype('uint8')
                for key, donor_mask in donorsToNodes.iteritems():
                    self.addDonorToNode(edge_id[1], key, ImageWrapper(donor_mask).invert())
                    donors.append((edge_id[1], donor_mask))
        return donors

    def fixInputMasks(self):
        """
        Temporary: Add missing input masks
        :return:
        """
        for edge_id in self.G.get_edges():
            edge = self.G.get_edge(edge_id[0],edge_id[1])
            if graph_rules.missing_donor_inputmask(edge,self.G.dir):
                startimage,name = self.G.get_image(edge_id[0])
                finalimage, fname = self.G.get_image(edge_id[1])
                mask = self.G.get_edge_image(edge_id[0], edge_id[1], 'maskname')[0]
                inputmaskname = name[0:name.rfind('.')] + '_inputmask.png'
                ImageWrapper(composeCloneMask(mask,startimage,finalimage)).save(inputmaskname)
#                if 'arguments' not in edge:
#                    edge['arguments'] = {}
                edge['inputmaskname'] = os.path.split(inputmaskname)[1]
#               edge['arguments']['inputmaskname'] = os.path.split(inputmaskname)[1]
                self.G.setDataItem('autopastecloneinputmask','yes')

    def renametobase(self):
        """
        Rename the project to match the name of the base image
        :return:
        """
        for nodeid in self.G.get_nodes():
            node = self.G.get_node(nodeid)
            if 'nodetype' in node and node['nodetype'] == 'base':
                self.getGraph().set_name(node['file'][0:node['file'].rfind('.')])
                break

    def addNextImage(self, pathname, invert=False, mod=Modification('', ''), sendNotifications=True, position=(50, 50),
                     skipRules=False, edge_parameters={}, node_parameters={}):
        """ Given a image file name and  PIL Image, add the image to the project, copying into the project directory if necessary.
             Connect the new image node to the end of the currently selected edge.  A node is selected, not an edge, then connect
             to the currently selected node.  Create the mask, inverting the mask if requested.
             Send a notification to the register caller if requested.
             Return an error message on failure, otherwise return None
        """
        if (self.end is not None):
            self.start = self.end
        params = dict(node_parameters)
        params['xpos'] = position[0]
        params['ypos'] = position[1]
        params['nodetype'] = 'base'
        for k,v in self.getAddTool(pathname).getAdditionalMetaData(pathname).iteritems():
            params[k] = v
        destination = self.G.add_node(pathname, seriesname=self.getSeriesName(), **params)
        analysis_params = dict(edge_parameters)
        msg, status = self._connectNextImage(destination, mod, invert=invert, sendNotifications=sendNotifications,
                                             skipRules=skipRules, analysis_params=analysis_params)
        return msg, status

    def getLinkType(self, start, end):
        return self.getNodeFileType(start) + '.' + self.getNodeFileType(end)

    def getLinkTool(self, start, end):
        return linkTools[self.getLinkType(start, end)]

    def getAddTool(self, media):
        """"
        :param media:
        :return:
        @rtype : AddTool
        """
        return addTools[fileType(media)]

    def _executeSkippedComparisons(self):
        allErrors = []
        completed = []
        skipped_edges = self.G.getDataItem('skipped_edges', [])
        for edge_data in skipped_edges:
            mask, analysis, errors = self.getLinkTool(edge_data['start'], edge_data['end']).compareImages(edge_data['start'],
                                                                                 edge_data['end'],
                                                                                 self,
                                                                                 edge_data['opName'],
                                                                                 arguments=edge_data['arguments'],
                                                                                 skipDonorAnalysis=edge_data['skipDonorAnalysis'],
                                                                                 invert=edge_data['invert'],
                                                                                 analysis_params=edge_data['analysis_params'])
            completed.append((edge_data['start'], edge_data['end']))
            allErrors.extend(errors)
            self.G.update_mask(edge_data['start'], edge_data['end'], mask=mask, errors=errors, **consolidate(analysis, edge_data['analysis_params']))
        self.G.setDataItem('skipped_edges',[edge_data for edge_data in skipped_edges if (edge_data['start'], edge_data['end']) not in completed])
        msg = os.linesep.join(allErrors).strip()
        return msg if len(msg) > 0 else None

    def _compareImages(self, start, destination, opName, invert=False, arguments={}, skipDonorAnalysis=True,
                       analysis_params=dict(),
                       force=False):
        if prefLoader.get_key('skip_compare') and not force:
            self.G.setDataItem('skipped_edges', self.G.getDataItem('skipped_edges',list()) + [{"start":start,
                                                                                               "end":destination,
                                                                                               "analysis_params":analysis_params,
                                                                                               "arguments": arguments,
                                                                                               "opName": opName,
                                                                                               "skipDonorAnalysis":skipDonorAnalysis,
                                                                                               "invert":invert
                                                                                               }])
            return None, {}, []
        try:
            for k,v in getOperationWithGroups(opName).compareparameters.iteritems():
                arguments[k] = v
        except:
            pass
        return self.getLinkTool(self.start, destination).compareImages(self.start, destination, self, opName,
                                                                       arguments=arguments,
                                                                       skipDonorAnalysis=skipDonorAnalysis,
                                                                       invert=invert,
                                                                       analysis_params=analysis_params)

    def reproduceMask(self,skipDonorAnalysis=False,analysis_params=dict()):
        edge = self.G.get_edge(self.start, self.end)
        arguments= dict(edge['arguments']) if 'arguments' in edge else dict()
        if 'inputmaskname' in edge and edge['inputmaskname'] is not None:
            arguments['inputmaskname'] = edge['inputmaskname']
        mask, analysis, errors = self._compareImages(self.start, self.end, edge['op'],
                                                               arguments=arguments,
                                                               skipDonorAnalysis=skipDonorAnalysis,
                                                               analysis_params=analysis_params,
                                                               force=True)
        self.G.update_mask(self.start, self.end, mask=mask,errors=errors,**consolidate(analysis,analysis_params))

    def _connectNextImage(self, destination, mod, invert=False, sendNotifications=True, skipRules=False,
                          skipDonorAnalysis=False,
                          analysis_params={}):
        try:
            maskname = shortenName(self.start + '_' + destination, '_mask.png')
            if mod.inputMaskName is not None:
                mod.arguments['inputmaskname'] = mod.inputMaskName
            mask, analysis, errors = self._compareImages(self.start, destination, mod.operationName,
                                                                   invert=invert, arguments=mod.arguments,
                                                                   skipDonorAnalysis=skipDonorAnalysis,
                                                                   analysis_params=analysis_params)
            self.end = destination
            if errors:
                mod.errors = errors
            for k,v in analysis_params.iteritems():
                if k not in analysis:
                    analysis[k] = v
            self.__addEdge(self.start, self.end, mask, maskname, mod, analysis)

            edgeErrors = [] if skipRules else graph_rules.run_rules(mod.operationName, self.G, self.start, destination)
            msgFromRules = os.linesep.join(edgeErrors) if len(edgeErrors) > 0 else ''
            if (self.notify is not None and sendNotifications):
                self.notify((self.start, destination), 'connect')
            msgFromErrors = "Comparison errors occured" if errors and len(errors) > 0 else ''
            msg = os.linesep.join([msgFromRules, msgFromErrors]).strip()
            msg = msg if len(msg) > 0 else None
            self.labelNodes(self.start)
            self.labelNodes(destination)
            return msg, True
        except ValueError as e:
            return 'Exception (' + str(e) + ')', False

    def __scan_args_callback(self,opName, arguments):
        """
        Call back function for image graph's arg_checker_callback.
        Add any discovered arguments that are associated with
        file paths so that the image graph can managed the file
        existence and archiving
        :param opName:
        :param arguments:
        :return:
        """
        if len(arguments) > 0 and opName != 'node':
            self.__addEdgeFilePaths(getOperationWithGroups(opName, fake=True))

    def __addEdgeFilePaths(self,op):
            for k,v in op.mandatoryparameters.iteritems():
                if k =='inputmaskname':
                    continue
                if v['type'].startswith('fileset:') or v['type'].startswith('file:'):
                    self.G.addEdgeFilePath('arguments.' +k,'')
            for k,v in op.optionalparameters.iteritems():
                if k == 'inputmaskname':
                    continue
                if v['type'].startswith('fileset:') or v['type'].startswith('file:'):
                    self.G.addEdgeFilePath('arguments.' +k,'')

    def __addEdge(self, start, end, mask, maskname, mod, additionalParameters):
        if len(mod.arguments) > 0:
            additionalParameters['arguments'] = {k: v for k, v in mod.arguments.iteritems() if k != 'inputmaskname'}
        self.G.add_edge(start, end,
                             mask=mask,
                             maskname=maskname,
                             op=mod.operationName,
                             description=mod.additionalInfo,
                             recordMaskInComposite=mod.recordMaskInComposite,
                             editable='no' if (
                                                  mod.software is not None and mod.software.internal) or mod.operationName == 'Donor' else 'yes',
                             softwareName=('' if mod.software is None else mod.software.name),
                             softwareVersion=('' if mod.software is None else mod.software.version),
                             inputmaskname=mod.inputMaskName,
                             automated=mod.automated,
                             semanticGroups = mod.semanticGroups,
                             errors=mod.errors,
                             **additionalParameters)
        self._save_group(mod.operationName)

    def _save_group(self, operation_name):
        op = getOperationWithGroups(operation_name, fake=True)
        if op.groupedOperations is not None and len(op.groupedOperations) > 0:
            groups = self.G.getDataItem('groups')
            if groups is None:
                groups = dict()
            groups[operation_name] = op.groupedOperations
            self.G.setDataItem('groups',groups,excludeUpdate=True)

    def getSeriesName(self):
        """ A Series is the prefix of the first image node """
        if self.start is None:
            return None
        startNode = self.G.get_node(self.start)
        prefix = None
        if (startNode.has_key('seriesname')):
            prefix = startNode['seriesname']
        if (self.end is not None):
            endNode = self.G.get_node(self.end)
            if (endNode.has_key('seriesname')):
                prefix = startNode['seriesname']
        return prefix

    def toCSV(self, filename, additionalpaths=list(), includeAllEdges=False):
        """
        Create a CSV containing all the edges of the graph
        :param filename:
        :return: NOne
        @type filename: str
        """
        import csv
        csv.register_dialect('unixpwd', delimiter=',', quoting=csv.QUOTE_MINIMAL)
        with open(filename,"ab") as fp:
            fp_writer = csv.writer(fp)
            for edge_id in self.G.get_edges():
                edge = self.G.get_edge(edge_id[0],edge_id[1])
                if 'compositecolor' not in edge and not includeAllEdges:
                    continue
                row = [self.G.get_name(),edge_id[0],edge_id[1],edge['op'],
                       edge['compositecolor'] if 'compositecolor' in edge else '']
                for path in additionalpaths:
                    values = getPathValues(edge, path)
                    if len(values) > 0:
                        row.append(values[0])
                    else:
                        row.append('')
                fp_writer.writerow(row)

    def getName(self):
        return self.G.get_name()

    def operationImageName(self):
        return self.end if self.end is not None else self.start

    def startImageName(self):
        return self.G.get_node(self.start)['file'] if self.start is not None else ""

    def nextImageName(self):
        return self.G.get_node(self.end)['file'] if self.end is not None else ""

    def nextId(self):
        return self.end

    def undo(self):
        """ Undo the last graph edit """
        s = self.start
        e = self.end
        self.start = None
        self.end = None
        self.G.undo()
        if self.notify is not None:
            self.notify((s,e), 'undo')

    def select(self, edge):
        self.start = edge[0]
        self.end = edge[1]

    def startNew(self, imgpathname, suffixes=[], organization=None):
        """ Inititalize the ProjectModel with a new project given the pathname to a base image file in a project directory """
        projectFile = imgpathname[0:imgpathname.rfind(".")] + ".json"
        projectType = fileType(imgpathname)
        self.G = self._openProject(projectFile,projectType)
        if organization is not None:
            self.G.setDataItem('organization', organization)
        self.start = None
        self.end = None
        self.addImagesFromDir(os.path.split(imgpathname)[0], baseImageFileName=os.path.split(imgpathname)[1],
                              suffixes=suffixes, \
                              sortalg=lambda f: os.stat(os.path.join(os.path.split(imgpathname)[0], f)).st_mtime)


    def load(self, pathname):
        """ Load the ProjectModel with a new project/graph given the pathname to a JSON file in a project directory """
        self._setup(pathname)

    def _openProject(self, projectFileName, projecttype):
        return createGraph(projectFileName,
                           projecttype=projecttype,
                           arg_checker_callback=self.__scan_args_callback,
                           edgeFilePaths={'inputmaskname': 'inputmaskownership',
                                           'selectmasks.mask': '',
                                           'videomasks.videosegment': ''},
                           nodeFilePaths={'donors.*': ''})

    def _autocorrect(self):
        updateJournal(self)

    def _setup(self, projectFileName, graph=None,baseImageFileName=None):
        projecttype = None if baseImageFileName is None else fileType(baseImageFileName)
        self.G = self._openProject(projectFileName,projecttype) if graph is None else graph
        self._autocorrect()
        self.start = None
        self.end = None
        n = self.G.get_nodes()
        if len(n) > 0:
            self.start = n[0]
            s = self.G.successors(n[0])
            if len(s) > 0:
                self.end = s[0]
            else:
                p = self.G.predecessors(n[0])
                if len(p) > 0:
                    self.start = p[0]
                    self.end = n[0]
        for group, ops in self.G.getDataItem('groups', default_value={}).iteritems():
            injectGroup(group,ops)

    def getStartType(self):
        return self.getNodeFileType(self.start) if self.start is not None else 'image'

    def getEndType(self):
        return self.getNodeFileType(self.end) if self.end is not None else 'image'

    def getNodeFileType(self, nodeid):
        node = self.G.get_node(nodeid)
        if node is not None and 'filetype' in node:
            return node['filetype']
        else:
            return fileType(self.G.get_image_path(nodeid))

    def saveas(self, pathname):
        with self.lock:
            self.clear_validation_properties()
            self.G.saveas(pathname)

    def save(self):
        with self.lock:
            self.clear_validation_properties()
            self.G.save()

    def getEdgeItem(self, name, default=None):
        edge = self.G.get_edge(self.start,self.end)
        return edge[name] if name in edge else default

    def getDescriptionForPredecessor(self, node):
        for pred in self.G.predecessors(node):
            edge = self.G.get_edge(pred, node)
            if edge['op'] != 'Donor':
                return self.getModificationForEdge(pred, node, edge)
        return None

    def getDescription(self):
        if self.start is None or self.end is None:
            return None
        edge = self.G.get_edge(self.start, self.end)
        if edge is not None:
            return self.getModificationForEdge(self.start, self.end,edge)
        return None

    def getImage(self, name):
        if name is None or name == '':
            return ImageWrapper(np.zeros((250, 250, 4)).astype('uint8'))
        return self.G.get_image(name)[0]

    def getImageAndName(self, name, arguments=dict()):
        """
        :param name:
        :param arguments:
        :return:
        @rtype (ImageWrapper,str)
        """
        if name is None or name == '':
            return ImageWrapper(np.zeros((250, 250, 4)).astype('uint8'))
        return self.G.get_image(name,metadata=arguments)

    def getStartImageFile(self):
        return os.path.join(self.G.dir, self.G.get_node(self.start)['file'])

    def getNextImageFile(self):
        return os.path.join(self.G.dir, self.G.get_node(self.end)['file'])

    def startImage(self):
        return self.getImage(self.start)

    def nextImage(self):
        if self.end is None:
            dim = (250, 250) if self.start is None else self.getImage(self.start).size
            return ImageWrapper(np.zeros((dim[1], dim[0])).astype('uint8'))
        return self.getImage(self.end)

    def updateSelectMask(self,selectMasks):
        if self.end is None:
            return
        sms = []
        for k,v in selectMasks.iteritems():
            if v is not None:
                sms.append({'mask': v[0], 'node': k})
        self.G.update_edge(self.start, self.end, selectmasks=sms)

    def _getUnresolvedSelectMasksForEdge(self, edge):
        """
             A selectMask is a mask the is used in composite mask production, overriding the default link mask
        """
        images = edge['selectmasks'] if 'selectmasks' in edge  else []
        sms = {}
        for image in images:
            sms[image['node']] = image['mask']
        return sms

    def getSelectMasks(self):
        """
        A selectMask is a mask the is used in composite mask production, overriding the default link mask
        """
        if self.end is None:
            return {}
        edge  = self.G.get_edge(self.start, self.end)
        terminals = self._findTerminalNodes(self.end,excludeDonor=True, includeOps=['Recapture','TransformWarp','TransformContentAwareScale','TransformDistort','TransformSkew','TransformSeamCarving'])
        images = edge['selectmasks'] if 'selectmasks' in edge  else []
        sms = {}
        for image in images:
            if image['node'] in terminals:
                sms[image['node']] = (image['mask'], openImageFile(os.path.join(self.get_dir(), image['mask']), isMask=False))
        for terminal in terminals:
            if terminal not in sms:
                sms[terminal] = None
        return sms

    def maskImage(self):
        if self.end is None:
            dim = (250, 250) if self.start is None else self.getImage(self.start).size
            return ImageWrapper(np.zeros((dim[1], dim[0])).astype('uint8'))
        return self.G.get_edge_image(self.start, self.end, 'maskname')[0]

    def maskStats(self):
        if self.end is None:
            return ''
        edge = self.G.get_edge(self.start, self.end)
        if edge is None:
            return ''
        stat_names = ['ssim','psnr','local psnr', 'local ssim','shape change','masks count','change size category','change size ratio']
        return '  '.join([ key + ': ' + formatStat(value) for key,value in edge.items() if key in stat_names ])

    def currentImage(self):
        if self.end is not None:
            return self.getImageAndName(self.end)
        elif self.start is not None:
            return self.getImageAndName(self.start)
        return None, None

    def selectImage(self, name):
        if self.G.has_node(name):
            self.start = name
            self.end = None

    def selectEdge(self, start, end):
        if self.G.has_node(start):
           self.start = start
        if self.G.has_node(end):
           self.end = end

    def remove(self):
        s = self.start
        e = self.end
        """ Remove the selected node or edge """
        if (self.start is not None and self.end is not None):
            self.G.remove_edge(self.start, self.end)
            self.labelNodes(self.start)
            self.labelNodes(self.end)
            self.end = None
        else:
            name = self.start if self.end is None else self.end
            p = self.G.predecessors(self.start) if self.end is None else [self.start]
            self.G.remove(name, None)
            self.start = p[0] if len(p) > 0  else None
            self.end = None
            for node in p:
                self.labelNodes(node)
        if self.notify is not None:
            self.notify((s,e), 'remove')

    def getProjectData(self, item,default_value=None):
        return self.G.getDataItem(item,default_value=default_value)

    def setProjectData(self, item, value,excludeUpdate=False):
        """
        :param item:
        :param value:
        :param excludeUpdate: True if the update does not change the update time stamp on the journal
        :return:
        """
        self.G.setDataItem(item, value,excludeUpdate=excludeUpdate)

    def get_edges(self):
        return [self.G.get_edge(edge[0],edge[1]) for edge in self.G.get_edges()]

    def getVersion(self):
        """ Return the graph/software versio n"""
        return self.G.getVersion()

    def getGraph(self):
        return self.G

    def validate(self, external=False):
        """ Return the list of errors from all validation rules on the graph. """

        self._executeSkippedComparisons()
        total_errors = list()

        if len(self.G.get_nodes()) == 0:
            return total_errors

        for node in self.G.get_nodes():
            if not self.G.has_neighbors(node):
                total_errors.append((str(node), str(node), str(node) + ' is not connected to other nodes'))
            predecessors = self.G.predecessors(node)
            if len(predecessors) == 1 and self.G.get_edge(predecessors[0],node)['op'] == 'Donor':
                total_errors.append((str(predecessors[0]), str(node), str(node) +
                                      ' donor links must coincide with another link to the same destintion node'))

        nodes = self.G.get_nodes()
        anynode = nodes[0]
        nodeSet = set(nodes)

        for prop in getProjectProperties():
            if prop.mandatory:
                item = self.G.getDataItem(prop.name)
                if item is None or len(item.strip()) < 3:
                    total_errors.append((str(anynode), str(anynode), 'Project property ' + prop.description + ' is empty or invalid'))

        for found in self.G.findRelationsToNode(nodeSet.pop()):
            if found in nodeSet:
                nodeSet.remove(found)

        for node in nodeSet:
            total_errors.append((str(node), str(node), str(node) + ' is part of an unconnected subgraph'))

        total_errors.extend(self.G.file_check())

        cycleNode = self.G.getCycleNode()
        if cycleNode is not None:
            total_errors.append((str(cycleNode), str(cycleNode), "Graph has a cycle"))

        for node in self.G.get_nodes():
            for error in graph_rules.check_graph_rules(self.G,node,external=external,prefLoader=prefLoader):
                total_errors.append((str(node), str(node), error))

        for frm, to in self.G.get_edges():
            edge = self.G.get_edge(frm, to)
            op = edge['op']
            errors = graph_rules.run_rules(op, self.G, frm, to)
            if len(errors) > 0:
                total_errors.extend([(str(frm), str(to), str(frm) + ' => ' + str(to) + ': ' + err) for err in errors])
        return total_errors

    def __assignColors(self):
        level = 1
        edgeMap = dict()
        for edge_id in self.G.get_edges():
            edge = self.G.get_edge(edge_id[0],edge_id[1])
            if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'yes':
                edgeMap[edge_id] = (level,None)
                level = level + 1
        redistribute_intensity(edgeMap)
        for k, v in edgeMap.iteritems():
            self.G.get_edge(k[0], k[1])['compositecolor'] = str(list(v[1])).replace('[', '').replace(']','').replace(
                    ',', '')
            self.G.get_edge(k[0], k[1])['compositeid'] = v[0]
        return edgeMap

    def __assignLabel(self, node, label):
        prior = self.G.get_node(node)['nodetype'] if 'nodetype' in self.G.get_node(node) else None
        if prior != label:
            self.G.update_node(node, nodetype=label)
            if self.notify is not None:
                self.notify(node, 'label')

    def renameFileImages(self):
        """
        :return: list of node ids renamed
        """
        renamed = []
        for node in self.getNodeNames():
            self.labelNodes(node)
            nodeData = self.G.get_node(node)
            if nodeData['nodetype'] in ['final']:
                logging.getLogger('maskgen').info( 'Inspecting {}  for rename'.format(nodeData['file']))
                suffix_pos = nodeData['file'].rfind('.')
                suffix = nodeData['file'][suffix_pos:].lower()
                file_path_name = os.path.join(self.G.dir, nodeData['file'])
                try:
                    with open(os.path.join(self.G.dir, nodeData['file']),'rb') as rp:
                        new_file_name = hashlib.md5(rp.read()).hexdigest() + suffix
                    fullname = os.path.join(self.G.dir, new_file_name)
                except:
                    logging.getLogger('maskgen').error( 'Missing file or invalid permission: {} '.format( nodeData['file']))
                    continue
                if not os.path.exists(fullname):
                    try:
                        os.rename(file_path_name, fullname)
                        renamed.append(node)
                        logging.getLogger('maskgen').info('Renamed {} to {} '.format( nodeData['file'], new_file_name))
                        self.G.update_node(node,file=new_file_name)
                    except Exception as e:
                        try:
                            logging.getLogger('maskgen').error(('Failure to rename file {} : {}.  Trying copy').format(file_path_name,str(e)))
                            shutil.copy2(file_path_name,fullname)
                            logging.getLogger('maskgen').info(
                                'Renamed {} to {} '.format(nodeData['file'], new_file_name))
                            self.G.update_node(node, file=new_file_name)
                        except:
                            continue
                else:
                   logging.getLogger('maskgen').warning('New name ' + new_file_name + ' already exists')
        self.save()
        return renamed

    def labelNodes(self, destination):
        baseNodes = []
        donorNodes = []
        terminalNodes = []
        candidateBaseDonorNodes  = self._findBaseNodes(destination, excludeDonor=False)
        for baseCandidate in candidateBaseDonorNodes:
            foundTerminalNodes = self._findTerminalNodes(baseCandidate,excludeDonor=True)
            terminalNodes.extend(foundTerminalNodes)
            if len(foundTerminalNodes) > 0:
                baseNodes.append(baseCandidate)
            else:
                donorNodes.append(baseCandidate)
        for node in donorNodes:
            self.__assignLabel(node, 'donor')
        for node in baseNodes:
            self.__assignLabel(node, 'base')
        if len(self.G.successors(destination)) == 0:
            if len(self.G.predecessors(destination)) == 0:
                self.__assignLabel(destination, 'base')
            else:
                self.__assignLabel(destination, 'final')
        elif len(self.G.predecessors(destination)) > 0:
            self.__assignLabel(destination, 'interim')
        elif 'nodetype' not in self.G.get_node(destination):
            self.__assignLabel(destination, 'base')

    def finalNodes(self):
        final = []
        for name in self.getNodeNames():
            node = self.G.get_node(name)
            if node['nodetype'] == 'final':
                final.append(name)
        return final

    def _findTerminalNodes(self, node, excludeDonor=False,includeOps=None):
        terminalsWithOps =  self._findTerminalNodesWithCycleDetection(node, visitSet=list(),excludeDonor=excludeDonor)
        return [terminalWithOps[0] for terminalWithOps in terminalsWithOps if
                includeOps is None or len(set(includeOps).intersection(terminalWithOps[1])) > 0]

    def _findTerminalNodesWithCycleDetection(self, node, visitSet=list(),excludeDonor=False):
        succs = self.G.successors(node)
        if len(succs) == 0:
            return [(node,[])]
        res = list()
        for succ in succs:
            if succ in visitSet:
                continue
            op = self.G.get_edge(node, succ)['op']
            if  op == 'Donor' and excludeDonor:
                continue
            visitSet.append(succ)
            terminals = self._findTerminalNodesWithCycleDetection(succ,
                                                                 visitSet=visitSet,
                                                                 excludeDonor=excludeDonor)
            for term in terminals:
                 term[1].append(op)
            res.extend(terminals)
        return res

    def _findEdgesWithCycleDetection(self, node, excludeDonor=True, visitSet=list()):
        preds = self.G.predecessors(node)
        res = list()
        for pred in preds:
            if pred in visitSet:
                continue
            edge = self.G.get_edge(pred, node)
            isNotDonor = (edge['op'] != 'Donor' or not excludeDonor)
            if isNotDonor:
                visitSet.append(pred)
                res.append(EdgeTuple(start=pred,end=node,edge=edge))
            res.extend(self._findEdgesWithCycleDetection(pred, excludeDonor=excludeDonor,
                                                             visitSet=visitSet) if isNotDonor else list())
        return res

    def _findBaseNodes(self, node, excludeDonor=True):
        return [item[0] for item in self._findBaseNodesWithCycleDetection(node, excludeDonor=excludeDonor)]

    def _findBaseNodesAndPaths(self, node, excludeDonor=True):
        return [(item[0],item[2]) for item in self._findBaseNodesWithCycleDetection(node, excludeDonor=excludeDonor)]

    def _findBaseNodesWithCycleDetection(self, node, excludeDonor=True):
        preds = self.G.predecessors(node)
        res = [(node,0,list())] if len(preds) == 0 else list()
        for pred in preds:
            if  self.G.get_edge(pred, node)['op'] == 'Donor' and  excludeDonor:
                continue
            for item in self._findBaseNodesWithCycleDetection(pred, excludeDonor=excludeDonor):
                res.append((item[0],item[1]+1,item[2]))
        for item in res:
            item[2].append(node)
        return res

    def isDonorEdge(self, start, end):
        edge = self.G.get_edge(start, end)
        if edge is not None:
            return edge['op'] == 'Donor'
        return False

    def getTerminalToBasePairs(self, suffix='.jpg'):
        """
         find all pairs of leaf nodes to matching base nodes
         :return list of tuples (leaf, base)
         @rtype: list of (str,str)
        """
        endPointTuples = self.getTerminalAndBaseNodeTuples()
        pairs = list()
        for endPointTuple in endPointTuples:
            matchBaseNodes = [baseNode for baseNode in endPointTuple[1] if
                              suffix is None or self.G.get_pathname(baseNode).lower().endswith(suffix)]
            if len(matchBaseNodes) > 0:
                # if more than one base node, use the one that matches the name of the project
                projectNodeIndex = matchBaseNodes.index(self.G.get_name()) if self.G.get_name() in matchBaseNodes else 0
                baseNode = matchBaseNodes[projectNodeIndex]
                startNode = endPointTuple[0]
                # perfect match
                # if baseNode == self.G.get_name():
                #    return [(startNode,baseNode)]
                pairs.append((startNode, baseNode))
        return pairs

    def imageFromGroup(self, grp, software=None, **kwargs):
        """
        :param grp:
        :param software:
        :param kwargs:
        :return:
        @type grp GroupFilterLoader
        @type software Software
        """
        pairs_composite = []
        resultmsg = ''
        for filter in grp.filters:
            msg, pairs = self.imageFromPlugin(filter, software=software,
                                                      **kwargs)
            if msg is not None:
                resultmsg += msg
            pairs_composite.extend(pairs)
        return resultmsg, pairs_composite

    def imageFromPlugin(self, filter, software=None, **kwargs):
        """
          Create a new image from a plugin filter.
          This method is given the plugin name, Image, the full pathname of the image and any additional parameters
          required by the plugin (name/value pairs).
          The name of the resulting image contains the prefix of the input image file name plus an additional numeric index.
          If requested by the plugin (return True), the Exif is copied from the input image to the resulting image.
          The method resolves the donor parameter's name to the donor's image file name.
          If a donor is used, the method creates a Donor link from the donor image to the resulting image node.
          If an input mask file is used, the input mask file is moved into the project directory.
          Prior to calling the plugin, the output file is created and populated with the contents of the input file for convenience.
          The filter plugin must update or overwrite the contents.
          The method returns tuple with an error message and a list of pairs (links) added.  The error message may be none if no error occurred.

          @type filter: str
          @type im: ImageWrapper
          @type filename: str
          @rtype: list of (str, list (str,str))
        """
        im, filename = self.currentImage()
        op = plugins.getOperation(filter)
        suffixPos = filename.rfind('.')
        suffix = filename[suffixPos:].lower()
        preferred = plugins.getPreferredSuffix(filter)
        fullOp = buildFilterOperation(op)
        resolved,donors,graph_args = self._resolvePluginValues(kwargs,fullOp)
        if preferred is not None:
            if preferred in donors:
                suffix = os.path.splitext(resolved[preferred])[1].lower()
            else:
                suffix = preferred
        target = os.path.join(tempfile.gettempdir(), self.G.new_name(self.start, suffix=suffix))
        shutil.copy2(filename, target)
        msg = None

        self.__addEdgeFilePaths(fullOp)
        try:
            extra_args,warning_message = plugins.callPlugin(filter, im, filename, target, **resolved)
        except Exception as e:
            msg = str(e)
            extra_args = None
        if msg is not None:
            return self._pluginError(filter, msg), []
        if extra_args is not None and 'rename_target' in extra_args:
            filename = extra_args.pop('rename_target')
            newtarget = os.path.join(os.path.split(target)[0],os.path.split(filename)[1])
            shutil.copy2(target, newtarget)
            target = newtarget
        if extra_args is not None and 'output_files' in extra_args:
            file_params = extra_args.pop('output_files')
            for name,value in file_params.iteritems():
                extra_args[name] = value
                self.G.addEdgeFilePath('arguments.' + name, '')
        description = Modification(op['name'], filter + ':' + op['description'])
        sendNotifications = kwargs['sendNotifications'] if 'sendNotifications' in kwargs else True
        skipRules = kwargs['skipRules'] if 'skipRules' in kwargs else False
        if software is None:
            software = Software(op['software'], op['version'], internal=True)
        if 'recordInCompositeMask' in kwargs:
            description.setRecordMaskInComposite(kwargs['recordInCompositeMask'])
        experiment_id = kwargs['experiment_id'] if 'experiment_id' in kwargs else None
        description.setArguments(
            {k: v for k, v in graph_args.iteritems() if k not in ['sendNotifications', 'skipRules', 'experiment_id']})
        if extra_args is not None and type(extra_args) == type({}):
             for k,v in extra_args.iteritems():
                 if k not in kwargs or v is not None:
                     description.arguments[k] = v
        description.setSoftware(software)
        description.setAutomated('yes')
        msg2, status = self.addNextImage(target, mod=description, sendNotifications=sendNotifications,
                                         skipRules=skipRules,
                                         position=self._getCurrentPosition((75 if len(donors) > 0 else 0,75)),
                                         edge_parameters={'plugin_name':filter},
                                         node_parameters={'experiment_id':experiment_id} if experiment_id is not None else {})
        pairs = list()
        msg = '\n'.join([msg if msg else '',
                         warning_message if warning_message else '',
                         msg2 if msg2 else '']).strip()
        if status:
            pairs.append((self.start, self.end))
            for donor in donors:
                _end = self.end
                _start = self.start
                self.selectImage(kwargs[donor])
                self.connect(_end)
                pairs.append((kwargs[donor], _end))
                self.select((_start, _end))
                # donor error message is skipped.  This annoys me (rwgdrummer).
                # really need to classify rules and skip certain categories
                if 'donor' in msg:
                    msg = None
        os.remove(target)
        return self._pluginError(filter, msg), pairs

    def _resolvePluginValues(self, args, operation):
        parameters = {}
        stripped_args ={}
        donors = []
        arguments = copy.copy(operation.mandatoryparameters)
        arguments.update(operation.optionalparameters)
        for k, v in args.iteritems():
            if k in arguments or k in {'sendNotifications', 'skipRules', 'experiment_id', 'recordInCompositeMask'}:
                parameters[k] = v
                #if arguments[k]['type'] != 'donor':
                stripped_args[k] = v
        for k, v in args.iteritems():
            if k in arguments and \
                arguments[k]['type'] == 'donor':
                   parameters[k] = self.getImageAndName(v)[1]
                   donors.append(k)
        for arg, info in arguments.iteritems():
            if arg not in parameters and 'defaultvalue' in info and \
                        info['defaultvalue'] is not None:
                parameters[arg] = info['defaultvalue']
        return parameters, donors, stripped_args

    def _pluginError(self, filter, msg):
        if msg is not None and len(msg) > 0:
            return 'Plugin ' + filter + ' Error:\n' + msg
        return None

    def scanNextImageUnConnectedImage(self):
        """Scan for an image node with the same prefix as the currently select image node.
           Scan in lexicographic order.
           Exlude images that have neighbors.
           Return None if a image nodee is not found.
        """
        selectionSet = [node for node in self.G.get_nodes() if not self.G.has_neighbors(node) and node != self.start]
        selectionSet.sort()
        if (len(selectionSet) > 0):
            matchNameSet = [name for name in selectionSet if name.startswith(self.start)]
            selectionSet = matchNameSet if len(matchNameSet) > 0 else selectionSet
        return selectionSet[0] if len(selectionSet) > 0 else None

    def scanNextImage(self):
        """
           Scan for a file with the same prefix as the currently select image node.
           Scan in lexicographic order.
           Exlude image files with names ending in _mask or image files that are already imported.
           Return None if a file is not found.
        """

        if self.start is None:
            return None, None

        suffix = self.start
        seriesName = self.getSeriesName()
        if seriesName is not None:
            prefix = seriesName
        prefix = prefix[0:32] if len(prefix) > 32 else prefix
        files = [self.G.get_node(node)['file'] for node in self.G.get_nodes()]

        def filterFunction(file):
            return os.path.split(file)[1] not in files and \
                   not (file.rfind('_mask') > 0) and \
                   not (file.rfind('_proxy') > 0)

        def findFiles(dir, preFix, filterFunction):
            set = [os.path.abspath(os.path.join(dir, filename)) for filename in os.listdir(dir) if
                   (filename.startswith(preFix)) and filterFunction(os.path.abspath(os.path.join(dir, filename)))]
            set = sorted(set, key=lambda f: -os.stat(f).st_mtime)
            return set

        nfile = None
        for file in findFiles(self.G.dir, prefix, filterFunction):
            nfile = file
            break
        return self.G.openImage(nfile) if nfile is not None else None, nfile

    def getDescriptions(self):
        """
        :return: descriptions for all edges
         @rtype list of Modification
        """
        return [self.getModificationForEdge(edge[0],edge[1],self.G.get_edge(edge[0],edge[1])) for edge in self.G.get_edges()]

    def openImage(self, nfile):
        im = None
        if nfile is not None and nfile != '':
            im = self.G.openImage(nfile)
        return nfile, im

    def findEdgesByOperationName(self,opName):
        return [edge for edge in self.get_edges()
            if edge['op'] == opName]

    def export(self, location,include=[]):
        with self.lock:
            self.clear_validation_properties()
            self.compress(all=True)
            path, errors = self.G.create_archive(location,include=include)
            return errors

    def exporttos3(self, location, tempdir=None):
        import boto3
        from boto3.s3.transfer import S3Transfer,TransferConfig
        with self.lock:
            self.clear_validation_properties()
            self.compress(all=True)
            path, errors = self.G.create_archive(tempfile.gettempdir() if tempdir is None else tempdir)
            if len(errors) == 0:
                config = TransferConfig()
                s3 = S3Transfer(boto3.client('s3', 'us-east-1'), config)
                BUCKET = location.split('/')[0].strip()
                DIR = location[location.find('/') + 1:].strip()
                logging.getLogger('maskgen').info( 'Upload to s3://' + BUCKET + '/' + DIR + '/' + os.path.split(path)[1])
                DIR = DIR if DIR.endswith('/') else DIR + '/'
                s3.upload_file(path, BUCKET, DIR + os.path.split(path)[1],callback=S3ProgressPercentage(path))
                os.remove(path)
                if not self.notify(self.getName(),'export', location='s3://' + BUCKET + '/' + DIR +  os.path.split(path)[1]):
                    errors = [('','','Export notification appears to have failed.  Please check the logs to ascertain the problem.')]
            return errors

    def export_path(self, location):
        if self.end is None and self.start is not None:
            self.G.create_path_archive(location, self.start)
        elif self.end is not None:
            self.G.create_path_archive(location, self.end)

    def _getCurrentPosition(self, augment):
        if self.start is None:
            return (50, 50)
        startNode = self.G.get_node(self.start)
        return ((startNode['xpos'] if startNode.has_key('xpos') else 50) + augment[0],
                (startNode['ypos'] if startNode.has_key('ypos') else 50) + augment[1])

    def _extendComposite(self,compositeMask,edge,source,target,
                         replacementEdgeMask=None,
                         level=IntObject(),
                         colorMap={},
                         operationTypes=None):
        """
        Pulls the color from the compositescolor attribute of the edge
        :param compositeMask:
        :param edge:
        :param source:
        :param target:
        :param level:
        :param colorMap:
        :param operationTypes:
        :return:
        """
        if compositeMask is None:
            imarray = self.G.get_image(source)[0].to_array()
            compositeMask = np.zeros((imarray.shape[0], imarray.shape[1])).astype(('uint8'))
        # merge masks first, the mask is the same size as the input image
        # consider a cropped image.  The mask of the crop will have the change high-lighted in the border
        # consider a rotate, the mask is either ignored or has NO change unless interpolation is used.
        edgeMask = self.G.get_edge_image(source, target, 'maskname',returnNoneOnMissing=True)[0] if target is not None else None
        if edgeMask is not None:
            edgeMask =  edgeMask.to_array()
        else:
            edgeMask = replacementEdgeMask
        if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'yes' and \
                (operationTypes is None or edge['op'] in operationTypes):
            if edgeMask is None:
                raise ValueError('Missing edge mask from ' + source + ' to ' + target)
            compositeMask = mergeMask(compositeMask, edgeMask, level=level.increment())
            color = [int(x)  for x in edge['compositecolor'].split(' ')] if 'compositecolor' in edge else [0,0,0]
            colorMap[level.value] = color
        return mask_rules.alterComposite(edge,source,target,compositeMask,edgeMask,self.get_dir(),level=level.value,graph=self.G)

    def getModificationForEdge(self, start,end, edge):
        """

        :param start:
        :param end:
        :param edge:
        :return: Modification
        @type start: str
        @type end: str
        @rtype: Modification
        """
        end_node = self.G.get_node(end)
        default_ctime = end_node['ctime'] if 'ctime' in end_node else None
        return Modification(edge['op'],
                            edge['description'],
                            start=start,
                            end=end,
                            arguments=edge['arguments'] if 'arguments' in edge else {},
                            inputMaskName=edge['inputmaskname'] if 'inputmaskname' in edge and edge[
                                'inputmaskname'] and len(edge['inputmaskname']) > 0 else None,
                            changeMaskName=edge['maskname'] if 'maskname' in edge else None,
                            software=Software(edge['softwareName'] if 'softwareName' in edge else None,
                                              edge['softwareVersion'] if 'softwareVersion' in edge else None,
                                              'editable' in edge and edge['editable'] == 'no'),
                            recordMaskInComposite=edge[
                                'recordMaskInComposite'] if 'recordMaskInComposite' in edge else 'no',
                            semanticGroups=edge['semanticGroups'] if 'semanticGroups' in edge else None,
                            automated=edge['automated'] if 'automated' in edge else 'no',
                            username =edge['username'] if 'username' in edge else '',
                            ctime=edge['ctime'] if 'ctime' in edge else default_ctime,
                            errors=edge['errors'] if 'errors' in edge else list(),
                            maskSet=(VideoMaskSetInfo(edge['videomasks']) if (
                                'videomasks' in edge and len(edge['videomasks']) > 0) else None))

    def getSemanticGroups(self,start,end):
        edge = self.getGraph().get_edge(start, end)
        if edge is not None:
            return edge['semanticGroups'] if 'semanticGroups' in edge and edge['semanticGroups'] is not None else []
        return []

    def setSemanticGroups(self,start,end,grps):
        edge = self.getGraph().get_edge(start, end)
        if edge is not None:
            self.getGraph().update_edge(start, end, semanticGroups=grps)
            self.notify((self.start, self.end), 'update_edge')

    def set_validation_properties(self,qaState,qaPerson, qaComment):
        import time
        self.setProjectData('validation', qaState, excludeUpdate=True)
        self.setProjectData('validatedby', qaPerson, excludeUpdate=True)
        self.setProjectData('validationdate', time.strftime("%m/%d/%Y"), excludeUpdate=True)
        self.setProjectData('validationtime', time.strftime("%H:%M:%S"), excludeUpdate=True)
        self.setProjectData('qacomment', qaComment.strip())

    def clear_validation_properties(self):
        import time
        validationProps = {'validation':'no', 'validatedby':'', 'validationtime':'','validationdate':''}
        currentProps = {}
        for p in validationProps:
            currentProps[p] = self.getProjectData(p)
        datetimeval = time.clock()
        if currentProps['validationdate'] is not None and \
            len(currentProps['validationdate']) > 0:
            datetimestr = currentProps['validationdate'] + ' ' + currentProps['validationtime']
            datetimeval = time.strptime(datetimestr, "%m/%d/%Y %H:%M:%S")
        if all(vp in currentProps for vp in validationProps) and \
                        currentProps['validatedby'] != get_username() and \
                        self.getGraph().getLastUpdateTime() > datetimeval:
            for key, val in validationProps.iteritems():
                self.setProjectData(key, val, excludeUpdate=True)


class VideoMaskSetInfo:
    """
    Set of change masks video clips
    """
    columnNames = ['Start', 'End', 'Frames', 'File']
    columnValues = {}

    def __init__(self, maskset):
        self.columnValues = {}
        for i in range(len(maskset)):
            self.columnValues['{:=02d}'.format(i)] = self._convert(maskset[i])

    def _convert(self, item):
        return {'Start': self.tofloat(item['starttime']), 'End': self.tofloat(item['endtime']), 'Frames': item['frames'],
                'File': item['videosegment'] if 'videosegment' in item else ''}

    def tofloat(self,o):
        return o if o is None else float(o)
