# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import collections
import copy
import shutil
import tempfile
import traceback
from threading import Lock
import ffmpeg_api
import graph_rules
import mask_rules
import notifiers
import plugins
import video_tools
from graph_auto_updates import updateJournal
from group_filter import buildFilterOperation,  GroupFilter,  GroupOperationsLoader
from image_graph import createGraph
from image_wrap import ImageWrapper
from maskgen.image_graph import ImageGraph
from maskgen.video_tools import DummyMemory
from support import MaskgenThreadPool, StatusTracker, getPathValuesFunc, getPathValues
from software_loader import Software, getProjectProperties, getRule
from tool_set import *
from validation.core import Validator, ValidationMessage,Severity,removeErrorMessages

def formatStat(val):
    if type(val) == float:
        return "{:5.3f}".format(val)
    return str(val)

prefLoader = MaskGenLoader()

def defaultNotify(edge, message, **kwargs):
    return True

def loadProject(projectFileName, notify=None, username=None, tool=None):
    """
      Given JSON file name, open then the appropriate type of project
      @rtype: ImageProjectModel
    """
    graph = createGraph(projectFileName, tool=tool)
    return ImageProjectModel(projectFileName, graph=graph, notify=notify, username=username, tool=tool)


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


EdgeTuple = collections.namedtuple('EdgeTuple', ['start', 'end', 'edge'])


def createProject(path,
                  notify=None,
                  base=None,
                  name=None,
                  suffixes=[],
                  tool=None,
                  username=None,
                  organization=None,preferences={}):
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
                        filename not in  ['operations.json','project_properties.json']]
        if len(selectionSet) == 0:
            return ImageProjectModel(os.path.join('.', 'Untitled.json'), notify=notify, username=username, tool=tool), True
    else:
        if (path.endswith(".json")) and os.path.exists(path):
            return ImageProjectModel(os.path.abspath(path), notify=notify, username=username, tool=tool), False
        # just a directory
        selectionSet = [filename for filename in os.listdir(path) if filename.endswith(".json")]
    if len(selectionSet) != 0 and base is not None:
        logging.getLogger('maskgen').warning('Cannot add base image/video to an existing project')
        return None
    # JSON file not found and base image not provided
    if len(selectionSet) == 0 and base is None:
        logging.getLogger('maskgen').info(
            'No project found and base image/video not provided; Searching for a base image/video')
        suffixPos = 0
        # look for a viable media file to create the project
        while len(selectionSet) == 0 and suffixPos < len(suffixes):
            suffix = suffixes[suffixPos]
            selectionSet = [filename for filename in os.listdir(path) if filename.lower().endswith(suffix)]
            selectionSet.sort()
            suffixPos += 1
        if len(selectionSet) == 0:
            logging.getLogger('maskgen').warning('Could not find a base image/video')
            return None
        projectFile = selectionSet[0]
    # add base is not None
    elif len(selectionSet) == 0:
        projectFile = os.path.split(base)[1]
    else:
        projectFile = selectionSet[0]
    projectFile = os.path.abspath(os.path.join(path, projectFile))
    if not os.path.exists(projectFile):
        logging.getLogger('maskgen').warning('Base project file ' + projectFile + ' not found')
        return None
    image = None
    existingProject = projectFile.endswith(".json")
    if not existingProject:
        image = projectFile
        if name is None:
            projectFile = os.path.splitext(projectFile)[0] + ".json"
        else:
            projectFile = os.path.abspath(os.path.join(path, name + ".json"))
    model = ImageProjectModel(projectFile, notify=notify, baseImageFileName=image, username=username, tool=tool)
    if organization is not None:
        model.setProjectData('organization', organization)

    if image is not None:
        model.addImagesFromDir(path, baseImageFileName=os.path.split(image)[1], suffixes=suffixes, \
                               sortalg=lambda f: os.stat(os.path.join(path, f)).st_mtime, preferences=preferences)
    return model, not existingProject


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
        return self.diffData.keys()

    def getColumnNames(self, section):
        return ['Operation', 'Old', 'New']

    def toColumns(self, section):
        d = {}
        if len(self.diffData) == 0:
            return d
        if section is None:
            section = self.diffData.keys()[0]
        self._sectionChanges(d, self.diffData[section])
        return d

    def _sectionChanges(self, d, sectionData, prefix=''):
        for k, v in sectionData.iteritems():
            dictKey = str(k)
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
    # generate mask
    generateMask = "all"
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
                 semanticGroups=None,
                 category=None,
                 generateMask="all"):
        self.start = start
        self.end = end
        self.additionalInfo = additionalInfo
        self.maskSet = maskSet
        self.automated = automated if automated else 'no'
        self.errors = errors if errors else list()
        self.operationName = operationName
        self.setArguments(arguments)
        self.semanticGroups = semanticGroups
        if inputMaskName is not None:
            self.setInputMaskName(inputMaskName)
        self.changeMaskName = changeMaskName
        self.username = username if username is not None else ''
        self.ctime = ctime if ctime is not None else datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        self.software = software
        if recordMaskInComposite is not None:
            self.recordMaskInComposite = recordMaskInComposite
        self.category = category
        self.generateMask = generateMask

    def getSemanticGroups(self):
        return [] if self.semanticGroups is None else self.semanticGroups

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

    def setFromOperation(self,op,filetype='image'):
        """
        :param op:
        :return:
        @type op: Operation
        """
        self.category = op.category
        self.generateMask = op.generateMask
        self.recordMaskInComposite = op.recordMaskInComposite(filetype)

class LinkTool:
    """
    LinkTools are used to handle the comparison and analysis of each each in the graph.
    The link tools are organizaed by transitions of
    media type: video->image, video->video, audio->video, etc.
    """

    def __init__(self):
        return

    def getDefaultDonorProcessor(self):
        return "maskgen.masks.donor_rules.donothing_processor"

    def processDonors(self, scModel, start, destination, startIm, startFileName, destIm, destFileName, arguments, invert=False):
        """

        :param scModel:
        :param destination:
        :param startIm:
        :param startFileName:
        :param destIm:
        :param destFileName:
        :param arguments:
        :param invert:
        :return:
        @type scModel: ImageProjectModel
        """
        result = scModel.getCreatingOperation(destination)
        if result is not None:
            return result[1].getDonorProcessor(default_processor=self.getDefaultDonorProcessor())(
                                                          scModel.getGraph(),
                                                          start,
                                                          destination,
                                                          result[0],
                                                          (startIm, startFileName),
                                                          (destIm, destFileName)).create(arguments=arguments,
                                                          invert=invert)

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False, analysis_params={}):
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
        directory = scModel.get_dir()
        opData = scModel.gopLoader.getOperationWithGroups(op)
        if opData is None:
            return
        arguments = dict(arguments)
        arguments['start_node'] = start
        arguments['end_node'] = end
        arguments['sc_model'] = scModel
        for analysisOp in opData.analysisOperations:
            mod_name, func_name = analysisOp.rsplit('.', 1)
            try:
                mod = importlib.import_module(mod_name)
                func = getattr(mod, func_name)
                func(analysis, startIm, destIm, mask=invertMask(mask), linktype=linktype,
                     arguments=arguments,
                     directory=directory)
            except Exception as e:
                logging.getLogger('maskgen').error('Failed to run analysis {}: {} '.format(analysisOp, str(e)))

    def addSubstituteMasks(self, start, destination, scModel, op, arguments={}, filename=''):
        return None

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
            operation = scModel.gopLoader.getOperationWithGroups(edge['op'] if edge is not None else 'NA', fake=True)
            compareFunction = operation.getCompareFunction()
        mask, analysis, error = createMask(im1, im2, invert=False, arguments=arguments,
                                    alternativeFunction=compareFunction)
        if error is not None:
            logging.getLogger('maskgen').warn('Failed mask generation for operation {} between {} and {}'.format(
                edge['op'] if edge is not None else 'NA',
                start,
                end
            ))
        return im1, im2, mask, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False, analysis_params={}):
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
        operation = scModel.gopLoader.getOperationWithGroups(op)
        if op == 'Donor':
            predecessors = scModel.G.predecessors(destination)
            mask = None
            expect_donor_mask = False
            analysis = {}
            if not skipDonorAnalysis:
                errors = list()
                mask = self.processDonors(scModel, start, destination, startIm, startFileName, destIm, destFileName,
                                          consolidate(arguments, analysis_params), invert=invert)
            if mask is None:
                mask = convertToMask(startIm).invert()
                if expect_donor_mask:
                    errors = ["Donor image has insufficient features for SIFT and does not have a predecessor node."]
                analysis = {}
            else:
                mask = startIm.apply_alpha_to_mask(mask)
        else:
            logging.getLogger('maskgen').debug('Create Mask')
            mask, analysis, error = createMask(startIm,
                                        destIm,
                                        invert=invert,
                                        arguments=arguments,
                                        alternativeFunction=operation.getCompareFunction(),
                                        convertFunction=operation.getConvertFunction())
            if error is not None:
                errors.append(error)
                logging.getLogger('maskgen').warn('Failed mask generation for operation {} between {} and {}'.format(
                    op,
                    start,
                    destination
                ))
            logging.getLogger('maskgen').debug('EXIF Compare')
            exifDiff = exif.compareexif(startFileName, destFileName)
            analysis = analysis if analysis is not None else {}
            analysis['exifdiff'] = exifDiff
            logging.getLogger('maskgen').debug('Analysis')
            self._addAnalysis(startIm, destIm, op, analysis, mask, linktype='image.image',
                              arguments=consolidate(arguments, analysis_params),
                              start=start, end=destination, scModel=scModel)
        return mask, analysis, errors


class VideoImageLinkTool(ImageImageLinkTool):
    """
    Supports mask construction and meta-data comparison when linking video to image.
    """

    def __init__(self):
        ImageImageLinkTool.__init__(self)

    def getDefaultDonorProcessor(self):
        return "maskgen.masks.donor_rules.video_without_audio_donor"

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask and the analysis results (a dictionary)
        """
        im1, startFileName = scModel.getImageAndName(start, arguments=arguments)
        im2, destFileName = scModel.getImageAndName(end)
        edge = scModel.G.get_edge(start, end)
        operation = scModel.gopLoader.getOperationWithGroups(edge['op'])
        mask, analysis,error = createMask(im1, im2, invert=False, arguments=arguments,
                                    alternativeFunction=operation.getCompareFunction())
        if error is not None:
            logging.getLogger('maskgen').warn('Failed mask generation for operation {} between {} and {}'.format(
                edge['op'] if edge is not None else 'NA',
                start,
                end
            ))
        return im1, im2, mask, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False, analysis_params={}):
        args = dict(arguments)
        args['skipSnapshot'] = True
        startIm, startFileName = scModel.getImageAndName(start, arguments=args)
        destIm, destFileName = scModel.getImageAndName(destination)
        errors = list()
        operation = scModel.gopLoader.getOperationWithGroups(op)
        mask, analysis = ImageWrapper(
            np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8')), {}
        if op == 'Donor':
            errors = [
                "An video cannot directly donate to an image.  First select a frame using an appropriate operation."]
            analysis = {}
        else:
            mask, analysis,error = createMask(startIm, destIm, invert=invert, arguments=arguments,
                                        alternativeFunction=operation.getCompareFunction())
            if error is not None:
                errors.append(error)
                logging.getLogger('maskgen').warn('Failed mask generation for operation {} between {} and {}'.format(
                    op,
                    start,
                    destination
                ))
            exifDiff = exif.compareexif(startFileName, destFileName)
            analysis = analysis if analysis is not None else {}
            analysis['exifdiff'] = exifDiff
            self._addAnalysis(startIm, destIm, op, analysis, mask, linktype='video.image',
                              arguments=consolidate(arguments, analysis_params),
                              start=start, end=destination, scModel=scModel)
        return mask, analysis, errors

class ZipImageLinkTool(VideoImageLinkTool):
    """
    Supports mask construction and meta-data comparison when linking zip to image.
    """
    def __init__(self):
        VideoImageLinkTool.__init__(self)

    def getDefaultDonorProcessor(self):
        return "maskgen.masks.donor_rules.donothing_stream_processor"

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask set and the meta-data diff results
        """
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(end)
        mask, analysis, errors = self.compareImages(start, end, scModel, 'noOp', skipDonorAnalysis=True,
                                                    arguments=arguments, analysis_params={})
        if 'videomasks' in analysis:
            analysis['videomasks'] = VideoMaskSetInfo(analysis['videomasks'])
        if 'errors' in analysis:
            analysis['errors'] = VideoMaskSetInfo(analysis['errors'])
        return startIm, destIm, mask, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False, analysis_params={}):

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
        mask, analysis = ImageWrapper(
            np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8')), {}
        operation = scModel.gopLoader.getOperationWithGroups(op, fake=True)
        maskSet = video_tools.formMaskDiffForImage(startFileName, destIm,
                                                       os.path.join(scModel.G.dir, start + '_' + destination),
                                                       op,
                                                       startSegment=getMilliSecondsAndFrameCount(arguments[
                                                                                                     'Start Time']) if 'Start Time' in arguments else None,
                                                       endSegment=getMilliSecondsAndFrameCount(arguments[
                                                                                                   'End Time']) if 'End Time' in arguments else None,
                                                       analysis=analysis,
                                                       alternateFunction=operation.getVideoCompareFunction(),
                                                       #alternateFrameFunction=operation.getCompareFunction(),
                                                       arguments=consolidate(arguments, analysis_params))
        # for now, just save the first mask
        if len(maskSet) > 0 and video_tools.get_mask_from_segment( maskSet[0] ) is not None:
            mask = ImageWrapper(video_tools.get_mask_from_segment( maskSet[0] ))
            for item in maskSet:
                video_tools.drop_mask_from_segment(item)
        analysis['masks count'] = len(maskSet)
        analysis['videomasks'] = maskSet
        metaDataDiff = None
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        analysis['shape change'] = sizeDiff(startIm, destIm)
        self._addAnalysis(startIm, destIm, op, analysis, mask, linktype='video.video',
                          arguments=consolidate(arguments, analysis_params),
                          start=start, end=destination, scModel=scModel)
        return mask, analysis, []


class CollectionImageLinkTool(VideoImageLinkTool):
    """
    Supports mask construction and meta-data comparison when linking zip to image.
    """
    def __init__(self):
        VideoImageLinkTool.__init__(self)

    def getDefaultDonorProcessor(self):
        return "maskgen.masks.donor_rules.donothing_stream_processor"

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask set and the meta-data diff results
        """
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(end)
        mask = np.ones((destIm.size[0],destIm.size[1]),dtype=np.uint8)*255
        return startIm, destIm, ImageWrapper(mask), {}

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False, analysis_params={}):

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
        startIm, destIm, mask, analysis = self.compare(start, destination, scModel)
        return mask, analysis, []

class VideoVideoLinkTool(LinkTool):
    """
     Supports mask construction and meta-data comparison when linking video to video.
     """

    def __init__(self):
        LinkTool.__init__(self)

    def getDefaultDonorProcessor(self):
        return "maskgen.masks.donor_rules.video_without_audio_donor"

    def compare(self, start, end, scModel, arguments={}):
        """ Compare the 'start' image node to the image node with the name in the  'destination' parameter.
            Return both images, the mask set and the meta-data diff results
        """
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(end)
        mask, analysis, errors = self.compareImages(start, end, scModel, 'noOp',
                                                    arguments=arguments, analysis_params={})
        if 'metadatadiff' in analysis:
            analysis['metadatadiff'] = VideoMetaDiff(analysis['metadatadiff'])
        if 'videomasks' in analysis:
            analysis['videomasks'] = VideoMaskSetInfo(analysis['videomasks'])
        if 'errors' in analysis:
            analysis['errors'] = VideoMaskSetInfo(analysis['errors'])
        return startIm, destIm, mask, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False, analysis_params={}):

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
        mask, analysis = ImageWrapper(
            np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8')), {}
        operation = scModel.gopLoader.getOperationWithGroups(op, fake=True)
        if op != 'Donor' and operation.generateMask not in ['audio', 'all']:
            maskSet = video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator(startFileName))
            if maskSet is None:
                maskSet = list()
            errors = list()
        elif op == 'Donor' and not skipDonorAnalysis:
            errors = list()
            maskSet = self.processDonors(scModel, start, destination, startIm, startFileName, destIm, destFileName,
                                          consolidate(arguments, analysis_params), invert=invert)
        else:
            maskSet, errors = video_tools.formMaskDiff(startFileName, destFileName,
                                                       os.path.join(scModel.G.dir, start + '_' + destination),
                                                       op,
                                                       startSegment=getMilliSecondsAndFrameCount(arguments[
                                                                                                     'Start Time']) if 'Start Time' in arguments else None,
                                                       endSegment=getMilliSecondsAndFrameCount(arguments[
                                                                                                   'End Time']) if 'End Time' in arguments else None,
                                                       analysis=analysis,
                                                       alternateFunction=operation.getVideoCompareFunction(),
                                                       #alternateFrameFunction=operation.getCompareFunction(),
                                                       arguments=consolidate(arguments, analysis_params))
        mask = None
        for item in maskSet:
            if video_tools.get_mask_from_segment(item) is not None:
                mask = ImageWrapper(video_tools.get_mask_from_segment(item))
                video_tools.drop_mask_from_segment(item)
        if mask is None:
            mask = ImageWrapper(np.ones(startIm.image_array.shape[0:2], dtype='uint8')*255)
        analysis['masks count'] = len(maskSet)
        analysis['videomasks'] = maskSet
        metaDataDiff = video_tools.form_meta_data_diff(startFileName, destFileName)
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        analysis['shape change'] = sizeDiff(startIm, destIm)
        self._addAnalysis(startIm, destIm, op, analysis, mask, linktype='video.video',
                          arguments=consolidate(arguments, analysis_params),
                          start=start, end=destination, scModel=scModel)
        return mask, analysis, errors

    def addSubstituteMasks(self,start, destination, scModel, op, arguments={}, filename=''):
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        startSegment = getMilliSecondsAndFrameCount(arguments[
                                                        'Start Time']) if 'Start Time' in arguments else None
        endSegment = getMilliSecondsAndFrameCount(arguments[
                                                      'End Time']) if 'End Time' in arguments else None
        subs = video_tools.formMaskForSource(startFileName,
                                             filename,
                                             start + '_' + destination + '_substitute',
                                             startTimeandFrame=startSegment,
                                             stopTimeandFrame=endSegment
                                             )
        #if subs is not None:
        #    analysis = {}
        #    startIm, startFileName = scModel.getImageAndName(start)
        #    destIm, destFileName = scModel.getImageAndName(destination)
        #    maskSet, errors = video_tools.formMaskDiff(startFileName, destFileName,
        #                                               os.path.join(scModel.G.dir, start + '_' + destination + '_cmp'),
        #                                               op,
        #                                               startSegment=startSegment,
        #                                               endSegment=endSegment,
        #                                               analysis=analysis,
        #                                               alternateFunction=video_tools.maskCompare,
        #                                               arguments=arguments)
        # how best to compare
        return subs


class AudioVideoLinkTool(VideoVideoLinkTool):
    """
     Supports mask construction and meta-data comparison when linking audio to video.
     """

    def __init__(self):
        VideoVideoLinkTool.__init__(self)

    def getDefaultDonorProcessor(self):
        return "maskgen.masks.donor_rules.all_audio_processor"

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
                      skipDonorAnalysis=False, analysis_params={}):
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
        analysis = dict()
        analysis['masks count'] = 0
        analysis['videomasks'] = list()
        metaDataDiff = video_tools.form_meta_data_diff(startFileName, destFileName, frames=False, media_types=['audio'])
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        operation = scModel.gopLoader.getOperationWithGroups(op, fake=True)
        errors = []
        if op == 'Donor':
            errors = list()
            maskSet = self.processDonors(scModel, start, destination, startIm, startFileName, destIm, destFileName,
                                      consolidate(arguments, analysis_params), invert=invert)
        elif op != 'Donor' and operation.generateMask in ['audio','all']:
            maskSet, errors = video_tools.formMaskDiff(startFileName, destFileName,
                                                       os.path.join(scModel.G.dir, start + '_' + destination),
                                                       op,
                                                       startSegment=getMilliSecondsAndFrameCount(arguments[
                                                                                                     'Start Time']) if 'Start Time' in arguments else None,
                                                       endSegment=getMilliSecondsAndFrameCount(arguments[
                                                                                                   'End Time']) if 'End Time' in arguments else None,
                                                       analysis=analysis,
                                                       alternateFunction=operation.getVideoCompareFunction(),
                                                       arguments=consolidate(arguments, analysis_params))
        else:
            maskSet = video_tools.getMaskSetForEntireVideo(
                video_tools.FileMetaDataLocator(startFileName), media_types=['audio'])
            if maskSet is None:
                maskSet = list()
                errors = list()

        analysis['masks count'] = len(maskSet)
        analysis['videomasks'] = maskSet
        self._addAnalysis(startIm, destIm, op, analysis, None, linktype='audio.audio',
                          arguments=consolidate(arguments, analysis_params),
                          start=start, end=destination, scModel=scModel)

        return mask, analysis, errors


class AudioAudioLinkTool(AudioVideoLinkTool):
    """
     Supports mask construction and meta-data comparison when linking audio to audio.
     """

    def __init__(self):
        AudioVideoLinkTool.__init__(self)


class VideoAudioLinkTool(LinkTool):
    """
     Supports mask construction and meta-data comparison when linking video to audio.
     """

    def __init__(self):
        LinkTool.__init__(self)

    def getDefaultDonorProcessor(self):
        return "maskgen.masks.donor_rules.all_audio_processor"

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
        analysis = dict()
        analysis['masks count'] = 0
        analysis['videomasks'] = list()
        metaDataDiff = video_tools.form_meta_data_diff(startFileName, destFileName, frames=False, media_types=['audio'])
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        self._addAnalysis(startIm, destIm, op, analysis, None, linktype='video.audio',
                          arguments=consolidate(arguments, analysis_params),
                          start=start, end=destination, scModel=scModel)
        return mask, analysis, list()


class ImageVideoLinkTool(VideoVideoLinkTool):
    """
     Supports mask construction and meta-data comparison when linking images to images.
     """

    def __init__(self):
        VideoVideoLinkTool.__init__(self)

    def getDefaultDonorProcessor(self):
        return "maskgen.masks.donor_rules.alpha_stream_processor"

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False, analysis_params={}):
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        mask = ImageWrapper(
            np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8'))
        if op == 'Donor':
            mask = self.processDonors(scModel, start, destination, startIm, startFileName, destIm, destFileName,
                                      consolidate(arguments, analysis_params), invert=invert)
            if mask is None:
                mask = startIm.to_mask().invert()
        return mask, {}, ()


class ImageZipAudioLinkTool(VideoAudioLinkTool):
    """
     Supports mask construction and meta-data comparison when linking images to images.
     """

    def __init__(self):
        VideoAudioLinkTool.__init__(self)

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False, analysis_params={}):
        startIm, startFileName = scModel.getImageAndName(start)
        #destIm, destFileName = scModel.getImageAndName(destination)
        mask, analysis = ImageWrapper(
            np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8')), {}
        return mask, analysis, []


class ImageZipVideoLinkTool(VideoVideoLinkTool):
    """
     Supports mask construction and meta-data comparison when linking images to images.
     """

    def __init__(self):
        VideoVideoLinkTool.__init__(self)

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False, analysis_params={}):
        startIm, startFileName = scModel.getImageAndName(start)
        #destIm, destFileName = scModel.getImageAndName(destination)
        mask, analysis = ImageWrapper(
            np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8')), {}
        return mask, analysis, []


class AddTool:
    def getAdditionalMetaData(self, media):
        return {}


class VideoAddTool(AddTool):
    def getAdditionalMetaData(self, media):
        parent = {}
        meta, frames = ffmpeg_api.get_meta_from_video(media, show_streams=True, with_frames=True, frame_limit=30, frame_meta=['pkt_duration_time'],media_types=['video'])
        indices = ffmpeg_api.get_stream_indices_of_type(meta, 'video')
        if indices:
            if_vfr = ffmpeg_api.is_vfr(meta[indices[0]], frames=frames[indices[0]])
        else:
            if_vfr = False
        meta, _ = ffmpeg_api.get_meta_from_video(media, show_streams=True,
                                                      frame_meta=['pkt_duration_time'])
        parent['media'] = meta
        width = 0
        height = 0
        rotation = 0
        for item in meta:
            if 'width' in item:
                width = int(item['width'])
            if 'height' in item:
                height = int(item['height'])
            if 'rotation' in item:
                rotation = int(item['rotation'])
        parent['shape'] = (width, height)
        parent['rotation'] = rotation
        meta[indices[0]]['is_vfr'] = if_vfr
        # redundant but requested by NIST
        parent['is_vfr'] = if_vfr
        return parent

class ZipAddTool(AddTool):
    def getAdditionalMetaData(self, media):
        from zipfile import ZipFile
        meta = {}
        with ZipFile(media, 'r') as myzip:
            names = myzip.namelist()
            meta['length'] = len(names)
        return meta

class OtherAddTool(AddTool):
    def getAdditionalMetaData(self, media):
        return {}

addTools = {
             'video': VideoAddTool(),
             'zip':ZipAddTool(),
             'collection': OtherAddTool(),
             'audio': OtherAddTool(),
             'image': OtherAddTool()
            }
linkTools = {'image.image': ImageImageLinkTool(), 'video.video': VideoVideoLinkTool(),
             'image.video': ImageVideoLinkTool(), 'video.image': VideoImageLinkTool(),
             'video.audio': VideoAudioLinkTool(), 'audio.video': AudioVideoLinkTool(),
             'audio.audio': AudioAudioLinkTool(), 'zip.video':ImageZipVideoLinkTool(),
             'collection.image': CollectionImageLinkTool(),
             'zip.image':   ZipImageLinkTool(),   'zip.audio': ImageZipAudioLinkTool()}


def true_notify(object, message, **kwargs):
    return True

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

    def __init__(self, projectFileName, graph=None, notify=None,
                 baseImageFileName=None, username=None,tool=None):
        self.probeMaskMemory = DummyMemory(None)
        if notify is not None:
            self.notify = notifiers.NotifyDelegate(
                [notify, notifiers.QaNotifier(self), notifiers.ValidationNotifier(total_errors=None)])
        else:
            self.notify = notifiers.NotifyDelegate([true_notify])
        if graph is not None:
            graph.arg_checker_callback = self.__scan_args_callback
        # Group Operations are tied to models since
        # group operations are created by a local instance and stored in the graph model
        # when used.

        self.gopLoader = GroupOperationsLoader()
        self.username = username if username is not None else get_username()
        self._setup(projectFileName, graph=graph, baseImageFileName=baseImageFileName,tool=tool)


    def set_notifier(self, notifier):
        self.notify = notifiers.NotifyDelegate(
            [notifier, notifiers.QaNotifier(self), notifiers.ValidationNotifier(total_errors=None)])

    def get_dir(self):
        return self.G.dir

    def getGroupOperationLoader(self):
        return self.gopLoader

    def addImagesFromDir(self, dir, baseImageFileName=None, xpos=100, ypos=30, suffixes=list(),
                         sortalg=lambda s: s.lower(),preferences={}):
        """
          Bulk add all images from a given directory into the project.
          Position the images in a grid, separated by 50 vertically with a maximum height of 520.
          Images are imported in lexicographic order, first importing JPG, then PNG and finally TIFF.
          If baseImageFileName, the name of an image node, is provided, then that node is selected
          upong completion of the operation.  Otherwise, the last not imported is selected"
        """
        initialYpos = ypos
        totalSet = []
        suffixes = set(suffixes)
        for suffix in suffixes:
            suffix_lower = suffix.lower()
            totalSet.extend([filename for filename in os.listdir(dir) if
                             filename.lower().endswith(suffix_lower ) and \
                             not filename.endswith('_mask' + suffix) and \
                             not filename.endswith('_proxy' + suffix)])
        totalSet = sorted(totalSet, key=sortalg)
        added = []
        for filename in totalSet:
            try:
                pathname = os.path.abspath(os.path.join(dir, filename))
                additional = self.getAddTool(pathname).getAdditionalMetaData(pathname)
                additional.update(preferences)
                nname = self.G.add_node(pathname, xpos=xpos, ypos=ypos, nodetype='base', **additional)
                added.append(nname)
                ypos += 50
                if ypos == 450:
                    ypos = initialYpos
                    xpos += 50
                if filename == baseImageFileName:
                    self.start = nname
                    self.end = None
            except Exception as ex:
                logging.getLogger('maskgen').warn('Failed to add media file {}'.format(filename))
        self.notify(added, 'add')


    def addImage(self, pathname, cgi=False, prnu=False, **kwargs):
        maxx = 50
        max_node = None
        for node_id in self.G.get_nodes():
            node = self.G.get_node(node_id)
            if 'xpos' in node and int(node['xpos']) > maxx:
                maxx = int(node['xpos'])
                max_node = node
        maxy = max_node['ypos'] + 50 if max_node is not None else 50
        additional = self.getAddTool(pathname).getAdditionalMetaData(pathname)
        additional.update(kwargs)
        nname = self.G.add_node(pathname, nodetype='base',
                                cgi='yes' if cgi else 'no',
                                xpos=maxx,
                                ypos=maxy,
                                prnu='yes' if prnu else 'no',
                                **additional)
        self.start = nname
        self.end = None
        self.notify([self.start], 'add')
        return nname

    def getEdgesBySemanticGroup(self):
        """
        :return: association of semantics groups to edge id tuples (start,end)
        @rtype: dict of list of tuple
        """
        result = {}
        for edgeid in self.getGraph().get_edges():
            for grp in self.getSemanticGroups(edgeid[0], edgeid[1]):
                if grp not in result:
                    result[grp] = [edgeid]
                else:
                    result[grp].append(edgeid)
        return result

    def add_to_edge(self, **items):
        self.G.update_edge(self.start, self.end, **items)
        self.notify((self.start, self.end), 'update_edge')

    def update_node(self, node_properties):
        deleteImage(self.getStartImageFile())
        self.G.update_node(self.start, **node_properties)

    def update_edge(self, mod):
        """
        :param mod:
        :return:
        @type mod: Modification
        """
        op = self.gopLoader.getOperationWithGroups(mod.operationName,fake=True)
        mod_old = self.getModificationForEdge(self.start, self.end)

        trigger_update = False
        for k,v in mod.arguments.iteritems():
            if (k not in mod_old.arguments or mod_old.arguments[k] != v) and \
                k in op.getTriggerUpdateArguments():
                trigger_update = True
        for k in mod_old.arguments:
            if k not in mod.arguments and \
                k in op.getTriggerUpdateArguments():
                trigger_update = True

        self.G.update_edge(self.start, self.end,
                           op=mod.operationName,
                           description=mod.additionalInfo,
                           arguments={k: v for k, v in mod.arguments.iteritems() if k != 'inputmaskname'},
                           recordMaskInComposite=mod.recordMaskInComposite,
                           semanticGroups=mod.semanticGroups,
                           editable='no' if (
                                                mod.software is not None and mod.software.internal) or mod.operationName == 'Donor' else 'yes',
                           softwareName=('' if mod.software is None else mod.software.name),
                           softwareVersion=('' if mod.software is None else mod.software.version),
                           inputmaskname=mod.inputMaskName)
        self._save_group(mod.operationName)

        if trigger_update:
            self.reproduceMask(force=False)
        else:
            self.notify((self.start, self.end), 'update_edge')

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
        videodiff = VideoMetaDiff(e['metadatadiff']) if getValue(e,'metadatadiff',None) is not None else None
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
            baseSet = self._findBaseNodesAndPaths(edge[0], excludeDonor=True)
            for base in baseSet:
                if (edge, base) not in results:
                    results.append((edge, base[0], base[1]))
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

    def getEdges(self, endNode,excludeDonor=True):
        """

        :param endNode: (identifier)
        :return: tuple (start, end, edge map) for all edges ending in endNode
        """
        return self._findEdgesWithCycleDetection(endNode, excludeDonor=excludeDonor, visitSet=list())

    def getNodeNames(self):
        return self.G.get_nodes()

    def getCurrentNode(self):
        return self.G.get_node(self.start)

    def isEditableEdge(self, start, end):
        e = self.G.get_edge(start, end)
        return 'editable' not in e or e['editable'] == 'yes'

    def findChild(self, parent, child):
        for suc in self.G.successors(parent):
            if suc == child or self.findChild(suc, child):
                return True
        return False

    def compress(self, all=False,force=False):
        if all:
            return [self._compress(node) for node in self.G.get_nodes()]
        else:
            return self._compress(self.start, force=force)

    def _compress(self, start, force=False):
        defaults = {'compressor.video': 'maskgen.video_tools.x264',
                    'compressor.audio': None,
                    'compressor.image': None}
        node = self.G.get_node(start)

        ftype = self.getNodeFileType(start)
        # cannot finish the action since the edge analysis was skipped
        for skipped_edge in self.G.getDataItem('skipped_edges', []):
            if skipped_edge['start'] == start and not force:
                return
        if (len(self.G.successors(start)) == 0 or len(self.G.predecessors(start)) == 0) and not force:
            return

        props = {'remove_video': False}
        #for pred in self.G.predecessors(start):
        #    edge = self.G.get_edge(pred, start)
        #    op = getOperationWithGroups(edge['op'], fake=True)
        #    if op.category == 'Audio':
        #        props['remove_video'] = True

        compressor = prefLoader.get_key('compressor.' + ftype,
                                        default_value=defaults['compressor.' + ftype])
        if 'compressed' in node:
            return

        func = getRule(compressor)
        newfile = None
        if func is not None:
            newfilename = func(os.path.join(self.get_dir(), node['file']), **props)
            if newfilename is not None:
                newfile = os.path.split(newfilename)[1]
                node['file'] = newfile
                node['compressed'] = compressor
        return newfile

    def connect(self, destination, mod=Modification('Donor', '',category='Donor'), invert=False, sendNotifications=True,
                skipDonorAnalysis=False):
        """ Given a image node name, connect the new node to the end of the currently selected node.
             Create the mask, inverting the mask if requested.
             Send a notification to the register caller if requested.
             Return an error message on failure, otherwise return None
        """
        if self.start is None:
            return ValidationMessage(Severity.ERROR,
                                     self.start,
                                     self.end,
                                     Message="Node node selected",
                                     Module=''), False
        elif not self.G.has_node(destination):
            return ValidationMessage(Severity.ERROR,
                                     self.start,
                                     self.end,
                                     Message="Canvas out of state from model. Node Missing.",
                                     Module=''), False
        elif self.findChild(destination, self.start):
            return ValidationMessage(Severity.ERROR,
                                     self.start,
                                     self.end,
                                     Message="Cannot connect to ancestor node",
                                     Module=''), False
        else:
            for successor in self.G.successors(self.start):
                if successor == destination:
                    return ValidationMessage(Severity.ERROR,
                                                    self.start,
                                                    self.end,
                                                    Message="Cannot connect to the same node twice",
                                                    Module=''), False

            return self._connectNextImage(destination,
                                          mod,
                                          invert=invert,
                                          sendNotifications=sendNotifications,
                                          skipDonorAnalysis=skipDonorAnalysis)

    def getPredecessorNode(self):
        if self.end is None:
            for pred in self.G.predecessors(self.start):
                edge = self.G.get_edge(pred, self.start)
                if edge['op'] != 'Donor':
                    return pred
        return self.start

    def getBaseNode(self, node):
        for pred in self.G.predecessors(node):
            edge = self.G.get_edge(pred, node)
            if edge['op'] != 'Donor':
                return self.getBaseNode(pred)
        return node

    def getCreatingOperation(self, destination):
        """
        :return: operation for the manipulation that created this destination and the start node
        @rtype: (str,Operation)
        """
        predecessors = self.G.predecessors(destination)
        for pred in predecessors:
            pred_edge = self.G.get_edge(pred, destination)
            edge_op = self.gopLoader.getOperationWithGroups(pred_edge['op'])
            if edge_op is not None and pred_edge['op'] != 'Donor':
                return pred, edge_op

    def getDonorAndBaseImage(self):
        """
         Get the donor image and associated baseImage for the selected node.
        """
        nodeName = self.start if self.end is None else self.end
        # verify the node is a leaf node
        endPointTuples = self.getDonorAndBaseNodeTuples()
        for x in endPointTuples:
            if nodeName == x[0][1]:
                baseImage, _ = self.G.get_image(x[1])
                donors = self.constructDonors()
                for donortuple in donors:
                    if donortuple.base == x[1]:
                        if donortuple.media_type == 'video':
                            return video_tools.getSingleFrameFromMask(donortuple.mask_wrapper), baseImage
                        elif donortuple.media_type == 'audio':
                            return None, None
                        else:
                            return donortuple.mask_wrapper, baseImage
        return None, None

    def getTransformedMask(self):
        """
        :return: list of CompositeImage
        """
        composite_generator = mask_rules.prepareComposite((self.start, self.end),self.G, self.gopLoader, self.probeMaskMemory)
        return composite_generator.constructComposites(checkEmptyMask=False)


    def executeFinalNodeRules(self):
        terminalNodes = [node for node in self.G.get_nodes() if
                         len(self.G.successors(node)) == 0 and len(self.G.predecessors(node)) > 0]
        for node in terminalNodes:
            graph_rules.setFinalNodeProperties(self, node)

    def constructDonors(self):

        """
          Construct donor images
          Find all valid base node, leaf node tuples
          :return computed donors in the form of tuples
          (image node id donated to, base image node, ImageWrapper mask, filename)
          @rtype list of DonorImage
        """
        self._executeSkippedComparisons()
        for edge_id in self.G.get_edges():
            if self.start is not None and self.start != edge_id[1]:
                continue
            composite_generator = mask_rules.prepareComposite(edge_id, self.G, self.gopLoader, self.probeMaskMemory)
            return composite_generator.constructDonors(saveImage=False)
        return []

    def invertInputMask(self):
        """
        Temporary: Add missing input masks
        :return:
        """
        if self.start is not None and self.end is not None:
            start_im = self.startImage()
            edge = self.G.get_edge(self.start, self.end)
            if edge is not None:
                maskname= getValue(edge,'inputmaskname')
                if maskname is not None:
                    mask = openImageMaskFile(self.get_dir(),maskname)
                    if mask is not None:
                        expected_shape = start_im.image_array.shape[0:2]
                        if expected_shape != mask.shape:
                            mask = cv2.resize(mask,tuple(reversed(expected_shape)))
                        mask = ImageWrapper(mask)
                        mask = mask.invert()
                        mask.save(os.path.join(self.get_dir(),maskname))

    def fixInputMasks(self):
        """
        Temporary: Add missing input masks
        :return:
        """
        for edge_id in self.G.get_edges():
            edge = self.G.get_edge(edge_id[0], edge_id[1])
            if graph_rules.missing_donor_inputmask(edge, self.G.dir):
                startimage, name = self.G.get_image(edge_id[0])
                finalimage, fname = self.G.get_image(edge_id[1])
                mask = self.G.get_edge_image(edge_id[0], edge_id[1], 'maskname')
                inputmaskname = os.path.splitext(name)[0]+ '_inputmask.png'
                ImageWrapper(composeCloneMask(mask, startimage, finalimage)).save(inputmaskname)
                #                if 'arguments' not in edge:
                #                    edge['arguments'] = {}
                edge['inputmaskname'] = os.path.split(inputmaskname)[1]
                #               edge['arguments']['inputmaskname'] = os.path.split(inputmaskname)[1]
                self.G.setDataItem('autopastecloneinputmask', 'yes')

    def renametobase(self):
        """
        Rename the project to match the name of the base image
        :return:
        """
        for nodeid in self.G.get_nodes():
            node = self.G.get_node(nodeid)
            if 'nodetype' in node and node['nodetype'] == 'base':
                pos = node['file'].find('.')
                self.getGraph().set_name(node['file'][:pos] if pos > 0 else node['file'])
                break

    def addNextImage(self, pathname, invert=False, mod=Modification('', ''), sendNotifications=True, position=(50, 50),
                     skipRules=False, edge_parameters={}, node_parameters={}):
        """ Given a image file name and  PIL Image, add the image to the project, copying into the project directory if necessary.
             Connect the new image node to the end of the currently selected edge.  A node is selected, not an edge, then connect
             to the currently selected node.  Create the mask, inverting the mask if requested.
             Send a notification to the register caller if requested.
             Return a list of validation messages on failure, otherwise return None
        """
        if (self.end is not None):
            self.start = self.end
        params = dict(node_parameters)
        params['xpos'] = position[0]
        params['ypos'] = position[1]
        params['nodetype'] = 'base'
        for k, v in self.getAddTool(pathname).getAdditionalMetaData(pathname).iteritems():
            params[k] = v
        destination = self.G.add_node(pathname, seriesname=self.getSeriesName(), **params)
        self.notify([destination],'add')
        analysis_params = dict({ k:v for k,v in edge_parameters.iteritems() if v is not None})
        msgs, status = self._connectNextImage(destination, mod, invert=invert, sendNotifications=sendNotifications,
                                             skipRules=skipRules, analysis_params=analysis_params)
        return msgs, status

    def getLinkType(self, start, end):
        return self.getNodeFileType(start) + '.' + self.getNodeFileType(end)

    def getLinkTool(self, start, end):
        """

        :param start:
        :param end:
        :return:
        @rtype: LinkTool
        """
        return linkTools[self.getLinkType(start, end)]

    def mergeProject(self, project):
        """
        Merge projects.  Does not support updating edges or nodes.
        Instead, it only adds new edges and nodes.
        Should be used with caution.
        :param project:
        :return:
        @type project: ImageProjectModel
        """
        # link from their node id to my node id
        merge_point = dict()
        myfiles = dict()
        for nodeid in self.getGraph().get_nodes():
            mynode = self.getGraph().get_node(nodeid)
            myfiles[mynode['file']] = (nodeid, md5_of_file(os.path.join(self.G.dir, mynode['file']),
                                                           raiseError=False))
        for nodeid in project.getGraph().get_nodes():
            theirnode = project.getGraph().get_node(nodeid)
            theirfilemd5 = md5_of_file(os.path.join(project.get_dir(), theirnode['file']),
                                       raiseError=False)
            if theirnode['file'] in myfiles:
                if myfiles[theirnode['file']][1] != theirfilemd5:
                    logging.getLogger('maskgen').warn(
                        'file {} is in both projects but MD5 is different'.format(theirnode['file']))
                else:
                    merge_point[nodeid] = myfiles[theirnode['file']][0]
        if len(merge_point) == 0:
            return 'No merge points found'
        for nodeid in project.getGraph().get_nodes():
            theirnode = project.getGraph().get_node(nodeid)
            if nodeid not in merge_point:
                merge_point[nodeid] = self.getGraph().add_node(os.path.join(project.get_dir(), theirnode['file']),
                                                               **theirnode)
        for start, end in project.getGraph().get_edges():
            mystart = merge_point[start]
            myend = merge_point[end]
            edge = self.getGraph().get_edge(mystart, myend)
            if edge is None:
                self.getGraph().copy_edge(mystart,
                                          myend,
                                          dir=project.get_dir(),
                                          edge=project.getGraph().get_edge(start, end))

    def getAddTool(self, media):
        """"
        :param media:
        :return:
        @rtype : AddTool
        """
        ft = fileType(media)
        if ft.startswith('zip'):
            ft = 'zip'
        return addTools[ft]

    def hasSkippedEdges(self):
        return len(self.G.getDataItem('skipped_edges', [])) > 0


    def _executeQueue(self,q,results,tracker):
        from Queue import Empty
        """
        :param q:
        :return:
        @type q : Queue
        @type failures: Queue
        """
        while not q.empty():
            try:
                edge_data = q.get_nowait()
                if edge_data is None:
                    break
                logging.getLogger('maskgen').info('Recomputing mask for edge {} to {} using operation {}'.format(
                    edge_data['start'],
                    edge_data['end'],
                    edge_data['opName']
                ))
                tracker.next('{}->{}'.format(edge_data['start'], edge_data['end']))
                if self.getGraph().has_node(edge_data['start']) and self.getGraph().has_node(edge_data['end']) and \
                    self.getGraph().has_edge(edge_data['start'],edge_data['end']):
                    mask, analysis, errors = self.getLinkTool(edge_data['start'], edge_data['end']).compareImages(
                        edge_data['start'],
                        edge_data['end'],
                        self,
                        edge_data['opName'],
                        arguments=edge_data['arguments'],
                        skipDonorAnalysis=edge_data['skipDonorAnalysis'],
                        invert=edge_data['invert'],
                        analysis_params=edge_data['analysis_params'])
                    maskname = shortenName(edge_data['start'] + '_' + edge_data['end'], '_mask.png', identifier=self.G.nextId())
                    self.G.update_mask(edge_data['start'], edge_data['end'], mask=mask, maskname=maskname, errors=errors,
                                       **consolidate(analysis, edge_data['analysis_params']))
                else:
                    errors = []
                results.put(((edge_data['start'], edge_data['end']), True, errors))
                #with self.G.lock:
                #    results.put(((edge_data['start'], edge_data['end']), True, errors))
                #    self.G.setDataItem('skipped_edges', [skip_data for skip_data in self.G.getDataItem('skipped_edges', []) if
                #                                          (skip_data['start'], skip_data['end']) != (edge_data['start'], edge_data['end'])])
            except Empty:
                break
            except Exception as e:
                if edge_data is not None:
                    logging.getLogger('maskgen').error('Failure to generate mask for edge {} to {} using operation {}: {}'.format(
                        edge_data['start'],
                        edge_data['end'],
                        edge_data['opName'],
                        str(e)
                    ))
                    results.put(((edge_data['start'], edge_data['end']),False, [str(e)]))
        return

    def _executeSkippedComparisons(self,status_cb=None):
        from Queue import Queue
        from threading import Thread
        allErrors = []
        completed = []
        q = Queue()
        status = Queue()
        results = Queue()
        skipped_edges = self.G.getDataItem('skipped_edges', [])
        if len(skipped_edges) == 0:
            return
        tracker_cb = status_cb
        tracker_cb = lambda x : status.put(x) if tracker_cb is not None and int(skipped_threads) >= 2 else None
        tracker = StatusTracker(module_name='Mask Generator',
                                amount=len(skipped_edges),
                                status_cb=tracker_cb)
        for edge_data in skipped_edges:
            q.put(edge_data)
        skipped_threads = prefLoader.get_key('skipped_threads', 2)
        logging.getLogger('maskgen').info('Recomputing {} masks with {} threads'.format(q.qsize(), skipped_threads))
        threads = list()
        try:
            if int(skipped_threads) < 2:
                self._executeQueue(q, results, tracker)
            else:
                for i in range(int(skipped_threads)):
                    t = Thread(target=self._executeQueue, name='skipped_edges' + str(i), args=(q,results,tracker))
                    threads.append(t)
                    t.start()
                if status_cb is not None:
                    while not q.empty():
                        try:
                            message = status.get(timeout=5)
                            if message is not None:
                                status_cb(message)
                        except:
                            continue
                for thread in threads:
                    thread.join()
            while not results.empty():
                result = results.get_nowait()
                allErrors.extend(result[2])
                if result[1]:
                    completed.append(result[0])
        finally:
            tracker.complete()
        self.G.setDataItem('skipped_edges',[edge_data for edge_data in skipped_edges if (edge_data['start'], edge_data['end']) not in completed])
        msg = os.linesep.join(allErrors).strip()
        return msg if len(msg) > 0 else None

    def _compareImages(self, start, destination, opName, invert=False, arguments={}, skipDonorAnalysis=False,
                       analysis_params=dict(),
                       force=False):
        if prefLoader.get_key('skip_compare') and not force:
            self.G.setDataItem('skipped_edges', self.G.getDataItem('skipped_edges', list()) + [{"start": start,
                                                                                                "end": destination,
                                                                                                "analysis_params": analysis_params,
                                                                                                "arguments": arguments,
                                                                                                "opName": opName,
                                                                                                "skipDonorAnalysis": skipDonorAnalysis,
                                                                                                "invert": invert
                                                                                                }])
            return None, {}, []
        try:
            for k, v in self.gopLoader.getOperationWithGroups(opName).compareparameters.iteritems():
                arguments[k] = v
        except:
            pass
        return self.getLinkTool(start, destination).compareImages(start, destination, self, opName,
                                                                       arguments=arguments,
                                                                       skipDonorAnalysis=skipDonorAnalysis,
                                                                       invert=invert,
                                                                       analysis_params=analysis_params)

    def reproduceMask(self, skipDonorAnalysis=False,edge_id=None, analysis_params=dict(), argument_params=dict(),
                      force=True):
        """

        :param skipDonorAnalysis:
        :param edge_id:
        :param analysis_params:
        :param argument_params:
        :param force: If True, then force mask creation do not skip.
        :return:
        """
        mask_edge_id = (self.start, self.end) if edge_id is None else edge_id
        edge = self.G.get_edge(mask_edge_id[0],mask_edge_id[1])
        arguments = dict(edge['arguments']) if 'arguments' in edge else dict()
        if len(argument_params) > 0:
            arguments = argument_params
        if 'inputmaskname' in edge and edge['inputmaskname'] is not None:
            arguments['inputmaskname'] = edge['inputmaskname']
        mask, analysis, errors = self._compareImages(mask_edge_id[0], mask_edge_id[1], edge['op'],
                                                     arguments=arguments,
                                                     skipDonorAnalysis=skipDonorAnalysis,
                                                     analysis_params=analysis_params,
                                                     force=force)
        analysis_params['arguments'] = arguments
        maskname = shortenName(mask_edge_id[0] + '_' + mask_edge_id[1], '_mask.png', identifier=self.G.nextId())
        self.G.update_mask(mask_edge_id[0], mask_edge_id[1], mask=mask, maskname=maskname, errors=errors, **consolidate(analysis, analysis_params))
        if len(errors) == 0:
            self.G.setDataItem('skipped_edges', [skip_data for skip_data in self.G.getDataItem('skipped_edges', []) if
                                                  (skip_data['start'], skip_data['end']) != mask_edge_id])
        self.notify(mask_edge_id, 'update_edge')
        return errors

    def _connectNextImage(self, destination, mod, invert=False, sendNotifications=True, skipRules=False,
                          skipDonorAnalysis=False,
                          analysis_params={}):
        """

        :param destination:
        :param mod:
        :param invert:
        :param sendNotifications:
        :param skipRules:
        :param skipDonorAnalysis:
        :param analysis_params:
        :return: Error message and success or failure
        @rtype: (str, bool)
        """
        try:
            maskname = shortenName(self.start + '_' + destination, '_mask.png', identifier=self.G.nextId())
            if mod.inputMaskName is not None:
                mod.arguments['inputmaskname'] = mod.inputMaskName
            mask, analysis, errors = self._compareImages(self.start, destination, mod.operationName,
                                                         invert=invert, arguments=mod.arguments,
                                                         skipDonorAnalysis=skipDonorAnalysis,
                                                         analysis_params=analysis_params)
            self.end = destination
            if errors:
                mod.errors = errors
            for k, v in analysis_params.iteritems():
                if k not in analysis:
                    analysis[k] = v
            if 'recordMaskInComposite' in mod.arguments:
                mod.recordMaskInComposite = mod.arguments.pop('recordMaskInComposite')
                mod.recordMaskInComposite = getValue(analysis,'global','yes') == 'no' | mod.recordMaskInComposite

            self.__addEdge(self.start, self.end, mask, maskname, mod, analysis)

            if sendNotifications:
                self.notify((self.start, destination), 'connect')
            logging.getLogger('maskgen').debug('Validation')
            edgeErrors = [] if skipRules else self.validator.run_edge_rules(self.G, self.start, destination, isolated=True)
            edgeErrors = edgeErrors if len(edgeErrors) > 0 else None
            self.labelNodes(self.start)
            self.labelNodes(destination)
            return edgeErrors, True
        except Exception as e:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            logging.getLogger('maskgen').error(' '.join(traceback.format_exception(exc_type,exc_value,exc_traceback)))
            return [ValidationMessage(Severity.ERROR,
                                      self.start,
                                      destination,
                                      'Exception (' + str(e) + ')',
                                      'Change Mask',
                                      None)], False

    def __scan_args_callback(self, opName, arguments):
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
            self.__addEdgeFilePaths(self.gopLoader.getOperationWithGroups(opName, fake=True))

    def __addEdgeFilePaths(self, op):
        for k, v in op.mandatoryparameters.iteritems():
            if k == 'inputmaskname':
                continue
            if v['type'].startswith('fileset:') or v['type'].startswith('file:'):
                self.G.addEdgeFilePath('arguments.' + k, '')
        for k, v in op.optionalparameters.iteritems():
            if k == 'inputmaskname':
                continue
            if v['type'].startswith('fileset:') or v['type'].startswith('file:'):
                self.G.addEdgeFilePath('arguments.' + k, '')

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
                        semanticGroups=mod.semanticGroups,
                        errors=mod.errors,
                        **additionalParameters)
        self._save_group(mod.operationName)

    def _save_group(self, operation_name):
        op = self.gopLoader.getOperationWithGroups(operation_name, fake=True)
        if op.groupedOperations is not None and len(op.groupedOperations) > 0:
            groups = self.G.getDataItem('groups')
            if groups is None:
                groups = dict()
            groups[operation_name] = op.groupedOperations
            self.G.setDataItem('groups', groups, excludeUpdate=True)

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


    def nodesToCSV(self, filename, additionalpaths=list(), nodeFilter=None):
        """
        Create a CSV containing all the nodes of the graph.
        By default, the first columns are project name, edge start node id,
        edge end node id, and edge operation.
        :param filename:
        :param additionalpaths: paths that describe nested keys within the edge dictionary identifying
        those keys' value to be placed as columns in the CSV
        :param nodeFilter: a function that accepts the node dictionary and returns True if
        the edge is to be included in the CSV file.  If the edgeFilter is None or not provided,
        all edges are included in the CSV file
        :return: None
        @type filename: str
        @type edgeFilter: func
        """
        import csv
        csv.register_dialect('unixpwd', delimiter=',', quoting=csv.QUOTE_MINIMAL)
        with open(filename, "ab") as fp:
            fp_writer = csv.writer(fp)
            for node_id in self.G.get_nodes():
                node = self.G.get_node(node_id)
                if nodeFilter is not None and not nodeFilter(node):
                    continue
                row = [self.G.get_name(), node_id, node['nodetype'], self.G.getNodeFileType(node_id), self.G.get_filename(node_id)]
                for path in additionalpaths:
                    if type(path) == 'str':
                        values = getPathValues(node, path)
                    else:
                        values = path(node)
                    if len(values) > 0:
                        row.append(values[0])
                    else:
                        row.append('')
                fp_writer.writerow(row)

    def toCSV(self, filename, additionalpaths=list(), edgeFilter=None):
        """
        Create a CSV containing all the edges of the graph.
        By default, the first columns are project name, edge start node id,
        edge end node id, and edge operation.
        :param filename:
        :param additionalpaths: paths that describe nested keys within the edge dictionary identifying
        those keys' value to be placed as columns in the CSV
        :param edgeFilter: a function that accepts the edge dictionary and returns True if
        the edge is to be included in the CSV file.  If the edgeFilter is None or not provided,
        all edges are included in the CSV file
        :return: None
        @type filename: str
        @type edgeFilter: func
        """
        import csv
        csv.register_dialect('unixpwd', delimiter=',', quoting=csv.QUOTE_MINIMAL)
        with open(filename, "ab") as fp:
            fp_writer = csv.writer(fp)
            for edge_id in self.G.get_edges():
                edge = self.G.get_edge(edge_id[0], edge_id[1])
                if edgeFilter is not None and not edgeFilter(edge):
                    continue
                row = [self.G.get_name(), edge_id[0], edge_id[1], edge['op']]
                baseNodes = self._findBaseNodes(edge_id[0])
                for path in additionalpaths:
                    if path == 'basenode':
                        row.append(baseNodes[0])
                        continue
                    elif type(path) == 'str':
                        values = getPathValues(edge, path)
                    else:
                        values = path(edge, edge_id=edge_id, op=self.gopLoader.getOperationWithGroups(edge['op']))
                    if len(values) > 0:
                        row.append(values[0])
                    else:
                        row.append('')
                fp_writer.writerow(row)

    def getName(self):
        return self.G.get_name()

    def operationImageName(self):
        return self.end if self.end is not None else self.start

    def getFileName(self, nodeid):
            return self.G.get_node(nodeid)['file']

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
        self.notify((s, e), 'undo')

    def select(self, edge):
        if self.getGraph().get_node(edge[0]) == None:
            return False
        self.start = edge[0]
        self.end = edge[1]
        return True

    def _openProject(self, projectFileName, projecttype, username=None,tool=None):
        return createGraph(projectFileName,
                           projecttype=projecttype,
                           arg_checker_callback=self.__scan_args_callback,
                           edgeFilePaths={'inputmaskname': 'inputmaskownership',
                                          'selectmasks.mask': '',
                                          'videomasks.videosegment': '',
                                          'substitute subsitute': '',
                                          'substitute videomasks.videosegment': ''},
                           nodeFilePaths={'donors.*': ''},
                           username=username if username is not None else self.username,
                           tool=tool)

    def _autocorrect(self):
        if not updateJournal(self):
            logging.getLogger('maskgen').error('Cannot auto update journal')

    def _setup(self, projectFileName, graph=None, baseImageFileName=None,tool=None):
        projecttype = None if baseImageFileName is None else fileType(baseImageFileName)
        self.G = self._openProject(projectFileName, projecttype, username=self.username,tool=tool) if graph is None else graph
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
        # inject loaded groups into the group operations manager
        for group, ops in self.G.getDataItem('groups', default_value={}).iteritems():
            self.gopLoader.injectGroup(group, ops)
        self.validator = Validator(prefLoader, self.gopLoader)

    def getStartType(self):
        return self.G.getNodeFileType(self.start) if self.start is not None else 'image'

    def getEndType(self):
        return self.G.getNodeFileType(self.end) if self.end is not None else 'image'

    def getNodeFileType(self, nodeid):
        return self.G.getNodeFileType(nodeid)

    def saveas(self, pathname):
        with self.lock:
            self.clear_validation_properties()
            self.assignColors()
            self.G.saveas(pathname)

    def save(self):
        with self.lock:
            self.clear_validation_properties()
            self.assignColors()
            self.setProjectSummary()
            self.G.save()

    def getEdgeItem(self, name, default=None):
        edge = self.G.get_edge(self.start, self.end)
        return edge[name] if name in edge else default

    def getDescriptionForPredecessor(self, node):
        for pred in self.G.predecessors(node):
            edge = self.G.get_edge(pred, node)
            if edge['op'] != 'Donor':
                return self.getModificationForEdge(pred, node)
        return None

    def getDescription(self):
        if self.start is None or self.end is None:
            return None
        return self.getModificationForEdge(self.start, self.end)

    def findPaths(self,node, condition):
        """
        Return a list of a tuple.  The first item is the full path in reverse order
        from final node to current node.  The second item is a boolean indicating if the path
        meets the condition.
        :param node:
        :param condition:
        :return:
        @rtype: list of (list,bool)
        """
        successors = self.G.successors(node)
        if len(successors) == 0:
            return [([node],False)]
        else:
            paths=[]
            for successsor in successors:
                for path in self.findPaths(successsor, condition):
                    paths.append(path)
            paths = [(path[0]+[node], condition(node, path[0][-1]) | path[1]) for path in paths]
            return paths

    def findEdgePaths(self,node):
        """
        Return a list of a tuple.  The first item is the full path in reverse order
        from final node to current node.  The second item is a boolean indicating if the path
        meets the condition.
        :param node:
        :param condition:
        :return:
        @rtype: list of (list,bool)
        """
        successors = self.G.successors(node)
        if len(successors) == 0:
            return [[]]
        else:
            paths=[]
            for successsor in successors:
                for path in self.findEdgePaths(successsor):
                    paths.append(path)
            paths = [path+[(node, successsor)] for path in paths]
            return paths

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
            return ImageWrapper(np.zeros((250, 250, 4)).astype('uint8')),''
        return self.G.get_image(name, metadata=arguments)

    def getStartImageFile(self):
        return os.path.join(self.G.dir, self.G.get_node(self.start)['file'])

    def getProxy(self):
        return getValue(self.G.get_node(self.start),'proxyfile')

    def setProxy(self, filename):
        if filename is None:
            if self.getProxy() is not None:
                self.G.get_node(self.start).pop('proxyfile')
            return
        self.G.update_node(self.start,proxyfile=os.path.basename(filename))

    def getNextImageFile(self):
        return os.path.join(self.G.dir, self.G.get_node(self.end)['file'])

    def startImage(self):
        return self.getImage(self.start)

    def nextImage(self):
        if self.end is None:
            dim = (250, 250) if self.start is None else self.getImage(self.start).size
            return ImageWrapper(np.zeros((dim[1], dim[0])).astype('uint8'))
        return self.getImage(self.end)

    def updateSelectMask(self, selectMasks):
        if self.end is None:
            return
        sms = []
        for k, v in selectMasks.iteritems():
            if v is not None:
                sms.append({'mask': v[0], 'node': k})
        self.G.update_edge(self.start, self.end, selectmasks=sms)

    def getSelectMasks(self):
        """
        A selectMask is a mask the is used in composite mask production, overriding the default link mask
        """
        if self.end is None:
            return {}
        edge = self.G.get_edge(self.start, self.end)
        terminals = self._findTerminalNodes(self.end, excludeDonor=True,
                                            includeOps=['Recapture', 'TransformWarp', 'TransformContentAwareScale',
                                                        'TransformDistort', 'TransformSkew', 'TransformSeamCarving'])
        images = edge['selectmasks'] if 'selectmasks' in edge  else []
        sms = {}
        for image in images:
            if image['node'] in terminals:
                sms[image['node']] = (
                image['mask'], openImageFile(os.path.join(self.get_dir(), image['mask']), isMask=False))
        for terminal in terminals:
            if terminal not in sms:
                sms[terminal] = None
        return sms

    def maskImageName(self):
        if self.end is None:
            return ''
        edge = self.G.get_edge(self.start, self.end)
        return edge['maskname'] if 'maskname' in edge else ''

    def maskImageFileTime(self):
        if self.end is None:
            return 0
        return self.G.get_edge_image_file_time(self.start, self.end, 'maskname')

    def maskImage(self, inputmask=False):
        mask = self.G.get_edge_image(self.start, self.end, 'maskname')
        if self.end is None or mask is None:
            dim = (250, 250) if self.start is None else self.getImage(self.start).size
            return ImageWrapper(np.zeros((dim[1], dim[0])).astype('uint8'))
        return mask

    def maskStats(self):
        if self.end is None:
            return ''
        edge = self.G.get_edge(self.start, self.end)
        if edge is None:
            return ''
        stat_names = ['ssim', 'psnr', 'local psnr', 'local ssim', 'shape change', 'masks count', 'change size category',
                      'change size ratio']
        return '  '.join([key + ': ' + formatStat(value) for key, value in edge.items() if key in stat_names])

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

    def remove(self, children=False):
        import copy
        s = self.start
        e = self.end
        list_to_process= []

        if children:
            list_to_process = copy.copy(self.G.successors(self.end if self.end is not None else self.start))

        def remove_children(children):
            for child in children:
                remove_children(self.G.successors(child))
                self.G.remove(child)
                print (child)
                self.notify((child, None), 'remove')

        remove_children(list_to_process)

        """ Remove the selected node or edge """
        if (self.start is not None and self.end is not None):
            if children:
                self.G.remove(self.end, None)
                self.labelNodes(self.start)
            else:
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

        self.notify((s, e), 'remove')

    def getProjectData(self, item, default_value=None):
        return self.G.getDataItem(item, default_value=default_value)

    def setProjectData(self, item, value, excludeUpdate=False):
        """
        :param item:
        :param value:
        :param excludeUpdate: True if the update does not change the update time stamp on the journal
        :return:
        """
        self.notify((item,value),'meta')
        self.G.setDataItem(item, value, excludeUpdate=excludeUpdate)

    def getVersion(self):
        """ Return the graph/software versio n"""
        return self.G.getVersion()

    def isFrozen(self):
        return self.G.isFrozen()

    def getGraph(self):
        """
        :return: underlying graph
        @rtype: ImageGraph
        """
        return self.G

    def validate(self, external=False, status_cb=None):
        """ Return the list of errors from all validation rules on the graph.
        @rtype: list of ValidationMessage
        """

        notifier = self.notify.get_notifier_by_type(notifiers.ValidationNotifier)
        if notifier is not None and not notifier.total_errors == None:
            return notifier.total_errors

        self._executeSkippedComparisons(status_cb=status_cb)
        logging.getLogger('maskgen').info('Begin validation for {}'.format(self.getName()))
        total_errors = self.validator.run_graph_suite(self.getGraph(), external=external, status_cb=status_cb)
        for prop in getProjectProperties():
            if prop.mandatory:
                item = self.G.getDataItem(prop.name)
                if item is None or len(item.strip()) < 3:
                    total_errors.append(
                        ValidationMessage(Severity.ERROR,
                                          '',
                                          '',
                                          'Project property ' + prop.description + ' is empty or invalid',
                                          'Mandatory Property',
                                          None))
        if notifier is not None:
            self.notify.replace(notifiers.ValidationNotifier(total_errors))

        return total_errors

    def assignColors(self):
        level = 1
        edgeMap = dict()
        foundColors = 0
        colors = []
        edges = 0
        for edge_id in self.G.get_edges():
            edge = self.G.get_edge(edge_id[0], edge_id[1])
            if edge['op'] == 'Donor':
                continue
            edges += 1
            if 'linkcolor' in edge:
                foundColors += 1
                colors.append(edge['linkcolor'])
        if edges == foundColors and len(set(colors)) ==foundColors:
            return
        for edge_id in self.G.get_edges():
            edge = self.G.get_edge(edge_id[0], edge_id[1])
            if edge['op'] == 'Donor':
                continue
            edgeMap[edge_id] = (level, None)
            level = level + 1
        redistribute_intensity(edgeMap)
        for k, v in edgeMap.iteritems():
            self.G.get_edge(k[0], k[1])['linkcolor'] = str(list(v[1])).replace('[', '').replace(']', '').replace(
                ',', '')
        return edgeMap

    def __assignLabel(self, node, label):
        prior = self.G.get_node(node)['nodetype'] if 'nodetype' in self.G.get_node(node) else None
        if prior != label:
            self.G.update_node(node, nodetype=label)
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
                logging.getLogger('maskgen').info('Inspecting {}  for rename'.format(nodeData['file']))
                suffix = os.path.splitext(nodeData['file'])[1].lower()
                file_path_name = os.path.join(self.G.dir, nodeData['file'])
                try:
                    new_file_name = md5_of_file(os.path.join(self.G.dir, nodeData['file'])) + suffix
                    fullname = os.path.join(self.G.dir, new_file_name)
                except:
                    logging.getLogger('maskgen').error(
                        'Missing file or invalid permission: {} '.format(nodeData['file']))
                    continue
                if not os.path.exists(fullname):
                    try:
                        os.rename(file_path_name, fullname)
                        renamed.append(node)
                        logging.getLogger('maskgen').info('Renamed {} to {} '.format(nodeData['file'], new_file_name))
                        self.G.update_node(node, file=new_file_name)
                    except Exception as e:
                        try:
                            logging.getLogger('maskgen').error(
                                ('Failure to rename file {} : {}.  Trying copy').format(file_path_name, str(e)))
                            shutil.copy2(file_path_name, fullname)
                            logging.getLogger('maskgen').info(
                                'Renamed {} to {} '.format(nodeData['file'], new_file_name))
                            self.G.update_node(node, file=new_file_name)
                        except:
                            continue
                else:
                    logging.getLogger('maskgen').warning('New name ' + new_file_name + ' already exists')
                    self.G.update_node(node, file=new_file_name)
        self.save()
        return renamed

    def labelNodes(self, destination):
        baseNodes = []
        donorNodes = []
        terminalNodes = []
        candidateBaseDonorNodes = self._findBaseNodes(destination, excludeDonor=False)
        for baseCandidate in candidateBaseDonorNodes:
            foundTerminalNodes = self._findTerminalNodes(baseCandidate, excludeDonor=True)
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

    def baseNodes(self):
        bases = []
        for name in self.getNodeNames():
            node = self.G.get_node(name)
            if node['nodetype'] == 'base':
                bases.append(name)
        return bases

    def _findTerminalNodes(self, node, excludeDonor=False, includeOps=None):
        terminalsWithOps = self._findTerminalNodesWithCycleDetection(node, visitSet=list(), excludeDonor=excludeDonor)
        return [terminalWithOps[0] for terminalWithOps in terminalsWithOps if
                includeOps is None or len(set(includeOps).intersection(terminalWithOps[1])) > 0]

    def _findTerminalNodesWithCycleDetection(self, node, visitSet=list(), excludeDonor=False):
        succs = self.G.successors(node)
        if len(succs) == 0:
            return [(node, [])]
        res = list()
        for succ in succs:
            if succ in visitSet:
                continue
            op = self.G.get_edge(node, succ)['op']
            if op == 'Donor' and excludeDonor:
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
                res.append(EdgeTuple(start=pred, end=node, edge=edge))
            res.extend(self._findEdgesWithCycleDetection(pred, excludeDonor=excludeDonor,
                                                         visitSet=visitSet) if isNotDonor else list())
        return res

    def _findBaseNodes(self, node, excludeDonor=True):
        return [item[0] for item in mask_rules.findBaseNodesWithCycleDetection(self.G, node, excludeDonor=excludeDonor)]

    def _findBaseNodesAndPaths(self, node, excludeDonor=True):
        return [(item[0], item[2]) for item in mask_rules.findBaseNodesWithCycleDetection(self.G,node, excludeDonor=excludeDonor)]

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
        @type grp GroupFilter
        @type software Software
        """
        import copy
        pairs_composite = []
        resultmsgs = []
        kwargs_copy = copy.copy(kwargs)
        for filter in grp.filters:
            msg, pairs = self.mediaFromPlugin(filter, software=software,
                                              **kwargs_copy)
            if msg is not None:
                resultmsgs.extend(msg)
            if len(pairs) == 0:
                break
            mod = self.getModificationForEdge(self.start,self.end)
            for key,value in mod.arguments.iteritems():
                if key not in kwargs_copy or not self.getGraph().isEdgeFilePath('arguments.' + key):
                    kwargs_copy[key] = value
            pairs_composite.extend(pairs)
        return resultmsgs, pairs_composite

    def substitutesAllowed(self):
        allowed = False
        modification = self.getDescription()
        if modification is not None:
            allowed = getValue(modification.arguments, 'videoinputmaskname', '')
        return 'disabled' if not allowed else 'normal'

    def hasSubstituteMasks(self):
        edge = self.getGraph().get_edge(self.start, self.end)
        subs = getValue(edge, 'substitute videomasks', [])
        return len(subs) > 0

    def removeSubstituteMasks(self):
        if self.hasSubstituteMasks():
            edge = self.getGraph().get_edge(self.start, self.end)
            edge.pop('substitute videomasks')

    def addSubstituteMasks(self, filename):
        edge = self.getGraph().get_edge(self.start, self.end)
        subs = self.getLinkTool(self.start, self.end).addSubstituteMasks(self.start,
                                                                  self.end,
                                                                  self,
                                                                  edge['op'],
                                                                  arguments=getValue(edge,'arguments',{}),
                                                                  filename=filename)
        if subs is not None:
            for sub in subs:
                sub.pop('mask')
            edge['substitute videomasks'] = subs
            self.getGraph().addEdgeFilePath('substitute videomasks.videosegment','')
            self.notify((self.start, self.end), 'update_edge')
        return subs is not None

    def mediaFromPlugin(self, filter, software=None, passthru=False, description=None, **kwargs):
        """
          Use a plugin to create a new media item and link.
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
          @rtype: list of (ValidationMessage, list of (str,str))
        """

        im, filename = self.currentImage()
        filetype= fileType(filename)
        op = plugins.getOperation(filter)
        suffix = os.path.splitext(filename)[1].lower()
        preferred = plugins.getPreferredSuffix(filter,filetype=filetype)
        if type(preferred) == dict:
            preferred = preferred[filetype]
        fullOp = buildFilterOperation(op)
        resolved, donors, graph_args, suffix_override, donorargs = self._resolvePluginValues(kwargs, fullOp)
        if suffix_override is not None:
            suffix = suffix_override
        elif preferred is not None:
            if preferred in donors:
                suffix = os.path.splitext(resolved[preferred])[1].lower()
            else:
                suffix = preferred
        target = os.path.join(tempfile.gettempdir(), self.G.new_name(self.start, suffix=suffix))
        shutil.copy2(filename, target)
        try:
            msg = None
            self.__addEdgeFilePaths(fullOp)
            try:
                if getValue(kwargs,'$$-pass-thru') or passthru:
                    extra_args, warning_message = None,None
                else:
                    extra_args, warning_message = plugins.callPlugin(filter, im, filename, target, **resolved)
            except Exception as e:
                msg = str(e)
                exc_type, exc_value, exc_traceback = sys.exc_info()
                traceback.print_tb(exc_traceback, limit=10, file=sys.stderr)
                logging.getLogger('maskgen').error(
                    'Plugin {} failed with {} given node {} for arguments {}'.format(filter, str(e),self.start, str(resolved)))
                extra_args = None
            if msg is not None:
                return self._pluginError(filter, msg), []
            if extra_args is not None and 'rename_target' in extra_args:
                filename = extra_args.pop('rename_target')
                newtarget = os.path.join(os.path.split(target)[0], os.path.split(filename)[1])
                shutil.copy2(target, newtarget)
                target = newtarget
            if extra_args is not None and 'override_target' in extra_args:
                filename = extra_args.pop('override_target')
                target = os.path.join(os.path.split(target)[0], os.path.split(filename)[1])
            if extra_args is not None and 'output_files' in extra_args:
                file_params = extra_args.pop('output_files')
                for name, value in file_params.iteritems():
                    extra_args[name] = value
                    self.G.addEdgeFilePath('arguments.' + name, '')
            opInfo = self.gopLoader.getOperationWithGroups(op['name'], fake=True)
            description = Modification(op['name'], filter + ':' + op['description'] if description is None else description,
                                       category=opInfo.category,
                                       generateMask=opInfo.generateMask,
                                       semanticGroups=graph_args['semanticGroups'] if 'semanticGroups' in graph_args else [],
                                       recordMaskInComposite=opInfo.recordMaskInComposite(filetype) if
                                       'recordMaskInComposite' not in kwargs else kwargs['recordMaskInComposite'])
            sendNotifications = kwargs['sendNotifications'] if 'sendNotifications' in kwargs else True
            skipRules = kwargs['skipRules'] if 'skipRules' in kwargs else False
            if software is None:
                software = Software(op['software'], op['version'], internal=True)
            if 'recordInCompositeMask' in kwargs:
                description.setRecordMaskInComposite(kwargs['recordInCompositeMask'])
            experiment_id = kwargs['experiment_id'] if 'experiment_id' in kwargs else None
            description.setArguments(
                {k: v for k, v in graph_args.iteritems() if k not in ['semanticGroups','sendNotifications', 'skipRules', 'experiment_id']})
            if extra_args is not None and type(extra_args) == type({}):
                for k, v in extra_args.iteritems():
                    if k not in kwargs or v is not None:
                        description.arguments[k] = v
            description.setSoftware(software)
            description.setAutomated('yes')
            edge_parameters = {'plugin_name': filter,'experiment_id': experiment_id}
            if  'global operation' in kwargs:
                edge_parameters['global operation'] = kwargs['global operation']
            results2, status = self.addNextImage(target,
                                                 mod=description,
                                                 sendNotifications=sendNotifications,
                                             skipRules=skipRules,
                                             position=self._getCurrentPosition((75 if len(donors) > 0 else 0, 75)),
                                             edge_parameters=edge_parameters,
                                             node_parameters={
                                                 'experiment_id': experiment_id} if experiment_id is not None else {})
            pairs = list()

            errors = []
            if warning_message is not None:
                errors.append(ValidationMessage(Severity.WARNING,
                                                self.start,
                                                self.start,
                                                warning_message,
                                                'Plugin {}'.format(filter),
                                                None))
            if results2 is not None:
                errors.extend(results2)
        finally:
            os.remove(target)
        if status:
            pairs.append((self.start, self.end))
            if sendNotifications:
                self.notify((self.start,  self.end), 'connect')

            for donor in donors:
                _end = self.end
                _start = self.start
                self.selectImage(kwargs[donor])
                mod = Modification('Donor', '',category='Donor',automated='yes',arguments=donorargs)
                self.connect(_end,mod=mod)
                pairs.append((kwargs[donor], _end))
                self.select((_start, _end))
                # donor error message is removed.  This annoys me (rwgdrummer).
                # really need to classify rules and skip certain categories
                errors = removeErrorMessages(errors,lambda msg: 'donor' in msg)

        return errors, pairs

    def _resolvePluginValues(self, args, operation):
        parameters = {}
        stripped_args = {}
        donors = []
        arguments = copy.copy(operation.mandatoryparameters)
        arguments.update(operation.optionalparameters)
        for k, v in args.iteritems():
            if k in arguments or k in {'sendNotifications',
                                       'override_suffix',
                                       'skipRules',
                                       'semanticGroups',
                                       'experiment_id',
                                       'recordInCompositeMask',
                                       'donorargs',
                                       'index'}:
                parameters[k] = v
                # if arguments[k]['type'] != 'donor':
                stripped_args[k] = v
        for k, v in args.iteritems():
            if k in arguments and \
                            arguments[k]['type'] == 'donor':
                parameters[k] = self.getImageAndName(v)[1]
                if parameters[k] is None:
                    if os.path.exists(v):
                        parameters[k] = v
                    else:
                        logging.getLogger('maskgen').error('Donor {} not found'.format(v))
                donors.append(k)
        for arg, info in arguments.iteritems():
            if arg not in parameters and 'defaultvalue' in info and \
                            info['defaultvalue'] is not None:
                parameters[arg] = info['defaultvalue']
        return parameters, donors, stripped_args, \
               args['override_suffix'] if 'override_suffix' in args else None, \
               getValue(args,'donorargs',{})

    def _pluginError(self, filter, msg):
        if msg is not None and len(msg) > 0:
            return [ValidationMessage(Severity.ERROR,
                                      self.start,
                                      self.start,
                                      'Plugin ' + filter + ': ' + msg,
                                      'Plugin {}'.format(filter),
                                      None)]
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
        return [self.getModificationForEdge(edge[0], edge[1]) for edge in
                self.G.get_edges()]

    def openImage(self, nfile):
        im = None
        if nfile is not None and nfile != '':
            im = self.G.openImage(nfile)
        return nfile, im

    def findEdgesByOperationName(self, opName):
        return [edge for edge in [self.G.get_edge(edge[0], edge[1]) for edge in self.G.get_edges()]
                if edge['op'] == opName]

    def getPathExtender(self):
        from services.probes import CompositeExtender
        """
        :return: Extend the composite or donor through current operation
        """
        #nodes = self._findTerminalNodes(self.start, excludeDonor=True)
        #if len(nodes) > 0:
        return CompositeExtender(self)
        #else:
        #    return DonorExtender(self)

    def export(self, location, include=[], redacted=[],notifier=None):
        with self.lock:
            self.clear_validation_properties()
            self.compress(all=True)
            path, errors = self.G.create_archive(location, include=include, redacted=redacted, notifier=notifier)
            return path, [ValidationMessage(Severity.ERROR,error[0],error[1],error[2],'Export',None) for error in errors]

    def export_path(self, location, redacted=[]):
        """
        :param location:
        :param redacted: a list of registered file paths to exclude @see ImageGraph.addEdgeFilePath
        :return:
        """
        if self.end is None and self.start is not None:
            self.G.create_path_archive(location, self.start, redacted=redacted)
        elif self.end is not None:
            self.G.create_path_archive(location, self.end, redacted=redacted)

    def _getCurrentPosition(self, augment):
        if self.start is None:
            return (50, 50)
        startNode = self.G.get_node(self.start)
        return ((startNode['xpos'] if startNode.has_key('xpos') else 50) + augment[0],
                (startNode['ypos'] if startNode.has_key('ypos') else 50) + augment[1])


    def getModificationForEdge(self, start, end):
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
        edge = self.G.get_edge(start, end)
        if edge is None:
            return None
        default_ctime = end_node['ctime'] if 'ctime' in end_node else None
        op = self.gopLoader.getOperationWithGroups(edge['op'], warning=True,fake=True)
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
                            username=edge['username'] if 'username' in edge else '',
                            ctime=edge['ctime'] if 'ctime' in edge else default_ctime,
                            errors=edge['errors'] if 'errors' in edge else list(),
                            maskSet=(VideoMaskSetInfo(edge['videomasks']) if (
                                'videomasks' in edge and len(edge['videomasks']) > 0) else None),
                            category=op.category,
                            generateMask=op.generateMask)

    def getSemanticGroups(self, start, end):
        edge = self.getGraph().get_edge(start, end)
        if edge is not None:
            return edge['semanticGroups'] if 'semanticGroups' in edge and edge['semanticGroups'] is not None else []
        return []

    def setSemanticGroups(self, start, end, grps):
        edge = self.getGraph().get_edge(start, end)
        if edge is not None:
            self.getGraph().update_edge(start, end, semanticGroups=grps)
            self.notify((self.start, self.end), 'update_edge')

    def setProjectSummary(self):
        groups = []
        for edgeTuple in self.getGraph().get_edges():
            edge = self.getGraph().get_edge(edgeTuple[0], edgeTuple[1])
            semantic_groups = getValue(edge,'semanticGroups',[])
            for group in semantic_groups:
                if group not in groups:
                    groups.append(group)
        self.setProjectData('semanticgroups', groups)

    def set_validation_properties(self,  qaState, qaPerson, qaComment, qaData):
        import qa_logic
        qa_logic.ValidationData(self,qaState,qaPerson,None,qaComment,qaData)

    def clear_validation_properties(self):
        import qa_logic
        logic = qa_logic.ValidationData(self)
        logic.clearProperties()

    def set_probe_mask_memory(self, memory):
        self.probeMaskMemory = memory

    """Not sure if this will ever see any use"""
    def get_probe_mask_memory(self):
        return self.probeMaskMemory

class VideoMaskSetInfo:
    """
    Set of change masks video clips
    """

    columnNames = ['Start', 'End', 'Frames', 'File']
    func = [float,float,int,str]
    columnKeys = ['starttime', 'endtime', 'frames', 'File']
    columnValues = {}

    def __init__(self, maskset):
        self.maskset = maskset
        self.columnValues = {'{:=02d}'.format(i):self._convert(maskset[i]) for i in range(len(maskset))}

    def _convert(self, item):
        return {'Start': self.tofloat(video_tools.get_start_time_from_segment(item)),
                'End': self.tofloat(video_tools.get_end_time_from_segment(item)),
                'Frames': video_tools.get_frames_from_segment(item),
                'File': video_tools.get_file_from_segment(item,default_value='')}


    def update(self, item_number, column, value):
        video_tools.update_segment(self.maskset[item_number],
                       **{self.columnKeys[column] : self.func[column](value)})
        video_tools.update_segment(self.maskset[item_number],rate= \
                                            (video_tools.get_end_time_from_segment(self.maskset[item_number]) -
                                             video_tools.get_start_time_from_segment(self.maskset[item_number])/
                                             video_tools.get_frames_from_segment(self.maskset[item_number])))

    def tofloat(self, o):
        return o if o is None else float(o)


