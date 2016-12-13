from image_graph import createGraph, current_version, getPathValues
import shutil
import exif
import os
import numpy as np
from tool_set import *
import video_tools
from maskgen import software_loader
from software_loader import Software
import tempfile
import plugins
import graph_rules
from image_wrap import ImageWrapper
from PIL import Image
from group_filter import getOperationWithGroups
from time import gmtime, strftime
from graph_auto_updates import updateJournal


def formatStat(val):
   if type(val) == float:
      return "{:5.3f}".format(val)
   return str(val)

def imageProjectModelFactory(name, **kwargs):
    return ImageProjectModel(name, **kwargs)

def loadProject(projectFileName):
    """
      Given JSON file name, open then the appropriate type of project
    """
    graph = createGraph(projectFileName)
    return ImageProjectModel(projectFileName, graph=graph)

def consolidate(dict1, dict2):
    d = dict(dict1)
    d.update(dict2)
    return d

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

    if (path.endswith(".json")):
        return projectModelFactory(os.path.abspath(path), notify=notify), False
    selectionSet = [filename for filename in os.listdir(path) if filename.endswith(".json")]
    if len(selectionSet) != 0 and base is not None:
        print 'Cannot add base image/video to an existing project'
        return None
    if len(selectionSet) == 0 and base is None:
        print 'No project found and base image/video not provided; Searching for a base image/video'
        suffixPos = 0
        while len(selectionSet) == 0 and suffixPos < len(suffixes):
            suffix = suffixes[suffixPos]
            selectionSet = [filename for filename in os.listdir(path) if filename.lower().endswith(suffix)]
            selectionSet.sort()
            suffixPos += 1
        projectFile = selectionSet[0] if len(selectionSet) > 0 else None
        if projectFile is None:
            print 'Could not find a base image/video'
            return None
    # add base is not None
    elif len(selectionSet) == 0:
        projectFile = os.path.split(base)[1]
    else:
        projectFile = selectionSet[0]
    projectFile = os.path.abspath(os.path.join(path, projectFile))
    if not os.path.exists(projectFile):
        print 'Base project file ' + projectFile + ' not found'
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
    targetChangeSizeInPixels = 0
    donorBaseNodeId = None
    donorMaskImage = None
    donorMaskFileName = None

    """
    @type edgeId: tuple
    @type targetBaseNodeId: str
    @type targetMaskFileName: str
    @type targetMaskImage: ImageWrapper
    @type targetChangeSizeInPixels: int
    @type finalNodeId: str
    @type donorBaseNodeId: str
    @type donorMaskImage : ImageWrapper
    @type donorMaskFileName: str

    The target is the node edgeId's target node (edgeId[1])--the image after the manipulation.
    The targetBaseNodeId is the id of the base node that supplies the base image for the target.
    """


    def __init__(self,edgeId,finalNodeId,targetBaseNodeId,targetMaskImage,targetMaskFileName,targetChangeSizeInPixels,donorBaseNodeId,donorMaskImage,donorMaskFileName):
        self.edgeId = edgeId
        self.finalNodeId = finalNodeId
        self.targetBaseNodeId = targetBaseNodeId
        self.targetMaskImage = targetMaskImage
        self.targetMaskFileName = targetMaskFileName
        self.donorBaseNodeId = donorBaseNodeId
        self.donorMaskImage = donorMaskImage
        self.donorMaskFileName = donorMaskFileName
        self.targetChangeSizeInPixels = targetChangeSizeInPixels

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


class IntObject:
      value = 0

      def __init__(self):
          pass

      def increment(self):
          self.value+=1
          return self.value

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
    # represents the composite selection mask, if different from the link mask
    selectMaskName = None
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

    def __init__(self, operationName, additionalInfo,
                 start='',
                 end='',
                 arguments={},
                 recordMaskInComposite=None,
                 changeMaskName=None,
                 selectMaskName=None,
                 inputMaskName=None,
                 software=None,
                 maskSet=None,
                 automated=None,
                 username=None,
                 ctime=None,
                 errors=list()):
        self.start = start
        self.end = end
        self.additionalInfo = additionalInfo
        self.maskSet = maskSet
        self.automated = automated if automated else 'no'
        self.errors = errors if errors else list()
        self.setOperationName(operationName)
        self.setArguments(arguments)
        if inputMaskName is not None:
            self.setInputMaskName(inputMaskName)
        self.changeMaskName = changeMaskName
        self.selectMaskName = selectMaskName
        self.username=username if username is not None else ''
        self.ctime =ctime if ctime is not None else datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        self.software = software
        if recordMaskInComposite is not None:
            self.recordMaskInComposite = recordMaskInComposite

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

    def usesInputMaskForSelectMask(self):
        return self.inputMaskName == self.selectMaskName

    def setArguments(self, args):
        self.arguments = dict()
        for k, v in args.iteritems():
            self.arguments[k] = v
            if k == 'inputmaskname':
                self.setInputMaskName(v)

    def setSelectMaskName(self, selectMaskName):
        self.selectMaskName = selectMaskName

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
        if name is None:
            return
        op = getOperationWithGroups(self.operationName)
        self.category = op.category if op is not None else None
        self.recordMaskInComposite = 'yes' if op is not None and op.includeInMask else 'no'
        self.generateMask = op.generateMask if op is not None else True


class LinkTool:
    def __init__(self):
        return

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):
        return None, None, {}, []

    def _addAnalysis(self, startIm, destIm, op, analysis, mask, linktype=None,
                     arguments={}):
        import importlib
        opData = getOperationWithGroups(op)
        if opData is None:
            return
        for analysisOp in opData.analysisOperations:
            mod_name, func_name = analysisOp.rsplit('.', 1)
            try:
                mod = importlib.import_module(mod_name)
                func = getattr(mod, func_name)
                func(analysis, startIm, destIm, mask=invertMask(mask),linktype=linktype, arguments=arguments)
            except Exception as e:
                print 'Failed to run analysis ' + analysisOp + ': ' + str(e)


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
        mask, analysis = createMask(im1, im2, invert=False, arguments=arguments)
        return im1, im2, mask, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        errors = list()
        maskname = start + '_' + destination + '_mask' + '.png'
        if op == 'Donor':
            predecessors = scModel.G.predecessors(destination)
            mask = None
            expect_donor_mask = False
            if not skipDonorAnalysis:
                errors= list()
                for pred in predecessors:
                    edge = scModel.G.get_edge(pred, destination)
                    op = getOperationWithGroups(edge['op'])
                    expect_donor_mask = op is not None and 'checkSIFT' in op.rules
                    if expect_donor_mask:
                        mask, analysis = interpolateMask(
                            scModel.G.get_edge_image(pred, destination, 'maskname')[0], startIm, destIm,
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
                    if edge['op'] != 'Donor':
                        mask = invertMask(scModel.G.get_edge_image(pred, start, 'maskname')[0])
                        if mask.size != startIm.size:
                            mask = mask.resize(startIm.size,Image.ANTIALIAS)
                        break
            if mask is None:
                mask = convertToMask(startIm)
                if expect_donor_mask:
                    errors = ["Donor image has insufficient features for SIFT and does not have a predecessor node."]
                analysis = {}
            else:
                mask = startIm.apply_alpha_to_mask(mask)
        else:
            mask, analysis = createMask(startIm, destIm, invert=invert, arguments=arguments, crop=(op == 'TransformCrop'))
            exifDiff = exif.compareexif(startFileName, destFileName)
            analysis = analysis if analysis is not None else {}
            analysis['exifdiff'] = exifDiff
            self._addAnalysis(startIm, destIm, op, analysis, mask, linktype='image.image',
                              arguments=consolidate(arguments,analysis_params))
        return maskname, mask, analysis, errors

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
        mask, analysis = createMask(im1, im2, invert=False, arguments=arguments)
        return im1, im2, mask, analysis

    def compareImages(self, start, destination, scModel, op, invert=False, arguments={},
                      skipDonorAnalysis=False,analysis_params={}):
        args = dict(arguments)
        args['skipSnapshot'] = True
        startIm, startFileName = scModel.getImageAndName(start,arguments=args)
        destIm, destFileName = scModel.getImageAndName(destination)
        errors = list()
        maskname = start + '_' + destination + '_mask' + '.png'
        if op == 'Donor':
            errors = ["An video cannot directly donate to an image.  First select a frame using an appropriate operation."]
            analysis = {}
        else:
            mask, analysis = createMask(startIm, destIm, invert=invert, arguments=arguments)
            exifDiff = exif.compareexif(startFileName, destFileName)
            analysis = analysis if analysis is not None else {}
            analysis['exifdiff'] = exifDiff
            self._addAnalysis(startIm, destIm, op, analysis, mask,linktype='video.image',
                              arguments=consolidate(arguments,analysis_params))
        return maskname, mask, analysis, errors

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
        maskname, mask, analysis, errors = self.compareImages(start, end, scModel, 'noOp', skipDonorAnalysis=True,
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
                    os.path.join(scModel.G.dir,start + '_' + destination + '_mask'),
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
        maskname = start + '_' + destination + '_mask' + '.png'
        if op != 'Donor' and not getOperationWithGroups(op).generateMask:
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
                                                       startSegment=getMilliSeconds(arguments[
                                                                                                 'Start Time']) if 'Start Time' in arguments else None,
                                                       endSegment=getMilliSeconds(arguments[
                                                                                               'End Time']) if 'End Time' in arguments else None,
                                                       applyConstraintsToOutput=op != 'SelectCutFrames')
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
                          arguments=consolidate(arguments,analysis_params))
        return maskname, mask, analysis, errors

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
        startIm, startFileName = scModel.getImageAndName(start)
        destIm, destFileName = scModel.getImageAndName(destination)
        mask = ImageWrapper(np.zeros((startIm.image_array.shape[0], startIm.image_array.shape[1])).astype('uint8'))
        maskname = start + '_' + destination + '_mask' + '.png'
        analysis =  dict()
        analysis['masks count'] = 0
        analysis['videomasks'] = list()
        metaDataDiff = video_tools.formMetaDataDiff(startFileName, destFileName)
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        self._addAnalysis(startIm, destIm, op, analysis, None,linktype='audio.audio',
                          arguments=consolidate(arguments,analysis_params))
        return maskname, mask, analysis, list()

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
        maskname = start + '_' + destination + '_mask' + '.png'
        self._addAnalysis(startIm, destIm, op, analysis, None, linktype='audio.audio',
                          arguments=consolidate(arguments,analysis_params))
        return maskname, mask, analysis, list()

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
        maskname = start + '_' + destination + '_mask' + '.png'
        analysis =  dict()
        analysis['masks count'] = 0
        analysis['videomasks'] = list()
        metaDataDiff = video_tools.formMetaDataDiff(startFileName, destFileName)
        analysis = analysis if analysis is not None else {}
        analysis['metadatadiff'] = metaDataDiff
        self._addAnalysis(startIm, destIm, op, analysis, None, linktype='video.audio',
                          arguments=consolidate(arguments,analysis_params))
        return maskname, mask, analysis, list()

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
        maskname = start + '_' + destination + '_mask' + '.png'
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
                          arguments=consolidate(arguments,analysis_params))
        return maskname, mask, analysis, errors



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
    """
    @type G: ImageGraph
    @type start: String
    @type end: String
    """

    def __init__(self, projectFileName, graph=None, importImage=False, notify=None,baseImageFileName=None):
        self._setup(projectFileName, graph=graph,baseImageFileName=baseImageFileName)
        self.notify = notify

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
                             filename.lower().endswith(suffix) and not filename.endswith('_mask' + suffix)])
        totalSet = sorted(totalSet, key=sortalg)
        for filename in totalSet:
            pathname = os.path.abspath(os.path.join(dir, filename))
            nname = self.G.add_node(pathname, xpos=xpos, ypos=ypos, nodetype='base')
            ypos += 50
            if ypos == 450:
                ypos = initialYpos
                xpos += 50
            if filename == baseImageFileName:
                self.start = nname
                self.end = None

    def addImage(self, pathname):
        maxx = max([self.G.get_node(node)['xpos'] for node in self.G.get_nodes() if 'xpos' in self.G.get_node(node)] + [50])
        maxy = max([self.G.get_node(node)['ypos'] for node in self.G.get_nodes() if 'ypos' in self.G.get_node(node)] + [50])
        nname = self.G.add_node(pathname, nodetype='base', xpos=maxx+75, ypos=maxy)
        self.start = nname
        self.end = None
        return nname

    def update_edge(self, mod):
        self.G.update_edge(self.start, self.end,
                           op=mod.operationName,
                           description=mod.additionalInfo,
                           arguments={k: v for k, v in mod.arguments.iteritems() if k != 'inputmaskname'},
                           recordMaskInComposite=mod.recordMaskInComposite,
                           editable='no' if (
                                                mod.software is not None and mod.software.internal) or mod.operationName == 'Donor' else 'yes',
                           softwareName=('' if mod.software is None else mod.software.name),
                           softwareVersion=('' if mod.software is None else mod.software.version),
                           inputmaskname=mod.inputMaskName,
                           selectmaskname=mod.selectMaskName)
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
        Return a tuple (edge, base node) for each valid donor path through the graph
        """
        donorEdges = [edge for edge in self.G.get_edges() if
                         self.G.get_edge(edge[0],edge[1])['op'] == 'Donor']
        results = []
        for edge in donorEdges:
            baseSet = self._findBaseNodes(edge[0])
            if len(baseSet) > 0:
                results.append((edge, baseSet[0]))
            else:
                results.append((edge, None))
        return results

    def removeCompositesAndDonors(self):
        """
        Remove a composite image or a donor image associated with any node
        """
        self.G.removeCompositesAndDonors()

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

    def connect(self, destination, mod=Modification('Donor', ''), invert=False, sendNotifications=True,
                skipDonorAnalysis=False):
        """ Given a image node name, connect the new node to the end of the currently selected node.
             Create the mask, inverting the mask if requested.
             Send a notification to the register caller if requested.
             Return an error message on failure, otherwise return None
        """
        if self.start is None:
            return "Node node selected", False
        if self.findChild(destination, self.start):
            return "Cannot connect to ancestor node", False
        for suc in self.G.successors(self.start):
            if suc == destination:
                return "Cannot connect to the same node twice", False
        return self._connectNextImage(destination, mod, invert=invert, sendNotifications=sendNotifications,
                                      skipDonorAnalysis=skipDonorAnalysis)


    def getProbeSet(self,skipComputation=False):
        """
        Calls constructComposites() and constructDonors()
        :return: list if Probe
        @rtype: List[Probe]
        """
        if not skipComputation:
            self.removeCompositesAndDonors()
            self.constructCompositesAndDonors()
        probes = list()
        for node_id in self.G.get_nodes():
            node = self.G.get_node(node_id)
            if 'compositemaskname' in node and len(node['compositemaskname']) > 0:
                composite_mask,composite_mask_filename = self.G.get_composite_mask(node_id)
                edgeTuples = self._constructProbeSet(node_id)
                for edgeTuple in edgeTuples:
                    # donor mask
                    donor_mask_image = None
                    donor_mask_file_name = None
                    donorbase = None
                    edge_end_node = self.G.get_node(edgeTuple[0][1])
                    if 'donormaskname' in edge_end_node:
                        donor_mask_image, donor_mask_file_name = self.G.get_donor_mask(edgeTuple[0][1])
                        donorbase = edge_end_node['donorbase']
                    elif edgeTuple[2] is not None:
                        donor_mask_file_name = os.path.abspath(os.path.join(self.get_dir(), edgeTuple[2]['maskname']))
                        donor_mask_image = self.G.openImage(donor_mask_file_name, mask=False)
                        donorbase = node['compositebase']
                    target_mask,target_mask_filename = self._toProbeComposite(composite_mask,
                                                                              edgeTuple[1],
                                                                              node_id,
                                                                              edgeTuple[0],
                                                                              regenerate = not skipComputation)
                    # no color in the composite mask...covered up
                    if target_mask is None:
                        continue
                    probes.append(Probe(edgeTuple[0],
                                  node_id,
                                  node['compositebase'],
                                  target_mask,
                                  target_mask_filename,
                                  sizeOfChange(np.asarray(target_mask).astype('uint8')),
                                  donorbase,
                                  donor_mask_image,
                                  donor_mask_file_name))
        return probes

    def getComposite(self):
        """
         Get the composite image for the selected node.
         If the composite does not exist AND the node is a leaf node, then create the composite
         Return None if the node is not a leaf node
        """
        nodeName = self.start if self.end is None else self.end
        mask, filename = self.G.get_composite_mask(nodeName)
        if mask is None:
            # verify the node is a leaf node
            endPointTuples = self.getTerminalAndBaseNodeTuples()
            if nodeName in [x[0] for x in endPointTuples]:
                self.constructCompositesAndDonors()
                mask, filename = self.G.get_composite_mask(nodeName)
            else:
                return self.constructComposite()
        return mask

    def getDonorAndBaseImages(self,force=False):
        """
         Get the composite image for the selected node.
         If the composite does not exist AND the node is a leaf node, then create the composite
         Return None if the node is not a leaf node
        """
        nodeName = self.start if self.end is None else self.end
        mask = None
        baseImage = None
        # verify the node is a leaf node
        endPointTuples = self.getDonorAndBaseNodeTuples()
        for x in endPointTuples:
            if nodeName == x[0][1]:
                baseImage,_ = self.G.get_image(x[1])
                mask, filename = self.G.get_donor_mask(nodeName)
                if mask is None or force:
                    self.constructDonors()
                    mask, filename = self.G.get_donor_mask(nodeName)
                break
        return mask,baseImage

    def _constructComposites(self, nodeAndMasks, stopAtNode=None,edgeMap=dict(),level=IntObject()):
        """
          Walks up down the tree from base nodes, assemblying composite masks"
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
                compositeMask = self._extendComposite(nodeAndMask[2], edge, nodeAndMask[1], suc, level=level,
                                                          edgeMap=edgeMap)
                result.append((nodeAndMask[0], suc, compositeMask))
        if len(result) == 0:
            return nodeAndMasks
        finished.extend(self._constructComposites(result,stopAtNode=stopAtNode,level=level,edgeMap=edgeMap))
        return finished

    def _constructDonor(self, edge_id, mask):
        """
          Walks up down the tree from base nodes, assemblying composite masks"
        """
        for pred in self.G.predecessors(edge_id[0]):
            edge = self.G.get_edge(pred, edge_id[0])
            if edge['op'] == 'Donor':
                continue
            donorMask = self._alterDonor(mask,pred, edge_id[0], edge)
            return self._constructDonor((pred, edge_id[0]),donorMask)
        return mask

    def _toProbeComposite(self, composite_mask, edge, node, edge_id,regenerate=False):
        """
        :param self:
        :param composite_mask:
        :param edge:
        :param node:
        :param edge_id:
        :param regenerate:
        :return:
        @rtype: (ImageWrapper, str)
        """
        filename = os.path.join(self.get_dir(), 'composite_' + node + '_' + edge_id[0] + '_' + edge_id[1] + '.png')
        if os.path.exists(filename) and not regenerate:
            return openImageFile(filename),filename
        mask_array = np.asarray(composite_mask)
        color = tuple([int(x) for x in edge['compositecolor'].split()])
        result = np.ones(mask_array.shape).astype('uint8')*255
        matches = np.all(mask_array == color, axis=2)
        result[matches] = color
        if not np.any(matches):
            return None, None
        im = ImageWrapper(result)
        im.save(filename)
        return im, filename


    def _constructProbeSet(self, node):
        """
          Walks up down the tree from base nodes, assemblying composite masks"
        """
        donor_edge = None
        select_edge = None
        select_edge_parent = None
        result = list()
        for pred in self.G.predecessors(node):
            edge = self.G.get_edge(pred, node)
            if edge['op'] == 'Donor':
                donor_edge = edge
                continue
            if 'compositecolor' in edge:
                select_edge = edge
                select_edge_parent = pred
            result.extend(self._constructProbeSet(pred))
        if select_edge is not None:
            result.append(((select_edge_parent, node),select_edge,donor_edge))
        return result

    def constructComposite(self):
        """
         Construct the composite mask for the selected node.
         Does not save the composite in the node.
         Returns the composite mask if successful, otherwise None
        """
        edgeMap = dict()
        selectedNode = self.end if self.end is not None else self.start
        baseNodes = self._findBaseNodes(selectedNode)
        level= IntObject()
        if len(baseNodes) > 0:
            baseNode = baseNodes[0]
            composites = self._constructComposites([(baseNode, baseNode, None)], edgeMap=edgeMap,
                                                  stopAtNode=selectedNode,level = level)
            for composite in composites:
                if composite[1] == selectedNode and composite[2] is not None:
                    intensityMap = redistribute_intensity(edgeMap)
                    return ImageWrapper(toColor(composite[2], intensity_map=intensityMap))
        return None

    def constructCompositesAndDonors(self):
        """
          Remove all prior constructed composites.
          Find all valid base node, leaf node tuples.
          Construct the composite make along the paths from base to lead node.
          Save the composite in the associated leaf nodes.
        """
        self.constructDonors()
        composites = list()
        edgeMap = dict()
        level = IntObject()
        endPointTuples = self.getTerminalAndBaseNodeTuples()
        for baseNode in set([endPointTuple[1][0] for endPointTuple in endPointTuples]):
                composites.extend(self._constructComposites([(baseNode, baseNode, None)], edgeMap=edgeMap,level=level))
        intensityMap = redistribute_intensity(edgeMap)
        changes = []
        for composite in composites:
            color_composite = toColor(composite[2], intensity_map=intensityMap)
            globalchange, changeCategory, ratio = maskChangeAnalysis(toComposite(composite[2]),
                                                                     globalAnalysis=True)
            changes.append((globalchange, changeCategory, ratio))
            self.G.addCompositeToNode(composite[1], composite[0], ImageWrapper(
                color_composite),changeCategory)
            graph_rules.setFinalNodeProperties(self, composite[1])

        for k, v in edgeMap.iteritems():
            if type(v) == int:
                continue
            self.G.get_edge(k[0], k[1])['compositecolor'] = str(list(v[1])).replace('[', '').replace(']','').replace(
                    ',', '')



        return composites

    def constructDonors(self):

        """
          Construct donor images
          Find all valid base node, leaf node tuples.
        """
        donors = list()
        donor_nodes = set()
        endPointTuples = self.getDonorAndBaseNodeTuples()
        for endPointTuple in endPointTuples:
            edge_im = self.G.get_edge_image(endPointTuple[0][0],endPointTuple[0][1],'maskname')[0]
            if edge_im is None:
                continue
            donor_mask = self._constructDonor(endPointTuple[0],np.asarray(edge_im))
            if donor_mask is not None:
                self.G.addDonorToNode(endPointTuple[0][1],endPointTuple[1], ImageWrapper(donor_mask.astype('uint8')))
                donors.append((endPointTuple[1], donor_mask))
                donor_nodes.add(endPointTuple[0][1])
        for edge_id in self.G.get_edges():
            edge = self.G.get_edge(edge_id[0],edge_id[1])
            if 'inputmaskname' in edge and \
                            edge['inputmaskname'] is not None and \
                            len(edge['inputmaskname']) > 0 and \
                            edge['recordMaskInComposite'] == 'yes' and \
                            edge_id[1] not in donor_nodes:
                donor_mask_file_name = os.path.abspath(os.path.join(self.get_dir(), edge['inputmaskname']))
                try:
                    if os.path.exists(donor_mask_file_name):
                        if len(edge['inputmaskname']) == 0:
                            donor_mask = self.G.get_image(edge_id[0])[0].to_mask().to_array()
                        else:
                            donor_mask = self.G.openImage(donor_mask_file_name, mask=False).to_mask().to_array()
                        donor_mask = self._constructDonor(edge_id,donor_mask)
                        baseNodes = self._findBaseNodes(edge_id[0])
                        baseNode = baseNodes[0] if len(baseNodes) > 0 else None
                        if donor_mask is not None:
                            self.G.addDonorToNode(edge_id[1], baseNode, ImageWrapper(donor_mask.astype('uint8')))
                            donors.append((edge_id, donor_mask))
                            donor_nodes.add(edge_id[1])
                except Exception as ex:
                    print 'could not generate donor mask for input mask'  + donor_mask_file_name
        return donors

    def addNextImage(self, pathname, invert=False, mod=Modification('', ''), sendNotifications=True, position=(50, 50),
                     skipRules=False):
        """ Given a image file name and  PIL Image, add the image to the project, copying into the project directory if necessary.
             Connect the new image node to the end of the currently selected edge.  A node is selected, not an edge, then connect
             to the currently selected node.  Create the mask, inverting the mask if requested.
             Send a notification to the register caller if requested.
             Return an error message on failure, otherwise return None
        """
        if (self.end is not None):
            self.start = self.end
        destination = self.G.add_node(pathname, seriesname=self.getSeriesName(), xpos=position[0], ypos=position[1],
                                      nodetype='base')
        msg, status = self._connectNextImage(destination, mod, invert=invert, sendNotifications=sendNotifications,
                                             skipRules=skipRules)
        return msg, status

    def getLinkType(self, start, end):
        return self.getNodeFileType(start) + '.' + self.getNodeFileType(end)

    def getLinkTool(self, start, end):
        return linkTools[self.getLinkType(start, end)]

    def _compareImages(self, start, destination, opName, invert=False, arguments={}, skipDonorAnalysis=True, analysis_params=dict()):
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
        maskname, mask, analysis, errors = self._compareImages(self.start, self.end, edge['op'],
                                                               arguments=edge['arguments'] if 'arguments' in edge else dict(),
                                                               skipDonorAnalysis=skipDonorAnalysis,
                                                               analysis_params=analysis_params)
        self.G.update_mask(self.start, self.end, mask=mask,errors=errors,**consolidate(analysis,analysis_params))

    def _connectNextImage(self, destination, mod, invert=False, sendNotifications=True, skipRules=False,
                          skipDonorAnalysis=False,
                          analysis_params={}):
        try:
            maskname, mask, analysis, errors = self._compareImages(self.start, destination, mod.operationName,
                                                                   invert=invert, arguments=mod.arguments,
                                                                   skipDonorAnalysis=skipDonorAnalysis,
                                                                   analysis_params=analysis_params)
            self.end = destination
            if errors:
                mod.errors = errors
            self.__addEdge(self.start, self.end, mask, maskname, mod, analysis)
            edgeErrors = graph_rules.run_rules(mod.operationName, self.G, self.start, destination)
            msgFromRules = os.linesep.join(edgeErrors) if len(edgeErrors) > 0 and not skipRules else ''
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

    def __addEdge(self, start, end, mask, maskname, mod, additionalParameters):
        if len(mod.arguments) > 0:
            additionalParameters['arguments'] = {k: v for k, v in mod.arguments.iteritems() if k != 'inputmaskname'}
        im = self.G.add_edge(start, end, mask=mask, maskname=maskname,
                             op=mod.operationName, description=mod.additionalInfo,
                             recordMaskInComposite=mod.recordMaskInComposite,
                             editable='no' if (
                                                  mod.software is not None and mod.software.internal) or mod.operationName == 'Donor' else 'yes',
                             softwareName=('' if mod.software is None else mod.software.name),
                             softwareVersion=('' if mod.software is None else mod.software.version),
                             inputmaskname=mod.inputMaskName,
                             selectmaskname=mod.selectMaskName,
                             automated=mod.automated,
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
            self.G.setDataItem('groups',groups)

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

    def toCSV(self, filename, additionalpaths=list()):
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
                if 'compositecolor' not in edge:
                    continue
                row = [self.G.get_name(),edge_id[0],edge_id[1],edge['op'], edge['compositecolor']]
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
        self.start = None
        self.end = None
        self.G.undo()

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
        return createGraph(projectFileName, projecttype=projecttype)

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
        self.clear_validation_properties()
        self.G.saveas(pathname)

    def save(self):
        self.clear_validation_properties()
        self.G.save()

    def getDescriptionForPredecessor(self, node):
        for pred in self.G.predecessors(node):
            edge = self.G.get_edge(pred, node)
            if edge['op'] != 'Donor':
                return self._getModificationForEdge(pred, node, edge)
        return None

    def getDescription(self):
        if self.start is None or self.end is None:
            return None
        edge = self.G.get_edge(self.start, self.end)
        if edge is not None:
            return self._getModificationForEdge(self.start, self.end,edge)
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

    def getSelectMask(self):
        """
        A selectMask is a mask the is used in composite mask production, overriding the default link mask
        """
        if self.end is None:
            return None, None
        mask = self.G.get_edge_image(self.start, self.end, 'maskname')
        selectMask = self.G.get_edge_image(self.start, self.end, 'selectmaskname')
        if selectMask[0] != None:
            return selectMask
        return mask

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
        stat_names = ['ssim','psnr','shape change','masks count','change size category','change size ratio']
        return '  '.join([ key + ': ' + formatStat(value) for key,value in edge.items() if key in stat_names ])

    def currentImage(self):
        if self.end is not None:
            return self.getImageAndName(self.end)
        elif self.start is not None:
            return self.getImageAndName(self.start)
        return None, None

    def selectImage(self, name):
        self.start = name
        self.end = None

    def selectEdge(self, start, end):
        self.start = start
        self.end = end

    def remove(self):
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

    def getProjectData(self, item):
        return self.G.getDataItem(item)

    def setProjectData(self, item, value):
        self.G.setDataItem(item, value)

    def get_edges(self):
        return [self.G.get_edge(edge[0],edge[1]) for edge in self.G.get_edges()]

    def getVersion(self):
        """ Return the graph/software versio n"""
        return self.G.getVersion()

    def getGraph(self):
        return self.G

    def validate(self):
        """ Return the list of errors from all validation rules on the graph. """

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
        select_node = nodes[0] if (len(nodes) > 0) else "NA"
        nodeSet = set(nodes)

        for found in self.G.findRelationsToNode(nodeSet.pop()):
            if found in nodeSet:
                nodeSet.remove(found)

        for node in nodeSet:
            total_errors.append((str(node), str(node), str(node) + ' is part of an unconnected subgraph'))

        total_errors.extend(self.G.file_check())

        cycleNode = self.G.getCycleNode()
        if cycleNode is not None:
            total_errors.append((str(cycleNode), str(cycleNode), "Graph has a cycle"))

        for error in graph_rules.check_graph_rules(self.G):
            total_errors.append((str(select_node), str(select_node), error))

        for frm, to in self.G.get_edges():
            edge = self.G.get_edge(frm, to)
            op = edge['op']
            errors = graph_rules.run_rules(op, self.G, frm, to)
            if len(errors) > 0:
                total_errors.extend([(str(frm), str(to), str(frm) + ' => ' + str(to) + ': ' + err) for err in errors])
        return total_errors

    def __assignLabel(self, node, label):
        prior = self.G.get_node(node)['nodetype'] if 'nodetype' in self.G.get_node(node) else None
        if prior != label:
            self.G.update_node(node, nodetype=label)
            if self.notify is not None:
                self.notify(node, 'label')

    def labelNodes(self, destination):
        baseNodes = []
        candidateBaseDonorNodes = []
        for terminal in self._findTerminalNodes(destination):
            baseNodes.extend(self._findBaseNodes(terminal))
            candidateBaseDonorNodes.extend(self._findBaseNodes(terminal, excludeDonor=False))
        baseDonorNodes = [node for node in candidateBaseDonorNodes if node not in baseNodes]
        for node in baseDonorNodes:
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

    def _findTerminalNodes(self, node):
        succs = self.G.successors(node)
        res = [node] if len(succs) == 0 else list()
        for succ in succs:
            res.extend(self._findTerminalNodes(succ))
        return res

    def _findTerminalNodes(self, node):
        return self._findTerminalNodesWithCycleDetection(node, visitSet=list())

    def _findTerminalNodesWithCycleDetection(self, node, visitSet=list()):
        succs = self.G.successors(node)
        res = [node] if len(succs) == 0 else list()
        for succ in succs:
            if succ in visitSet:
                continue
            visitSet.append(succ)
            res.extend(self._findTerminalNodesWithCycleDetection(succ, visitSet=visitSet))
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
                res.append((pred, node,edge))
            res.extend(self._findEdgesWithCycleDetection(pred, excludeDonor=excludeDonor,
                                                             visitSet=visitSet) if isNotDonor else list())
        return res

    def _findBaseNodes(self, node, excludeDonor=True):
        return self._findBaseNodesWithCycleDetection(node, excludeDonor=excludeDonor, visitSet=list())

    def _findBaseNodesWithCycleDetection(self, node, excludeDonor=True, visitSet=list()):
        preds = self.G.predecessors(node)
        res = [node] if len(preds) == 0 else list()
        for pred in preds:
            if pred in visitSet:
                continue
            isNotDonor = (self.G.get_edge(pred, node)['op'] != 'Donor' or not excludeDonor)
            if isNotDonor:
                visitSet.append(pred)
            res.extend(self._findBaseNodesWithCycleDetection(pred, excludeDonor=excludeDonor,
                                                             visitSet=visitSet) if isNotDonor else list())
        return res

    def isDonorEdge(self, start, end):
        edge = self.G.get_edge(start, end)
        if edge is not None:
            return edge['op'] == 'Donor'
        return False

    def getTerminalToBasePairs(self, suffix='.jpg'):
        """
         find all pairs of leaf nodes to matching base nodes
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

    def imageFromPlugin(self, filter, im, filename, **kwargs):
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
        """
        op = plugins.getOperation(filter)
        suffixPos = filename.rfind('.')
        suffix = filename[suffixPos:].lower()
        preferred = plugins.getPreferredSuffix(filter)
        if preferred is not None:
            suffix = preferred
        target = os.path.join(tempfile.gettempdir(), self.G.new_name(os.path.split(filename)[1], suffix=suffix))
        shutil.copy2(filename, target)
        msg = None
        try:
            extra_args,warning_message = plugins.callPlugin(filter, im, filename, target, **self._resolvePluginValues(kwargs))
        except Exception as e:
            msg = str(e)
            extra_args = None
        if msg is not None:
            return self._pluginError(filter, msg), []
        description = Modification(op[0], filter + ':' + op[2])
        sendNotifications = kwargs['sendNotifications'] if 'sendNotifications' in kwargs else True
        skipRules = kwargs['skipRules'] if 'skipRules' in kwargs else False
        software = Software(op[3], op[4], internal=True)
        description.setArguments(
            {k: v for k, v in kwargs.iteritems() if k != 'donor' and k != 'sendNotifications' and k != 'skipRules'})
        if extra_args is not None and type(extra_args) == type({}):
             for k,v in extra_args.iteritems():
                 if k not in kwargs:
                     description.arguments[k] = v
        description.setSoftware(software)
        description.setAutomated('yes')
        msg2, status = self.addNextImage(target, mod=description, sendNotifications=sendNotifications,
                                         skipRules=skipRules,
                                         position=self._getCurrentPosition((75 if 'donor' in kwargs else 0,75)))
        pairs = list()
        msg = '\n'.join([msg if msg else '',
                         warning_message if warning_message else '',
                         msg2 if msg2 else '']).strip()
        if status:
            pairs.append((self.start, self.end))
            if 'donor' in kwargs:
                _end = self.end
                _start = self.start
                self.selectImage(kwargs['donor'])
                self.connect(_end)
                pairs.append((kwargs['donor'], _end))
                self.select((_start, _end))
                if 'donor'  in msg:
                    msg = None
        os.remove(target)
        return self._pluginError(filter, msg), pairs

    def _resolvePluginValues(self, args):
        result = {}
        for k, v in args.iteritems():
            if k == 'donor':
                result[k] = self.getImageAndName(v)
            else:
                result[k] = v
        return result

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

        def filterFunction(file):
            return not self.G.has_node(os.path.split(file[0:file.rfind('.')])[1]) and not (file.rfind('_mask') > 0)

        def findFiles(dir, preFix, filterFunction):
            set = [os.path.abspath(os.path.join(dir, filename)) for filename in os.listdir(dir) if
                   (filename.startswith(preFix)) and filterFunction(os.path.abspath(os.path.join(dir, filename)))]
            set.sort()
            return set

        nfile = None
        for file in findFiles(self.G.dir, prefix, filterFunction):
            nfile = file
            break
        return self.G.openImage(nfile) if nfile is not None else None, nfile

    def getDescriptions(self):
        """
        :return: descriptions for all edges
         @rtype [Modification]
        """
        return [self._getModificationForEdge(edge[0],edge[1],self.G.get_edge(edge[0],edge[1])) for edge in self.G.get_edges()]

    def openImage(self, nfile):
        im = None
        if nfile is not None and nfile != '':
            im = self.G.openImage(nfile)
        return nfile, im

    def findEdgesByOperationName(self,opName):
        return [edge for edge in self.get_edges()
            if edge['op'] == opName]

    def export(self, location,include=[]):
        self.clear_validation_properties()
        path, errors = self.G.create_archive(location,include=include)
        return errors

    def exporttos3(self, location, tempdir=None):
        import boto3
        self.clear_validation_properties()
        path, errors = self.G.create_archive(tempfile.gettempdir() if tempdir is None else tempdir)
        if len(errors) == 0:
            s3 = boto3.client('s3', 'us-east-1')
            BUCKET = location.split('/')[0].strip()
            DIR = location[location.find('/') + 1:].strip()
            print 'Upload to s3://' + BUCKET + '/' + DIR + '/' + os.path.split(path)[1]
            DIR = DIR if DIR.endswith('/') else DIR + '/'
            s3.upload_file(path, BUCKET, DIR + os.path.split(path)[1])
            os.remove(path)
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

    def _extendComposite(self,compositeMask,edge,source,target,level=IntObject(),edgeMap={}):
        if compositeMask is None:
            imarray = self.G.get_image(source)[0].to_array()
            compositeMask = np.zeros((imarray.shape[0], imarray.shape[1])).astype(('uint8'))
        # merge masks first, the mask is the same size as the input image
        # consider a cropped image.  The mask of the crop will have the change high-lighted in the border
        # consider a rotate, the mask is either ignored or has NO change unless interpolation is used.
        edgeMask = self.G.get_edge_image(source, target, 'maskname')[0]
        selectMask = self.G.get_edge_image(source, target, 'selectmaskname')[0]
        edgeMask = selectMask.to_array() if selectMask is not None else edgeMask.to_array()
        if 'recordMaskInComposite' in edge and edge['recordMaskInComposite'] == 'yes':
            compositeMask = mergeMask(compositeMask, edgeMask, level=level.increment())
            try:
               color = [int(x)  for x in edge['compositecolor'].split(' ')] if 'compositecolor' in edge else None
            except:
               color = None
            edgeMap[(source, target)] = (level.value,color)
        # change the mask to reflect the output image
        # considering the crop again, the high-lighted change is not dropped
        # considering a rotation, the mask is now rotated
        sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
        location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0, 0)
        rotation = float(edge['rotation'] if 'rotation' in edge and edge['rotation'] is not None else 0.0)
        args = edge['arguments'] if 'arguments' in edge else {}
        rotation = float(args['rotation'] if 'rotation' in args and args['rotation'] is not None else rotation)
        interpolation = args['interpolation'] if 'interpolation' in args and len(
            args['interpolation']) > 0 else 'nearest'
        tm = edge['transform matrix'] if 'transform matrix' in edge  else None
        flip = args['flip direction'] if 'flip direction' in args else None
        orientflip, orientrotate = exif.rotateAmount(self._getOrientation(edge))
        flip = flip if flip is not None else orientflip
        rotation = rotation if rotation is not None and abs(rotation) > 0.00001 else orientrotate
        tm = None if ('global' in edge and edge['global'] == 'yes' and rotation != 0.0) else tm
        tm = None if ('global' in edge and edge['global'] == 'yes' and flip is not None) else tm
        tm = tm if sizeChange == (0,0)  else None
        compositeMask = alterMask(compositeMask, edgeMask, rotation=rotation,
                                           sizeChange=sizeChange, interpolation=interpolation,
                                           location=location, flip=flip,
                                           transformMatrix=tm,
                                           crop=edge['op']=='TransformCrop')
        return compositeMask

    def _getOrientation(self,edge):
        return edge['exifdiff']['Orientation'][1] if ('arguments' in edge and \
                                                      (('rotate' in edge['arguments'] and \
                                                     edge['arguments']['rotate'] == 'yes') or \
                                                     ('Image Rotated' in edge['arguments'] and \
                                                      edge['arguments']['Image Rotated'] == 'yes'))) and \
                                                     'exifdiff' in edge and 'Orientation' in edge['exifdiff'] else ''

    def _alterDonor(self,donorMask,source, target,edge):
        if donorMask is None:
            return None
        edgeMask = self.G.get_edge_image(source, target, 'maskname')[0]
        selectMask = self.G.get_edge_image(source, target, 'selectmaskname')[0]
        edgeMask = selectMask.to_array() if selectMask is not None else edgeMask.to_array()
        # change the mask to reflect the output image
        # considering the crop again, the high-lighted change is not dropped
        # considering a rotation, the mask is now rotated
        sizeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)
        location = toIntTuple(edge['location']) if 'location' in edge and len(edge['location']) > 0 else (0, 0)
        rotation = float(edge['rotation'] if 'rotation' in edge and edge['rotation'] is not None else 0.0)
        args = edge['arguments'] if 'arguments' in edge else {}
        rotation = float(args['rotation'] if 'rotation' in args and args['rotation'] is not None else rotation)
        interpolation = args['interpolation'] if 'interpolation' in args and len(
            args['interpolation']) > 0 else 'nearest'
        tm = edge['transform matrix'] if 'transform matrix' in edge  else None
        flip = args['flip direction'] if 'flip direction' in args else None
        orientflip, orientrotate = exif.rotateAmount(self._getOrientation(edge))
        orientrotate = -orientrotate if orientrotate is not None else None
        flip = flip if flip is not None else orientflip
        rotation = rotation if rotation is not None and abs(rotation) > 0.00001 else orientrotate
        tm = None if ('global' in edge and edge['global'] == 'yes' and rotation != 0.0) else tm
        tm = None if ('global' in edge and edge['global'] == 'yes' and flip is not None) else tm
        tm = tm if sizeChange == (0,0) else None
        return  alterReverseMask(donorMask, edgeMask, rotation=rotation,
                                           sizeChange=sizeChange,
                                           location=location, flip=flip,
                                           transformMatrix=tm,
                                          crop = edge['op']=='TransformCrop')

    def _getModificationForEdge(self, start,end, edge):
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
                            selectMaskName=edge['selectmaskname'] if 'selectmaskname' in edge and edge[
                                'selectmaskname'] and len(edge['selectmaskname']) > 0 else None,
                            changeMaskName=edge['maskname'] if 'maskname' in edge else None,
                            software=Software(edge['softwareName'] if 'softwareName' in edge else None,
                                              edge['softwareVersion'] if 'softwareVersion' in edge else None,
                                              'editable' in edge and edge['editable'] == 'no'),
                            recordMaskInComposite=edge[
                                'recordMaskInComposite'] if 'recordMaskInComposite' in edge else 'no',
                            automated=edge['automated'] if 'automated' in edge else 'no',
                            username =edge['username'] if 'username' in edge else '',
                            ctime=edge['ctime'] if 'ctime' in edge else default_ctime,
                            errors=edge['errors'] if 'errors' in edge else list(),
                            maskSet=(VideoMaskSetInfo(edge['videomasks']) if (
                                'videomasks' in edge and len(edge['videomasks']) > 0) else None))

    def clear_validation_properties(self):
        validationProps = {'validation':'no', 'validatedby':'', 'validationdate':''}
        currentProps = {}
        for p in validationProps:
            currentProps[p] = self.getProjectData(p)
        if all(vp in currentProps for vp in validationProps) and currentProps['validatedby'] != get_username():
            for key, val in validationProps.iteritems():
                self.setProjectData(key, val)


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
