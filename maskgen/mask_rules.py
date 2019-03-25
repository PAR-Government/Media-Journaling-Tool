# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import logging
import os
import sys
import time
import traceback
from collections import namedtuple

import cv2
import exif
import graph_rules
import numpy as np
import tool_set
import video_tools
from graph_meta_tools import MetaDataExtractor
from image_graph import ImageGraph
from image_wrap import ImageWrapper, openImageMaskFile
from support import getValue
from tool_set import toIntTuple, alterMask, alterReverseMask, shortenName, openImageFile, sizeOfChange, \
    convertToMask,maskChangeAnalysis,  mergeColorMask, maskToColorArray, IntObject, addFrame, \
    getMilliSecondsAndFrameCount, sumMask, applyFlipComposite


class EdgeMaskError(ValueError):
    def __init__(self, message, edge_id):
        ValueError.__init__(self, message)
        self.edge_id = edge_id

def raiseError(caller, message, edge_id):
    logging.getLogger('maskgen').error('{} reporting {} for edge {} to {}'.format( caller, message, edge_id[0], edge_id[1]))
    raise EdgeMaskError(message, edge_id)

#====================================================================
#  Probe Support Classes
#====================================================================

class VideoSegment:
    """
      USED FOR AUDIO and VIDEO
      Filename is ONLY present if there are localization tasks.
      rate = frames per second
      starttime = in milliseconds
      startframe = integer number
      endtime = in milliseconds
      endframe = integer number
      frames = integer total frames changed in segment
      filename = string
    """
    rate = 0.0
    starttime = 0.0
    startframe = 0
    endtime = 0.0
    endframe = 0
    frames = 0
    filename = None
    media_type = None

    def __init__(self,rate, starttime, startframe, endtime,endframe, frames, filename, media_type, error):
        """
        :param rate: seconds
        :param starttime: milliseconds starting at 0
        :param startframe: starting at 1
        :param endtime:milliseconds the start time of the last frame manipulated
        :param endframe: the last frame manipulated
        :param frames: number frames affected by manipulation in this segment (end - start + 1)
        :param filename: may not be present without mask, otherwise this is an HDF5 file
        :param media_type: one of 'audio','video'
        :param error: amount of accumluative rounding error due to frame rate changes in milliseconds
        @type rate : float
        @type starttime : float
        @type startframe : int
        @type endtime : float
        @type endframe : int
        @type frames : int
        @type filename : str
        @type media_type : str
        @type error : float
        """
        self.rate = rate
        self.startframe = startframe
        self.starttime = starttime
        self.endtime = endtime
        self.endframe = endframe
        self.frames = frames
        self.filename = filename
        self.media_type = media_type
        self.error = error

class Probe:
    """
    donorBaseNodeId = the donor base media node id
    donorVideoSegments = the list video and audio donor segments
    targetMaskImage = the ImageWrapper target mask image (aligned to target final node)
    donorMaskImage= the ImageWrapper donor mask image (aligned to donor)
    targetMaskFileName = the file name of the target mask image (aligned to target final node)
    donorMaskFileName = the file name of the  donor mask image (aligned to donor)
    targetVideoSegments = the list video and audio final node segments
    targetChangeSizeInPixels = (0,0)
    failure = if failure occured generating this probe
    level = 0
    taskDesignation = str
    """
    edgeId = None
    targetBaseNodeId = None
    finalNodeId = None
    composites = None
    donorBaseNodeId = None
    donorVideoSegments = None
    targetMaskImage = None
    donorMaskImage= None
    targetMaskFileName = None
    donorMaskFileName = None
    targetVideoSegments = None
    donorMask = None
    targetChangeSizeInPixels = 0
    level = 0
    taskDesignation = 'detect'
    # vfr indicator

    """
    @type edgeId: tuple
    @type targetBaseNodeId: str
    @type targetMaskFileName: str
    #type targetChangeSizeInPixels: size
    @type targetMaskImage: ImageWrapper
    @type finalNodeId: str
    @type composites: dict[str,dict]
    @type donorBaseNodeId: str
    @type donorMaskFileName: str
    @type finalImageFileName: str
    @type donorMaskImage: ImageWrapper
    @type donorVideoSegments: list[VideoSegment]
    @type level: int
    @type targetVideoSegments: list[ VideoSegment]

    The target is the node edgeId's target node (edgeId[1])--the image after the manipulation.
    The targetBaseNodeId is the id of the base node that supplies the base image for the target.
    The level is level from top to bottom in the tree.  Top is level 0
    """

    def __init__(self,
                 edgeId,
                 finalNodeId,
                 targetBaseNodeId,
                 donorBaseNodeId,
                 targetMaskImage = None,
                 donorMaskFileName=None,
                 targetMaskFileName=None,
                 targetVideoSegments=None,
                 donorMask=None,
                 donorMaskImage=None,
                 donorVideoSegments=None,
                 targetChangeSizeInPixels=0,
                 finalImageFileName=None,
                 empty=False,
                 failure=False,
                 donorFailure=False,
                 level=0,
                 taskDesignation='detect',
                 usesSubsituteMask=False  ):
        self.edgeId = edgeId
        self.empty = empty
        self.finalNodeId = finalNodeId
        self.targetBaseNodeId = targetBaseNodeId
        self.targetMaskFileName = targetMaskFileName
        self.donorBaseNodeId = donorBaseNodeId
        self.donorMaskFileName = donorMaskFileName
        self.donorMaskImage=donorMaskImage
        self.donorVideoSegments = donorVideoSegments
        self.targetVideoSegments = targetVideoSegments
        self.donorMask = donorMask
        self.targetMaskImage = targetMaskImage
        self.targetChangeSizeInPixels = targetChangeSizeInPixels
        self.level = level
        self.failure=failure
        self.donorFailure = donorFailure
        self.finalImageFileName = finalImageFileName
        self.composites = dict()
        self.taskDesignation = taskDesignation
        self.usesSubsituteMask = usesSubsituteMask

    def has_masks_in_target(self):
        if self.targetVideoSegments is not None:
            return len([s for s in self.targetVideoSegments if s.filename is not None]) > 0
        return False

    def max_time(self):
        mt = 0
        if self.targetVideoSegments is not None:
            mt = max(max([segment.endtime for segment in self.targetVideoSegments]), mt)
        if self.donorVideoSegments is not None:
            mt = max(max([segment.endtime for segment in self.donorVideoSegments]), mt)
        return mt

    def media_types(self):
        if self.targetVideoSegments  is not None:
            return list(set([segment.media_type for segment in self.targetVideoSegments]))
        elif self.donorVideoSegments  is not None:
            return list(set([segment.media_type for segment in self.donorVideoSegments]))

DonorImage = namedtuple('DonorImage', ['target', 'base', 'mask_wrapper', 'mask_file_name', 'media_type'])

class CompositeImage:

    def __init__(self,source, target, media_type, mask, issubstitute=False):
        self.source = source
        self.target = target
        self.media_type = media_type
        self.videomasks = mask if media_type != 'image' else None
        self.mask = mask if media_type == 'image' else None
        self.ok = True
        self.issubstitute = issubstitute

    def create(self, mask):
        return CompositeImage(self.source,self.target,self.media_type, mask, self.issubstitute)

    def __getitem__(self, item):
        if item == 0:
            return self.source
        elif item == 1:
            return self.target
        elif item == 2:
            return self.media_type
        elif item == 3:
            return self.videomasks
        else:
            return self.mask

    def isEmpty(self):
        if self.mask is not None:
            return np.sum(self.mask) == 0
        return self.videomasks is None or len(self.videomasks) == 0

    def isImage(self):
        return self.media_type == 'image'

    def sizeOfChange(self):
        return sizeOfChange(
            np.asarray(self.mask).astype('uint8')) if self.media_type == 'image' else None

    def finalMask(self):
        return self.mask if self.media_type == 'image' else video_tools.getSingleFrameFromMask(
                                    self.videomasks)

    def composeVideoSegments(self):
        return _compositeImageToVideoSegment(self) if not self.isImage() else None

def getOrientationForEdge(edge):
    orientation = getValue(edge,'exifdiff.Orientation')
    if (getValue(edge,'arguments.Image Rotated','no') == 'yes') and orientation is not None:
        return orientation[1]
    if (getValue(edge,'arguments.rotate','no') == 'yes') and orientation is not None:
        return orientation[2] if orientation[0].lower() == 'change' else orientation[1]
    return ''

class BuildState:
    def __init__(self,
                 edge,
                 source,
                 target,
                 edgeMask,
                 sourceShape,
                 targetShape,
                 compositeMask=None,
                 directory='.',
                 donorMask=None,
                 pred_edges=None,
                 graph=None,
                 checkEmpties=False
                 ):
        """

        :param edge: edge dictionary
        :param source: node id
        :param target: node id
        :param edgeMask: mask
        :param targetShape: (w,h)
        :param compositeMask: composite mask
        :param directory: directory
        :param donorMask: donor mask
        :param pred_edges:
        :param graph: ImageGraph
        @type edge: dict
        @type source: str
        @type target: str
        @type compositeMask: CompositeImage
        @type donorMask: CompositeImage
        @type pred_edges: list
        @type graph: ImageGraph
        @targetShape: (int,int)
        """
        self.isComposite = compositeMask is not None
        self.compositeMask = compositeMask
        self.edgeMask  = edgeMask
        self.sourceShape = sourceShape
        self.targetShape  = targetShape
        self.edge = edge
        self.source = source
        self.target = target
        self.directory = directory
        self.donorMask = donorMask
        self.pred_edges = pred_edges
        self.graph = graph
        self.meta_extractor =  MetaDataExtractor(graph=self.graph)
        self.checkEmpties = checkEmpties

    def isImage(self):
        return self.compositeMask is not None and self.compositeMask.isImage() or \
               self.donorMask is not None and self.donorMask.isImage()

    def getName(self):
        return '{} to {}'.format(self.source,self.target)

    def getSourceFileName(self):
        return self.graph.get_pathname(self.source)

    def getTargetFileName(self):
        return self.graph.get_pathname(self.target)

    def shapeChange(self):
        return (self.targetShape[0]-self.sourceShape[0], self.targetShape[1]-self.sourceShape[1])

    def compositeChange(self):
        return (self.targetShape[0]-self.compositeMask.mask.shape[0], self.targetShape[1]-self.compositeMask.mask.shape[1])

    def donorChange(self):
        return (self.sourceShape[0]-self.donorMask.mask.shape[0], self.sourceShape[1]-self.donorMask.mask.shape[1])

    def location(self):
        location = getValue(self.edge,'location',getValue(self.edge,'arguments.location',None))
        return toIntTuple(location) if location is not None and len(location) > 1 else (0,0)

    def rotation(self):
        return float(getValue(self.edge,'arguments.rotation','0.0'))

    def flip(self):
        return getValue(self.edge, 'arguments.flip direction')

    def transformMatrix(self):
        tm = getValue(self.edge,'arguments.transform matrix', getValue(self.edge,'transform matrix'))
        if tm is not None:
            return tool_set.deserializeMatrix(tm)
        return None

    def arguments(self):
        return getValue(self.edge,'arguments',{})

    def getVideoMetaExtractor(self):
        return self.meta_extractor

    def checkEmptyMask(self, composite,force=True):
        """

        :param composite:
        :param force:  ok empty
        :return:
        @type composite: CompositeImage
        """

        allowed_empties = [x.split(':') for x in getValue(self.edge, 'allowed_empties', [])]
        found = len([x for x in allowed_empties if allowed_empties[0] == composite.source and allowed_empties[1] == composite.target]) > 0
        composite.ok = not composite.isEmpty() or not self.checkEmpties or force or found
        return composite

    def getNodeFile(self):
        return self.meta_extractor.getNodeFile(self.source)

    def getMasksFromEdge(self, expect_types, channel=0, startTime=None, endTime=None):
        return self.meta_extractor.getMasksFromEdge(self.source, self.target, expect_types, channel=channel,
                                             startTime=startTime, endTime=endTime)

    def getExifOrientation(self):
        """

        :return: flip and rotate
        @rtype: (str, int)
        """
        return exif.rotateAmount(getOrientationForEdge(self.edge))

    def substitute(self,composite_image):
        """

        :param composite_image:
        :return:
        @param composite_image: CompositeImage
        """
        self.compositeMask = composite_image if self.isComposite else None
        self.donorMask = composite_image if not self.isComposite else None

    def warpMask(self, media_type=None):
        if self.isComposite:
            return self.compositeMask.create(self.meta_extractor.warpMask(self.compositeMask.videomasks,
                                                               source= self.source,
                                                               target= self.target,
                                                               expectedType=media_type if media_type is not None else self.compositeMask.media_type))
        elif self.donorMask is not None:
            return CompositeImage(self.donorMask.source,
                                  self.donorMask.target,
                                  self.donorMask.media_type if media_type is None else media_type,
                                  self.meta_extractor.warpMask(self.donorMask.videomasks,
                                                               self.target,
                                                               self.source,
                                                               inverse=True,
                                                               expectedType=media_type if media_type is not None else self.donorMask.media_type),
                                  issubstitute=self.donorMask.issubstitute)

    def frame_rate_check(self):
        if self.isImage():
            return
        if self.isComposite:
            self.compositeMask = self.compositeMask.create(
                                                self.meta_extractor.warpMask(self.compositeMask.videomasks,
                                                                             self.source,
                                                                             self.target,
                                                                              expectedType=self.compositeMask.media_type))
        elif self.donorMask is not None:
            self.donorMask = self.donorMask.create(
                                            self.meta_extractor.warpMask(self.donorMask.videomasks,
                                                                         self.target,
                                                                         self.source,
                                                                         inverse=True,
                                                                         expectedType=self.donorMask.media_type))

def segmentToVideoSegment (segment):
    return VideoSegment(video_tools.get_rate_from_segment(segment),
                         video_tools.get_start_time_from_segment(segment),
                         video_tools.get_start_frame_from_segment(segment),
                         video_tools.get_end_time_from_segment(segment),
                         video_tools.get_end_frame_from_segment(segment),
                         video_tools.get_frames_from_segment(segment),
                         video_tools.get_file_from_segment(segment),
                         video_tools.get_type_of_segment(segment),
                         video_tools.get_error_from_segment(segment))

def _compositeImageToVideoSegment(compositeImage):
    """

    :param compositeImage:
    :return:
    @type compositeImage: CompositeImage
    """
    if compositeImage is None or compositeImage.videomasks is None:
        return []
    return [segmentToVideoSegment(item) for item in compositeImage.videomasks]

def compositeMaskSetFromVideoSegment(videoSegments):
    """
    Convert Segments back to masks
    :param videoSegments:
    :return:
    @type videoSegments: list of VideoSegment
    """
    mask_set = []
    for seg in videoSegments:
        ms = video_tools.create_segment(rate=seg.rate,
                                        endtime=seg.endtime,
                                        endframe=seg.endframe,
                                        startframe=seg.startframe,
                                        starttime=seg.starttime,
                                        type=seg.media_type,
                                        frames=seg.frames,
                                        videosegment=seg.filename)
        mask_set.append(ms)
    return mask_set


def _guess_type(edge):
    """
    Backfill old journals.  New journals will have the type built into the videomasks.
    :param edge:
    :return:
    @type edge: dict
    """
    return 'audio' if edge['op'].find('Audio') >= 0 else 'video'


def _prepare_video_masks(meta_extractor,
                         video_masks,
                         media_type,
                         source,
                         target,
                         edge,
                         returnEmpty=True,
                         fillWithUserBoundaries=False,
                         operation=None,
                         issubstitute=False):
    """
    Remove empty videosegments, set the videosegment file names to full path names,
    set the media_type of the segment if missing.
    :param directory:
    :param video_masks:
    :param media_type:
    :param source:
    :param target:
    :param returnEmpty: If True, emoty masks (e.g. []) is permitted, otherwise return None
    :return: CompositeImage
    @rtype: CompositeImage
    @type operation: Operation
    """
    import copy

    def preprocess(func, edge, target_size, video_masks):
        return [func(mask,edge,target_size) for mask in video_masks]

    def donothing(mask, edge, targetsize):
        return mask

    def replace_with_dir(directory, video_masks):
        for mask in video_masks:
            mask_copy = copy.deepcopy(mask)
            video_tools.update_segment(mask_copy, type=video_tools.get_type_of_segment(mask_copy,default_value=media_type))
            if video_tools.get_file_from_segment( mask ) is not None:
                    vs = os.path.join(directory, os.path.split(video_tools.get_file_from_segment( mask ))[1])
                    if not os.path.exists(vs):
                        video_tools.drop_file_from_segment(mask_copy)
                    else:
                        video_tools.update_segment(mask_copy,videosegment=vs)
            yield mask_copy

    if len(video_masks) == 0:
        if not returnEmpty:
            return None
        if fillWithUserBoundaries:
            video_masks = video_tools.getMaskSetForEntireVideo(meta_extractor.getMetaDataLocator(source),
                                                 start_time = getValue(edge,'arguments.Start Time',
                                                                       defaultValue='00:00:00.000'),
                                                 end_time = getValue(edge,'arguments.End Time'),
                                                 media_types=[media_type])
    preprocess_func = donothing
    target_size = meta_extractor.getNodeSize(target)
    if operation is not None:
        preprocess_func_id = media_type + '_preprocess'
        if operation.maskTransformFunction is not None and preprocess_func_id in operation.maskTransformFunction:
            preprocess_func = graph_rules.getRule(operation.maskTransformFunction[preprocess_func_id])
    return None if len(video_masks) == 0 and not returnEmpty else \
         CompositeImage(source, target, media_type, [item for item in
                                                     preprocess(preprocess_func,
                                                                edge,
                                                                target_size,
                                                                replace_with_dir(meta_extractor.graph.dir, video_masks))],
                        issubstitute=issubstitute)



#====================================================================
#  Probe Edge Transforms
#====================================================================

def _apply_recapture_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    tm = buildState.transformMatrix()
    args = buildState.arguments()
    position_str = args['Position Mapping'] if 'Position Mapping' in args else None
    if position_str is not None and len(position_str) > 0:
        parts = position_str.split(':')
        left_box = tool_set.coordsFromString(parts[0])
        right_box = tool_set.coordsFromString(parts[1])
        angle = int(float(parts[2]))
        if right_box[3] > buildState.targetShape[0] or right_box[2] > buildState.targetShape[1]:
            logging.getLogger('maskgen').warn(
                'The mask for recapture edge with file {} has an incorrect size'.format(buildState.edge['maskname']))
            right_box = (right_box[0], right_box[1], buildState.targetShape[1], buildState.targetShape[0])
        if left_box[3] > buildState.sourceShape[0] or left_box[2] > buildState.sourceShape[1]:
            logging.getLogger('maskgen').warn(
                'The mask for recapture edge with file {} has an incorrect size'.format(
                        buildState.edge['maskname']))
            left_box = (left_box[0], left_box[1], buildState.sourceShape[1], buildState.sourceShape[0])
        if buildState.isComposite:
            mask = buildState.compositeMask.mask
            expectedShape= buildState.targetShape
            newMask = np.zeros(expectedShape)
            clippedMask = mask[left_box[1]:left_box[3], left_box[0]:left_box[2]]
            angleFactor = round(float(angle) / 90.0)
            if abs(angleFactor) > 0:
                mask = np.rot90(clippedMask, int(angleFactor)).astype('uint8')
                angle = angle - int(angleFactor * 90)
            else:
                mask = clippedMask
            expectedPasteSize = ((right_box[3] - right_box[1]), (right_box[2] - right_box[0]))
            mask = tool_set.applyResizeComposite(mask, (expectedPasteSize[0], expectedPasteSize[1]))
            newMask[right_box[1]:right_box[3], right_box[0]:right_box[2]] = mask
            if angle != 0:
                center = (
                    right_box[1] + (right_box[3] - right_box[1]) / 2, right_box[0] + (right_box[2] - right_box[0]) / 2)
                mask = tool_set.applyRotateToCompositeImage(newMask, angle, center)
            else:
                mask = newMask.astype('uint8')
            return buildState.compositeMask.create(
                                  mask.astype('uint8'))
        elif buildState.donorMask is not None:
            mask = buildState.donorMask.mask
            expectedShape = buildState.sourceShape
            expectedPasteShape = ((left_box[3] - left_box[1]), (left_box[2] - left_box[0]))
            newMask = np.zeros(expectedShape)
            ninetyRotate = 0
            angleFactor = round(float(angle) / 90.0)
            if abs(angleFactor) > 0:
                ninetyRotate = int(angleFactor)
                angle = angle - int(angleFactor * 90)
            if angle != 0:
                center = (
                    right_box[1] + (right_box[3] - right_box[1]) / 2, right_box[0] + (right_box[2] - right_box[0]) / 2)
                mask = tool_set.applyRotateToCompositeImage(mask, -angle, center)
            clippedMask = mask[right_box[1]:right_box[3], right_box[0]:right_box[2]]
            if ninetyRotate != 0:
                clippedMask = np.rot90(clippedMask, -ninetyRotate).astype('uint8')
            newMask[left_box[1]:left_box[3], left_box[0]:left_box[2]] = tool_set.applyResizeComposite(clippedMask, (expectedPasteShape[0], expectedPasteShape[1]))
            return  buildState.donorMask.create(
                                  newMask.astype('uint8'))

    if buildState.isComposite:
        mask = buildState.compositeMask.mask
        if tm is not None:
            mask = tool_set.applyTransformToComposite(mask,
                                                     buildState.edgeMask,
                                                     tm,
                                                     shape=buildState.targetShape,
                                                     returnRaw=True)
        elif buildState.targetShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.targetShape)
        return buildState.compositeMask.create(mask)
    elif buildState.donorMask is not None:
        mask = buildState.donorMask.mask
        if tm is not None:
            mask = tool_set.applyTransform(mask,
                                          mask=buildState.edgeMask,
                                          transform_matrix=tm,
                                          invert=True,
                                          shape=buildState.sourceShape,
                                          returnRaw=True)
        elif buildState.sourceShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.sourceShape)
        return buildState.donorMask.create(mask)
    return CompositeImage(buildState.source,
                          buildState.target,
                          'image',
                          buildState.edgeMask)


def recapture_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return buildState.checkEmptyMask(_apply_recapture_transform(buildState))

def crop_resize_transform(buildState):
    """

    :param buildState:
    :return:
    @type buildState: BuildState
    """
    # only want the mask overlayed on the crop area.
    args = buildState.arguments()
    if 'Position Mapping' in args:
        return recapture_transform(buildState)

    if buildState.isComposite:
        location = buildState.location()
        args = buildState.arguments()
        width = int(args['crop width'])
        height =  int(args['crop height'])
        crop_mask = buildState.compositeMask.mask[location[0]:location[0]+height, location[1]:location[1]+width]
        return  buildState.compositeMask.create(
                              tool_set.applyResizeComposite(crop_mask, buildState.targetShape))
    else:
        location = buildState.location()
        args = buildState.arguments()
        width = int(args['crop width'])
        height = int(args['crop height'])
        crop_shape = (height,width)
        crop_mask = tool_set.applyResizeComposite(buildState.donorMask.mask, crop_shape)
        final_mask = np.zeros((buildState.sourceShape)).astype('uint8')
        # replace into cropped location
        final_mask[location[0]:location[0]+height, location[1]:location[1]+width] = crop_mask
        return buildState.donorMask.create(final_mask)

def resize_analysis(analysis, img1, img2, mask=None, linktype=None, arguments=dict(), directory='.'):
    from PIL import Image
    tool_set.globalTransformAnalysis(analysis, img1, img2, mask=mask, arguments=arguments)
    sizeChange  = toIntTuple(analysis['shape change']) if 'shape change' in analysis else (0, 0)
    canvas_change = (sizeChange != (0, 0) and ('interpolation' not in arguments or
                     arguments['interpolation'].lower().find('none') >= 0))
    if not canvas_change or getValue(arguments,'homography',defaultValue='None') != 'None':
        mask2 = mask.resize(img2.size, Image.ANTIALIAS) if mask is not None and img1.size != img2.size else mask
        matrix, matchCount = tool_set.__sift(img1, img2, mask1=mask, mask2=mask2, arguments=arguments)
        analysis['transform matrix'] = tool_set.serializeMatrix(matrix)

def resize_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    import os
    shapeChange = buildState.shapeChange()
    location =buildState.location()
    args = buildState.arguments()
    tm = buildState.transformMatrix()
    canvas_change = (shapeChange != (0, 0) and 'interpolation' in args and \
                     args['interpolation'].lower().find('none')>=0 and \
                     tm is None)
    if location != (0, 0):
        shapeChange = (-location[0], -location[1]) if shapeChange == (0, 0) else shapeChange
    if buildState.isComposite:
        mask = buildState.compositeMask.mask
        expectedShape = (mask.shape[0] + shapeChange[0], mask.shape[1] + shapeChange[1])
        if canvas_change:
            newRes = np.zeros(expectedShape).astype('uint8')
            upperBound = (min(mask.shape[0] + location[0], newRes.shape[0]),
                          min(mask.shape[1] + location[1], newRes.shape[1]))
            newRes[location[0]:upperBound[0], location[1]:upperBound[1]] = mask[0:(upperBound[0] - location[0]),
                                                                           0:(upperBound[1] - location[1])]
            mask = newRes
        else:
            if tm is not None:
                mask = tool_set.applyTransformToComposite(mask, buildState.edgeMask, tm,
                                                         shape= buildState.targetShape, returnRaw=shapeChange != (0, 0))
            elif getValue(buildState.edge,'inputmaskname') is not None and shapeChange == (0, 0):
                inputmask = openImageFile(os.path.join(buildState.directory, buildState.edge['inputmaskname']))
                if inputmask is not None:
                    inputmaskarray = inputmask.to_mask().to_array()
                    mask = move_pixels(inputmaskarray, 255 - buildState.edgeMask, mask, isComposite=True)
        if buildState.targetShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask,  buildState.targetShape)
        return buildState.compositeMask.create(mask)
    elif buildState.donorMask is not None:
        mask = buildState.donorMask.mask
        if canvas_change:
            upperBound = (
                min(buildState.sourceShape[0] + location[0], mask.shape[0]), min(buildState.sourceShape[1] + location[1], mask.shape[1]))
            mask = mask[location[0]:upperBound[0], location[1]:upperBound[1]]
        else:
            if tm is not None:
                mask = tool_set.applyTransform(mask, mask=buildState.edgeMask, transform_matrix=tm,
                                              invert=True,  shape=buildState.sourceShape, returnRaw=shapeChange != (0, 0))
            elif getValue(buildState.edge,'inputmaskname') is not None and shapeChange == (0, 0):
                inputmask = openImageFile(os.path.join(buildState.directory, buildState.edge['inputmaskname']))
                if inputmask is not None:
                    inputmaskarray = inputmask.to_mask().to_array()
                    mask = move_pixels(255 - buildState.edgeMask, inputmaskarray, mask)
        if buildState.sourceShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.sourceShape)
        return buildState.donorMask.create(mask)
    return CompositeImage(buildState.source,
                          buildState.target,
                          'image',
                          buildState.edgeMask)

def video_resize_helper(buildState, criteria_function):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """

    canvas_change = criteria_function(buildState)
    if buildState.isComposite:
        expectedSize = buildState.getVideoMetaExtractor().getNodeSize( buildState.target)
        if canvas_change:
            return buildState.compositeMask.create(
                                  video_tools.resizeMask(buildState.compositeMask.videomasks, expectedSize))
        return buildState.compositeMask
    elif buildState.donorMask is not None:
        expectedSize = buildState.getVideoMetaExtractor().getNodeSize(buildState.source)
        if canvas_change:
            return buildState.donorMask.create(
                                  video_tools.resizeMask(buildState.donorMask.videomasks, expectedSize))
        return buildState.donorMask
    return None

def video_resize_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    def vrt_criteria(buildState):
        shapeChange = buildState.shapeChange()
        return shapeChange != (0, 0)
    return video_resize_helper(buildState, vrt_criteria)

def median_stacking(buildState):
    if buildState.isComposite:
        return CompositeImage(buildState.source,
                             buildState.target,
                              'image',
                              video_tools.extractMask(buildState.compositeMask.videomasks,
                                       getValue(buildState.edge, 'arguments.Frame Time',
                                                                 defaultValue='00:00:00.000')))
    else:
        return CompositeImage(buildState.source,
                            buildState.target,
                            buildState.getVideoMetaExtractor().getNodeFileType(buildState.source),
                              video_tools.inverse_intersection_for_mask(buildState.donorMask,
                                                                        getValue(buildState.edge, 'videomasks', [])))

def rotate_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    shapeChange = buildState.shapeChange()
    args = buildState.arguments()
    rotation = buildState.rotation()
    tm = buildState.transformMatrix()
    rotation = rotation if rotation is not None and abs(rotation) > 0.00001 else 0
    local = (args['local'] == 'yes') if 'local' in args else False
    if not local and shapeChange != (0, 0) and abs(int(round(rotation))) % 90 == 0:
        tm = None
    if buildState.donorMask is not None:
        if tm is not None:
            mask = tool_set.applyTransform(buildState.donorMask.mask,
                                          mask=buildState.edgeMask,
                                          transform_matrix=tm,
                                          invert=True,
                                          returnRaw=False)
        else:
            mask = tool_set.__rotateImage(-rotation, buildState.donorMask.mask,
                                         expectedDims=buildState.sourceShape, cval=0)
        return buildState.donorMask.create(mask)
    elif buildState.isComposite:
        if tm is not None:
            mask = tool_set.applyTransformToComposite(buildState.compositeMask.mask,
                                                     buildState.edgeMask,
                                                     tm)
        else:
            mask = tool_set.applyRotateToComposite(rotation,
                                                  buildState.compositeMask.mask,
                                                  buildState.edgeMask,
                                                  buildState.targetShape,
                                                  local=local)
    return buildState.compositeMask.create(mask)


def video_copy_exif(buildState):
    """
    Applicable to video
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    buildState.frame_rate_check()
    orientrotate = buildState.getVideoMetaExtractor().get_video_orientation_change(
        buildState.source, buildState.target)
    if buildState.isComposite:
        if orientrotate == 0:
            return buildState.compositeMask
        targetSize = buildState.getVideoMetaExtractor().getNodeSize(buildState.target)
        return buildState.compositeMask.create(
                              video_tools.rotateMask(-orientrotate, buildState.compositeMask.videomasks,
                                                     expectedDims=(targetSize[1],targetSize[0]), cval=0))
    elif buildState.donorMask is not None:
        targetSize = buildState.getVideoMetaExtractor().getNodeSize(buildState.source)
        if orientrotate == 0:
            return buildState.donorMask
        return buildState.donorMask.create(
                              video_tools.rotateMask(orientrotate, buildState.donorMask.videomasks,
                                                     expectedDims=(targetSize[1],targetSize[0]), cval=0))
    return None

def video_rotate_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    buildState.frame_rate_check()
    rotation = buildState.rotation()
    rotation = rotation if rotation is not None and abs(rotation) > 0.00001 else 0
    if buildState.isComposite:
        targetSize = buildState.getVideoMetaExtractor().getNodeSize(buildState.target)
        return buildState.compositeMask.create(
                              video_tools.rotateMask(rotation, buildState.compositeMask.videomasks,
                                                     expectedDims=(targetSize[1],targetSize[0]), cval=0))
    elif buildState.donorMask is not None:
        targetSize = buildState.getVideoMetaExtractor().getNodeSize(buildState.source)
        return buildState.donorMask.create(
                              video_tools.rotateMask(-rotation, buildState.donorMask.videomasks,
                                                     expectedDims=(targetSize[1],targetSize[0]), cval=0))
    return None


def median_stacking_preprocess(mask, edge, target_size):
    return video_tools.resizeMask([mask], target_size)[0]

def image_selection_preprocess(mask, edge,target_size ):
    """
       :param mask:
       :param edge
       :return:
       @type mask: dict
       """
    return mask

def select_cut_frames_preprocess(mask, edge, target_size):
    """
    Creates the neighbor indicators...since can register frames cut from the target(they are done).

    :param mask:
    :param edge
    :return:
    @type mask: dict
    """
    mask = mask.copy()
    if 'videomasks' in mask:
        mask.pop('videomasks')
    fps = 1000.0 / video_tools.get_rate_from_segment(mask)
    video_tools.update_segment(mask,
                               startframe=video_tools.get_start_frame_from_segment(mask) - 1,
                               endframe=video_tools.get_start_frame_from_segment(mask),
                               starttime=video_tools.get_start_time_from_segment(mask) - fps,
                               endtime=video_tools.get_start_time_from_segment(mask))
    if video_tools.get_start_frame_from_segment(mask) < 0:
        video_tools.update_segment(mask,
                                   startframe=1,
                                   starttime=0.0,
                                   frames=1)
    return mask

def select_crop_frames_preprocess(mask, edge, target_size):
    """
    Whole video
    :param mask:
    :param edge
    :return:
    @type mask: dict
    """
    new_mask = mask.copy()
    if 'videomasks' in new_mask:
        new_mask.pop('videomasks')
    fps = 1000.0 / video_tools.get_rate_from_segment (mask)
    video_tools.update_segment(new_mask,
                   startframe=1,
                   starttime=0.0,
                   endframe=video_tools.get_frames_from_segment(mask) - 1,
                   endtime=video_tools.get_start_time_from_segment(mask) + fps * (video_tools.get_frames_from_segment(mask) - 1))
    return new_mask

def select_cut_frames(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        return buildState.compositeMask.create(
                              video_tools.dropFramesFromMask(buildState.getMasksFromEdge(
                                  ['audio','video']),
                                  buildState.compositeMask.videomasks))
    elif buildState.donorMask is not None:
        return buildState.donorMask.create(
                              video_tools.insertFramesToMask(buildState.getMasksFromEdge(
                                  ['audio','video']),
                                buildState.donorMask.videomasks))
    return None


def select_crop_frames(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    frame_bounds = buildState.getMasksFromEdge(['audio','video'])
    masks_to_use = buildState.compositeMask if buildState.isComposite else buildState.donorMask
    video_masks = [vm for vm in masks_to_use.videomasks if video_tools.get_type_of_segment(vm) == 'video']
    audio_masks = [vm for vm in masks_to_use.videomasks if video_tools.get_type_of_segment(vm) == 'audio']
    video_bound = [frame_bound for frame_bound in frame_bounds if video_tools.get_type_of_segment(frame_bound) == 'video']
    audio_bound = [frame_bound for frame_bound in frame_bounds if video_tools.get_type_of_segment(frame_bound) == 'audio']

    def setbound(bound,max_mask):
        fps = 1000.0 / video_tools.get_rate_from_segment(bound[0])
        start_vid = video_tools.create_segment(starttime=0,
                                                      startframe=1,
                                                      endtime=video_tools.get_start_time_from_segment(bound[0]) - fps,
                                                      endframe= video_tools.get_start_frame_from_segment(bound[0])  - 1,
                                                      rate=video_tools.get_rate_from_segment(bound[0]),
                                                      type=video_tools.get_type_of_segment(bound[0]))

        end_vid = video_tools.create_segment(starttime=video_tools.get_end_time_from_segment(bound[0]) + fps,
                                                      startframe=video_tools.get_end_frame_from_segment(bound[0]) + 1,
                                                      endtime=video_tools.get_end_time_from_segment(max_mask),
                                                      endframe=video_tools.get_end_frame_from_segment(max_mask),
                                                      rate=video_tools.get_rate_from_segment(bound[0]),
                                                      type=video_tools.get_type_of_segment(bound[0]))
        return start_vid, end_vid


    def run_composite(bound, masks):
        if len(bound) > 0 and len(masks) > 0:
            max_media = np.argmax([video_tools.get_end_frame_from_segment(vm) for vm in masks])
            start, end = setbound(bound, masks[max_media])
            return video_tools.dropFramesFromMask([start],
                                                          video_tools.dropFramesFromMask([end],
                                                                                         buildState.compositeMask.videomasks))
        return []

    def run_donor(bound, masks):
        if len(bound) > 0 and len(masks) > 0:
            max_media = np.argmax([video_tools.get_end_frame_from_segment(vm) for vm in masks])
            start, end = setbound(bound, masks[max_media])
            return video_tools.insertFramesToMask([start],buildState.donorMask.videomasks)
        return []

    if buildState.isComposite:
        results = run_composite(video_bound,video_masks)
        results.extend(run_composite(audio_bound, audio_masks))
        return buildState.compositeMask.create(results)
    elif buildState.donorMask is not None:
        results = run_donor(video_bound, video_masks)
        results.extend(run_composite(audio_bound, audio_masks))
        return buildState.donorMask.create(results)
    return None


def replace_audio(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    channel_name = getValue(buildState.arguments(), 'Stream', 'all')
    #TODO: filter masks based on channel
    masks = buildState.compositeMask.videomasks if buildState.isComposite else buildState.donorMask.videomasks

    new_masks = []
    new_masks = [mask_segment for mask_segment in masks if video_tools.get_type_of_segment(mask_segment) != 'audio']

    if buildState.isComposite:
        return buildState.compositeMask.create(new_masks)
    else:
        return buildState.donorMask

def copy_add_audio(buildState):
    start_time = getValue(buildState.edge,'arguments.Insertion Time')
    start_time_value = tool_set.getMilliSecondsAndFrameCount(start_time)
    copy_start_time = tool_set.getMilliSecondsAndFrameCount(getValue(buildState.edge, 'arguments.Copy Start Time'))
    copy_end_time = tool_set.getMilliSecondsAndFrameCount(getValue(buildState.edge,'arguments.Copy End Time'))
    end_time = (start_time_value[0] + (copy_end_time[0] - copy_start_time[0]), 0) if copy_end_time is not None else None
    return add_audio(buildState, start_time=start_time, end_time=end_time)

def add_audio(buildState, start_time = None, end_time=None):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    buildState.substitute(buildState.warpMask('video'))
    if buildState.isComposite:
        # if there is a match the source and target, then this is 'seeded' composite mask
        # have to wonder if this is necessary, but I suppose it gives the transform
        # an opportunity to make adjustments for composite.

        if buildState.compositeMask.source != buildState.source and \
                        buildState.compositeMask.target != buildState.target:
            args = buildState.arguments()
            if 'add type' in args and args['add type'] == 'insert':
                return buildState.compositeMask.create(
                                      video_tools.insertFrames(buildState.getMasksFromEdge(
                                          ['audio'],
                                          startTime=start_time,
                                          endTime=end_time),
                                          buildState.compositeMask.videomasks,
                                          expectedType='audio'))
            return buildState.compositeMask.create(
                                  video_tools.dropFramesWithoutMask(buildState.getMasksFromEdge(
                                      ['audio'],
                                      startTime=start_time,
                                      endTime=end_time),
                                      buildState.compositeMask.videomasks,
                                      keepTime=True,
                                      expectedType='audio'))
        return buildState.compositeMask
    # in donor case, the donor was already trimmed
    else:
        args = buildState.arguments()
        if 'add type' in args and args['add type'] == 'insert':
            return buildState.donorMask.create(
                video_tools.dropFramesWithoutMask(buildState.getMasksFromEdge(
                    ['audio'],
                    startTime=start_time,
                    endTime=end_time),
                    buildState.donorMask.videomasks,
                    expectedType='audio'))
        return buildState.donorMask.create(
            video_tools.removeIntersectionOfMaskSets(buildState.donorMask.videomasks,
                                     buildState.getMasksFromEdge(
                                          ['audio'],
                                          startTime=start_time,
                                          endTime=end_time
                                      )))


def delete_audio(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        if buildState.compositeMask.source != buildState.source and \
                        buildState.compositeMask.target != buildState.target:
            return buildState.compositeMask.create(
                                  video_tools.dropFramesWithoutMask(buildState.getMasksFromEdge(
                                      ['audio']),
                                      buildState.compositeMask.videomasks,
                                      expectedType='audio'))
        return buildState.compositeMask
    # in donor case, need to add the deleted frames back
    else:
        return buildState.donorMask.create(video_tools.insertFrames(buildState.getMasksFromEdge(
            ['audio']),
            buildState.donorMask.videomasks,
            expectedType='audio'))


def copy_paste_frames(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    startTime = getValue(buildState.edge,'arguments.Dest Paste Time')
    framesCount = getValue(buildState.edge,'arguments.Number of Frames')
    endTime = addFrame(getMilliSecondsAndFrameCount(startTime, defaultValue=(0,0)),framesCount)

    args = buildState.arguments()
    if 'add type' not in args or args['add type'] == 'insert':
        if buildState.isComposite:
            if buildState.compositeMask.source != buildState.source and \
                            buildState.compositeMask.target != buildState.target:
                return buildState.compositeMask.create(
                                      video_tools.insertFramesToMask(buildState.getMasksFromEdge(
                                          ['video'],
                                          startTime=startTime,
                                          endTime=endTime),
                                          buildState.compositeMask.videomasks))
            return buildState.compositeMask
        elif buildState.donorMask is not None:
            return buildState.donorMask.create(
                                  video_tools.dropFramesFromMask(buildState.getMasksFromEdge(
                                      ['video'],
                                      startTime=startTime,
                                      endTime=endTime),
                                      buildState.donorMask.videomasks))
        return None
    else:
        # overlay case, trim masks
        if buildState.isComposite:
            if buildState.compositeMask.source != buildState.source and \
                            buildState.compositeMask.target != buildState.target:
                return  buildState.compositeMask.create(
                                      video_tools.dropFramesFromMask(buildState.getMasksFromEdge(
                                          ['video'],
                                          startTime=startTime,
                                          endTime=endTime
                                      ),
                                          buildState.compositeMask.videomasks,
                                          keepTime=True))
            return buildState.compositeMask
        else:
            # the donor uses some of the pasted data from somewhere else
            # so remove that part
            donorMask= video_tools.dropFramesFromMask(buildState.getMasksFromEdge(
                                      ['video'],
                                      startTime=startTime,
                                      endTime=endTime),
                                      buildState.donorMask.videomasks,
                                  keepTime=True)
            # that 'somewhere else' is still part of the donor, so add it back
            startTime = getValue(buildState.edge, 'arguments.Select Start Time')
            endTime = addFrame(getMilliSecondsAndFrameCount(startTime, defaultValue=(0, 0)), framesCount)
            return buildState.donorMask.create(
                                  video_tools.removeIntersectionOfMaskSets(buildState.getMasksFromEdge(
                                          ['video'],
                                          startTime=startTime,
                                          endTime=endTime
                                      ),donorMask))


def _paste_add(buildState,media_types):
    """
       :param buildState:
       :return: updated composite mask
       @type buildState: BuildState
       @type media_types: list of str
       @rtype: CompositeImage
       """
    args = buildState.arguments()
    if 'add type' in args and args['add type'] == 'insert':
        if buildState.isComposite:
            if buildState.compositeMask.source != buildState.source and \
                            buildState.compositeMask.target != buildState.target:
                return buildState.compositeMask.create(
                                      video_tools.insertFramesToMask(buildState.getMasksFromEdge(
                                          media_types),
                                          buildState.compositeMask.videomasks))
            return buildState.compositeMask
        elif buildState.donorMask is not None:
            return buildState.donorMask.create(
                                  video_tools.dropFramesFromMask(buildState.getMasksFromEdge(
                                      media_types),
                                      buildState.donorMask.videomasks))
        return None
    else:
        # overlay case, trim masks
        if buildState.isComposite:
            if buildState.compositeMask.source != buildState.source and \
                            buildState.compositeMask.target != buildState.target:
                return buildState.compositeMask.create(
                                      video_tools.dropFramesFromMask(buildState.getMasksFromEdge(
                                          media_types),
                                          buildState.compositeMask.videomasks,
                                          keepTime=True))
            return buildState.compositeMask
        else:
            return buildState.donorMask.create(
                                  video_tools.dropFramesFromMask(buildState.getMasksFromEdge(
                                      media_types),
                                      buildState.donorMask.videomasks,
                                      keepTime=True))

def paste_add_frames(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return _paste_add(buildState,['video'])

def paste_add_audio_frames(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return _paste_add(buildState,['audio'])

def time_warp_frames(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        if buildState.compositeMask.source != buildState.source and \
                        buildState.compositeMask.target != buildState.target:
            return buildState.compositeMask.create(
                                  video_tools.insertFramesToMask(buildState.getMasksFromEdge(
                                      ['video']),
                                      buildState.compositeMask.videomasks))
        return buildState.compositeMask
    elif buildState.donorMask is not None:
        return buildState.donorMask.create(
                              video_tools.dropFramesFromMask(buildState.getMasksFromEdge(
                                  ['video']),
                                  buildState.donorMask.videomasks))
    return None

def reverse_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    buildState.frame_rate_check()
    if buildState.isComposite:
        if buildState.compositeMask.source != buildState.source and \
                        buildState.compositeMask.target != buildState.target:
            return buildState.compositeMask.create(
                                  video_tools.reverseMasks(buildState.getMasksFromEdge(
                                                                            ['video','audio']),
                                                           buildState.compositeMask.videomasks))
        return buildState.compositeMask
    elif buildState.donorMask is not None:
        return buildState.donorMask.create(
                              video_tools.reverseMasks(buildState.getMasksFromEdge(
                                                                        ['video','audio']),
                                                       buildState.donorMask.videomasks))
    return None

def time_warp_audio(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        if buildState.compositeMask.source != buildState.source and \
                        buildState.compositeMask.target != buildState.target:
            return buildState.compositeMask.create(
                                  video_tools.insertFramesToMask(buildState.getMasksFromEdge(
                                                                                  ['audio']),
                                                                 buildState.compositeMask.videomasks))
        return buildState.compositeMask
    elif buildState.donorMask is not None:
        return buildState.donorMask.create(
                              video_tools.dropFramesFromMask(buildState.getMasksFromEdge(
                                  ['audio']),
                                  buildState.donorMask.videomasks))
    return None

def select_remove(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        mask = tool_set.applyMask(buildState.compositeMask.mask, buildState.edgeMask)
        if buildState.targetShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.targetShape)
        return buildState.checkEmptyMask(buildState.compositeMask.create(mask),force=False)
    else:
        mask = buildState.donorMask.mask
        # res is the donor mask
        # edgeMask may be the overriding mask from a PasteSplice, thus in the same shape
        # The transfrom will convert to the target mask size of the donor path.
        # res = tool_set.applyMask(donorMask, edgeMask)
        if mask is not None and  buildState.sourceShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.sourceShape)
        return buildState.donorMask.create(mask)


def crop_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    location = buildState.location()
    if buildState.isComposite:
        mask = buildState.compositeMask.mask
        mask = mask[location[0]:buildState.targetShape[0]+location[0], location[1]:buildState.targetShape[1]+location[1]]
        return buildState.checkEmptyMask(
                              buildState.compositeMask.create(mask), force=True)
    elif buildState.donorMask is not None:
        mask = buildState.donorMask.mask
        expectedShape = buildState.sourceShape
        newRes = np.zeros(expectedShape).astype('uint8')
        upperBound = (mask.shape[0] + location[0], mask.shape[1] + location[1])
        newRes[location[0]:upperBound[0], location[1]:upperBound[1]] = mask[0:(upperBound[0] - location[0]),
                                                                       0:(upperBound[1] - location[1])]
        mask = newRes
        if expectedShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, expectedShape)
        return buildState.donorMask.create(mask)
    return CompositeImage(buildState.source,
                              buildState.target,
                              'image',
                              buildState.edgeMask)


def video_crop_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    buildState.frame_rate_check()
    targetSize = buildState.getVideoMetaExtractor().getNodeSize(buildState.target)
    sourceSize = buildState.getVideoMetaExtractor().getNodeSize(buildState.source)
    location = buildState.location()
    if buildState.isComposite:
        expectedSize = targetSize
        return buildState.compositeMask.create(
                              video_tools.cropMask(buildState.compositeMask.videomasks,
                                                   (location[0], location[1], expectedSize[1], expectedSize[0])))
    elif buildState.donorMask is not None:
        expectedSize = sourceSize
        upperBound = (min(targetSize[1],sourceSize[1] + location[0]),
                      min(targetSize[0], sourceSize[0] + location[1]))
        return buildState.donorMask.create(
                              video_tools.insertMask(
                                  buildState.donorMask.videomasks,
                                  (location[0], location[1], upperBound[0], upperBound[1]),
                                  expectedSize))
    return None

def seam_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    from functools import partial
    openImageFunc = partial(openImageMaskFile,buildState.directory)
    from maskgen.algorithms.seam_carving import MaskTracker
    sizeChange = buildState.shapeChange()
    col_adjust = getValue(buildState.edge, 'arguments.column adjuster')
    row_adjust = getValue(buildState.edge, 'arguments.row adjuster')
    apply_mask = getValue(buildState.edge, 'argments.apply mask','no')
    mask_type = getValue(buildState.edge, 'argments.inputmasktype', 'color')
    diffMask = getValue(buildState.edge, 'arguments.plugin mask',
                        defaultValue=buildState.edgeMask,
                        convertFunction=openImageFunc)

    if col_adjust is not None and row_adjust is not None:
        targetImage = buildState.graph.get_image(buildState.target)[0]
        mask_tracker = MaskTracker((targetImage.size[1], targetImage.size[0]))
        mask_tracker.read_adjusters(os.path.join(buildState.directory,row_adjust),os.path.join(buildState.directory,col_adjust))
        if buildState.isComposite:
            return buildState.compositeMask.create(
                               mask_tracker.move_pixels(buildState.compositeMask.mask))
        else:
            mask_tracker.set_dropped_mask(diffMask)
            return buildState.donorMask.create(
                              mask_tracker.invert_move_pixels(buildState.donorMask.mask))

    # if 'skip'
    matchx = sizeChange[0] == 0
    matchy = sizeChange[1] == 0
    res = None
    transformMatrix = buildState.transformMatrix()
    if (matchx and not matchy) or (not matchx and matchy):
        if buildState.isComposite:
            # left over from the prior algorithms.  to be removed.
            res = tool_set.carveMask(buildState.compositeMask.mask, diffMask, buildState.targetShape)
        elif buildState.donorMask is not None:
            # Need to think through this some more.
            # Seam carving essential puts pixels back.
            # perhaps this is ok, since the resize happens first and then the cut of the removed pixels
            res = tool_set.applyMask(buildState.donorMask.mask, diffMask)
            if transformMatrix is not None:
                res = cv2.warpPerspective(res, transformMatrix,
                                          (buildState.sourceShape[1], buildState.sourceShape[0]),
                                          flags=cv2.WARP_INVERSE_MAP,
                                          borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype('uint8')
            # need to use target size since the expected does ot align with the donor paths.
            if buildState.sourceShape != res.shape:
                res =tool_set.applyResizeComposite(res, buildState.sourceShape)

    elif buildState.donorMask is not None or buildState.compositeMask is not None:
        res = buildState.compositeMask.mask if buildState.compositeMask is not None else buildState.donorMask.mask
        res = tool_set.applyInterpolateToCompositeImage(res,
                                                        ImageWrapper(buildState.source) if type(
                                                            buildState.source) not in [
                                                                                               str, unicode] else
                                                        buildState.graph.get_image(buildState.source)[0],
                                                        ImageWrapper(buildState.target) if type(
                                                            buildState.target) not in [
                                                                                               str, unicode] else
                                                        buildState.graph.get_image(buildState.target)[0],
                                                        diffMask,
                                                        inverse=buildState.donorMask is not None,
                                                        arguments=buildState.arguments(),
                                                        defaultTransform=transformMatrix,
                                                        withMask=apply_mask == 'yes' and mask_type == 'keep')
    if res is None or len(np.unique(res)) == 1:
        return scale_transform(buildState)
    return buildState.compositeMask.create(res) if buildState.isComposite else \
           buildState.donorMask.create(res)


def warp_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return composite_transform(buildState, withMask = True)

def composite_transform(buildState, withMask = False):
    """
        :param buildState:
        :return: updated composite mask
        @type buildState: BuildState
        @rtype: CompositeImage
        """
    tm = buildState.transformMatrix()
    masktowarp = buildState.compositeMask.mask if buildState.isComposite else buildState.donorMask.mask
    res = tool_set.applyInterpolateToCompositeImage(masktowarp,
                                                    ImageWrapper(buildState.source) if type(buildState.source) not in [
                                                        str, unicode] else
                                                    buildState.graph.get_image(buildState.source)[0],
                                                    ImageWrapper(buildState.target) if type(buildState.target) not in [
                                                        str, unicode] else
                                                    buildState.graph.get_image(buildState.target)[0],
                                                    buildState.edgeMask,
                                                    inverse=not buildState.isComposite,
                                                    arguments=buildState.arguments(),
                                                    defaultTransform=tm,
                                                    withMask=withMask)
    if res is None or len(np.unique(res)) == 1:
        return scale_transform(buildState)
    return buildState.compositeMask.create(res) if buildState.isComposite else \
        buildState.donorMask.create(res)

def video_flip_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    buildState.frame_rate_check()
    args = buildState.arguments()
    flip = args['flip direction'] if 'flip direction' in args else None
    if buildState.isComposite:
        expectedSize = buildState.getVideoMetaExtractor().getNodeSize(buildState.target)
        return buildState.compositeMask.create(
                              video_tools.flipMask(buildState.compositeMask.videomasks, expectedSize, flip))
    elif buildState.donorMask is not None:
        expectedSize = buildState.getVideoMetaExtractor().getNodeSize(buildState.source)
        return buildState.donorMask.create(
                              video_tools.flipMask(buildState.donorMask.videomasks, expectedSize, flip))
    return buildState.donorMask


def move_pixels(frommask, tomask, image, isComposite=False):
    lowerm, upperm = tool_set.boundingRegion(frommask)
    lowerd, upperd = tool_set.boundingRegion(tomask)
    # if lowerm == lowerd:
    #    M = cv2.getAffineTransform(np.asarray([
    #                                                [upperm[0], lowerm[1]],
    #                                                [upperm[0], upperm[1]],
    #                                                [lowerm[0], upperm[1]]]
    #                                               ).astype(
    #        'float32'),
    #       np.asarray([
    #                   [upperd[0], lowerd[1]],
    #                   [upperd[0], upperd[1]],
    #                    [lowerd[0], upperd[1]]]).astype(
    #            'float32'))
    #    if isComposite:
    #        transformedImage = tool_set.applyAffineToComposite(image, M, tomask.shape)
    #        transformedImage = transformedImage.astype('uint8')
    #    else:
    #        transformedImage = cv2.warpAffine(image, M, (tomask.shape[1], tomask.shape[0]))
    #        transformedImage = transformedImage.astype('uint8')
    #    return transformedImage

    M = cv2.getPerspectiveTransform(np.asarray([[lowerm[0], lowerm[1]],
                                                [upperm[0], lowerm[1]],
                                                [upperm[0], upperm[1]],
                                                [lowerm[0], upperm[1]]]
                                               ).astype(
        'float32'),
        np.asarray([[lowerd[0], lowerd[1]],
                    [upperd[0], lowerd[1]],
                    [upperd[0], upperd[1]],
                    [lowerd[0], upperd[1]]]).astype(
            'float32'))

    if isComposite:
        transformedImage = tool_set.applyPerspectiveToComposite(image, M, tomask.shape)
        transformedImage = transformedImage.astype('uint8')
    else:
        transformedImage = cv2.warpPerspective(image, M, (tomask.shape[1], tomask.shape[0]))
        transformedImage = transformedImage.astype('uint8')
    return transformedImage


def move_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    import os
    returnRaw = False
    try:
        inputmask = \
            openImageFile(os.path.join(buildState.directory, buildState.edge['inputmaskname'])).to_mask().invert().to_array() \
                if 'inputmaskname' in buildState.edge and buildState.edge['inputmaskname'] is not None else buildState.edgeMask
        # cdf29bf86e41c26c1247aa7952338ac0
        # 25% seems arbitrary.  How much overlap is needed before the inputmask stops providing useful information?
        decision = __getInputMaskDecision(buildState.edge)
        if decision == 'no' or \
                (decision != 'yes' and \
                                 sumMask(abs(((255 - buildState.edgeMask) - (255 - inputmask)) / 255)) / float(
                                 sumMask((255 - buildState.edgeMask) / 255)) <= 0.25):
            inputmask = buildState.edgeMask
    except Exception as ex:
        logging.getLogger('maskgen').warn('Invalid Input Mask size for {}'.format(buildState.getName()))
        inputmask = buildState.edgeMask

    tm = buildState.transformMatrix()
    if buildState.isComposite:
        mask = buildState.compositeMask.mask
        expectedShape = buildState.targetShape
        if inputmask.shape != mask.shape:
            inputmask = cv2.resize(inputmask, (mask.shape[1], mask.shape[0]))
        if tm is not None:
            mask = tool_set.applyTransformToComposite(mask, inputmask, tm,
                                                     returnRaw=returnRaw)
        else:
            inputmask = 255 - inputmask
            differencemask = (255 - buildState.edgeMask) - inputmask
            differencemask[differencemask < 0] = 0
            mask = move_pixels(inputmask, differencemask, mask, isComposite=True)
        if expectedShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, expectedShape)
        return buildState.compositeMask.create(mask)
    elif buildState.donorMask is not None:
        mask = buildState.donorMask.mask
        if tm is not None:
            mask = tool_set.applyTransform(mask,
                                          mask=inputmask,
                                          transform_matrix=tm,
                                          invert=True,
                                          returnRaw=False)
        else:
            if inputmask.shape != buildState.sourceShape:
                inputmask = cv2.resize(inputmask,
                                       (buildState.sourceShape[1], buildState.sourceShape[0]))
            inputmask = 255 - inputmask
            differencemask = (255 - buildState.edgeMask) - inputmask
            differencemask[differencemask < 0] = 0
            mask = move_pixels(differencemask, inputmask, mask)
        if buildState.sourceShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.sourceShape)
        return buildState.donorMask.create(mask)
    return CompositeImage(buildState.source,
                          buildState.target,
                          'image',
                          buildState.edgeMask)

def ca_fill(buildState):
    """
       :param buildState:
       :return: updated composite mask
       @type buildState: BuildState
       @rtype: CompositeImage
       """
    if buildState.isComposite:
        args = buildState.arguments()
        if 'purpose' in args and args['purpose'] == 'remove':
            buildState.compositeMask.mask[buildState.edgeMask == 0] = 0
        return buildState.compositeMask
    else:
        args = buildState.arguments()
        if 'purpose' in args and args['purpose'] in ['remove']:
            buildState.donorMask.mask[buildState.edgeMask == 0] = 0
        return buildState.donorMask

def paste_sampled(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype:CompositeImage
    """
    if buildState.isComposite:
        args = buildState.arguments()
        if 'purpose' in args and args['purpose'] == 'remove':
            buildState.compositeMask.mask[buildState.edgeMask==0] = 0
        return buildState.checkEmptyMask(buildState.compositeMask)
    else:
        args = buildState.arguments()
        if 'purpose' in args and args['purpose'] in ['remove']:
            buildState.donorMask.mask[buildState.edgeMask == 0] = 0
        return buildState.donorMask

def paste_splice(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        args = buildState.arguments()
        if 'purpose' in args and args['purpose'] != 'blend':
            buildState.compositeMask.mask[buildState.edgeMask==0] = 0
        return buildState.checkEmptyMask(buildState.compositeMask)
    elif buildState.donorMask is not None:
        # during a paste splice, the edge mask can split up the donor.
        # although I am wondering if the edgemask needs to be inverted.
        # this effectively sets the donorMask pixels to 0 where the edge mask is 0 (which is 'changed')
        donorMask = tool_set.applyMask(buildState.donorMask.mask, buildState.edgeMask)
    else:
        donorMask = np.zeros(buildState.sourceShape, dtype=np.uint8)
    return CompositeImage( buildState.donorMask.source if buildState.donorMask is not None else buildState.source,
                           buildState.donorMask.target if buildState.donorMask is not None else buildState.target,
                           'image',
                           donorMask)


def select_region_frames(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        return buildState.compositeMask
    return buildState.donorMask

def select_region(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        return buildState.compositeMask
    elif buildState.donorMask is not None:
        return buildState.donorMask
    return CompositeImage(buildState.source,
                        buildState.target,
                        'image',
                        buildState.edgeMask)

def donor(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        return buildState.compositeMask
    elif buildState.donorMask is not None:
        # removed code to handle the paste splice issue where part of the donor
        # may NOT be used.  The old method tried a reverse transform of the
        # inverted paste splice edge mask, rather than using the  edge mask itself.
        # this only works IF there a transform matrix.
        # pred_edges would contain the paste splice mask
        # (edgeMask = edge['maskname']) to which can be use to zero out the
        # unchanged pixels and then apply a transform.
        if len([edge for edge in buildState.pred_edges if getValue(edge,'recordMaskInComposite','no') == 'yes']) > 0:
            tm = buildState.transformMatrix()
            targetShape = buildState.sourceShape
            if tm is not None:
                donorMask = cv2.warpPerspective(buildState.donorMask.mask, tm,
                                                (targetShape[1], targetShape[0]),
                                                flags=cv2.WARP_INVERSE_MAP,
                                                borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype('uint8')
            else:
                donorMask = ImageWrapper(buildState.edgeMask).invert().to_array()
        else:
            donorMask = np.zeros(buildState.donorMask.shape, dtype=np.uint8)
    return CompositeImage( buildState.donorMask.source if buildState.donorMask is not None else buildState.source,
                           buildState.donorMask.target if buildState.donorMask is not None else buildState.target,
                           'image',
                           donorMask)


def image_to_video(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        return _prepare_video_masks(buildState.meta_extractor,
                                    video_tools.getMaskSetForEntireVideo(
                                        buildState.meta_extractor.getMetaDataLocator(buildState.target)),
                                    'video',
                                    buildState.source,
                                    buildState.target,
                                    buildState.edge,
                                    fillWithUserBoundaries=True)
    else:
        wrapper, name = buildState.graph.get_image(buildState.source)
        return CompositeImage(buildState.donorMask.source,
                              buildState.donorMask.target,
                              'image',
                              np.ones(wrapper.to_array().size, dtype=np.uint8) * 255)


def video_donor(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        return buildState.compositeMask
    else:
        return _prepare_video_masks(buildState.meta_extractor,
                                    buildState.edge['videomasks'],
                                    'video',
                                    buildState.source,
                                    buildState.target,
                                    buildState.edge) if buildState.donorMask is None and \
                                                        'videomasks' in buildState.edge and \
                                                        len(buildState.edge[
                                                                'videomasks']) > 0 else buildState.donorMask
    return buildState.donorMask

def flip_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    flip = buildState.flip()
    if buildState.isComposite:
        mask = buildState.compositeMask.mask
        if flip is not None:
            mask = applyFlipComposite(buildState.compositeMask.mask, buildState.edgeMask, flip)
        if buildState.targetShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.targetShape)
        return buildState.compositeMask.create(mask)
    else:
        mask = applyFlipComposite(buildState.donorMask.mask, buildState.edgeMask, flip)
        if buildState.sourceShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.sourceShape)
        return buildState.donorMask.create(mask)


def scale_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    tm = buildState.transformMatrix()
    if buildState.isComposite:
        mask = buildState.compositeMask.mask
        if tm is not None:
            mask = tool_set.applyTransformToComposite(mask,
                                                     buildState.edgeMask,
                                                     tm,
                                                     shape=buildState.targetShape,
                                                     returnRaw=False)
        elif buildState.targetShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.targetShape)
        return buildState.compositeMask.create(mask)
    elif buildState.donorMask is not None:
        mask = buildState.donorMask.mask
        if tm is not None:
            mask = tool_set.applyTransform(mask,
                                          mask=buildState.edgeMask,
                                          transform_matrix=tm,
                                          invert=True,
                                          shape=buildState.sourceShape,
                                          returnRaw=False)
        elif buildState.sourceShape != mask.shape:
            mask = tool_set.applyResizeComposite(mask, buildState.sourceShape)
        return buildState.donorMask.create(mask)


def distort_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return scale_transform(buildState)

def affine_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return scale_transform(buildState)

def shear_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return scale_transform(buildState)


def skew_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return scale_transform(buildState)


def image_selection(buildState):
    """
       :param buildState:
       :return: updated composite mask
       @type buildState: BuildState
       @rtype: CompositeImage
       """
    if buildState.isComposite:
        return video_tools.extractMask(buildState.compositeMask.videomasks,getValue(buildState.edge, 'arguments.Frame Time',
                                                                 defaultValue='00:00:00.000'))
    else:
        masks = video_tools.getMaskSetForEntireVideo(buildState.meta_extractor.getMetaDataLocator(buildState.source),
                                             start_time=getValue(buildState.edge, 'arguments.Frame Time',
                                                                 defaultValue='00:00:00.000'),
                                             end_time=getValue(buildState.edge, 'arguments.Frame Time',
                                                                 defaultValue='00:00:00.000'),
                                             media_types=['video'])

        return _prepare_video_masks(buildState.meta_extractor,
                                    masks,
                                    _guess_type(buildState.edge),
                                    buildState.source,
                                    buildState.target,
                                    buildState.edge,
                                    returnEmpty=False,
                                    fillWithUserBoundaries=True)

def warp_output(buildState):
    """
    Assumes frame rate has not changed.
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return buildState.warpMask()

def echo(buildState):
    """
    Assumes frame rate has not changed.
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        return buildState.compositeMask
    else:
        return buildState.donorMask


def sample_rate_change(buildState):
    """
        :param buildState:
        :return: updated composite mask
        @type buildState: BuildState
        @rtype: CompositeImage
        """
    return buildState.warpMask(media_type='audio')

def output_video_change(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    composite_image = buildState.warpMask()
    shapeChange = buildState.shapeChange()
    if shapeChange != (0, 0):
        buildState.substitute(composite_image)
        composite_image= video_resize_helper(buildState, lambda x : True)
    return composite_image

def audio_donor(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.isComposite:
        return buildState.compositeMask
    else:
        if buildState.getVideoMetaExtractor().getNodeFileType(buildState.target) in ['video', 'audio']:
            return _prepare_video_masks(buildState.meta_extractor,
                                        buildState.edge['videomasks'],
                                        'audio',
                                        buildState.source,
                                        buildState.target,
                                        buildState.edge,fillWithUserBoundaries=False) if buildState.donorMask is None and \
                                                           'videomasks' in buildState.edge and \
                                                           len(buildState.edge['videomasks']) > 0 else buildState.donorMask
    return buildState.donorMask


def __getInputMaskDecision(edge):
    tag = "use input mask for composites"
    if ('arguments' in edge and \
                (tag in edge['arguments'])):
        return edge['arguments'][tag]
    return None

def exif_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    orientflip, orientrotate = buildState.getExifOrientation()
    args = buildState.arguments()
    interpolation = args['interpolation'] if 'interpolation' in args and len(
        args['interpolation']) > 0 else 'nearest'
    if buildState.isComposite:
        mask = alterMask(buildState.compositeMask.mask,
                                  buildState.edgeMask,
                                  rotation=orientrotate,
                                  targetShape=buildState.targetShape,
                                  interpolation=interpolation,
                                  flip=orientflip)
        return buildState.compositeMask.create( mask)
    else:
        orientrotate = -orientrotate if orientrotate is not None else None
        mask= alterReverseMask(buildState.donorMask.mask,
                                buildState.edgeMask,
                                rotation=orientrotate,
                                flip=orientflip,
                                targetShape=buildState.sourceShape)
        return buildState.donorMask.create(mask)

def copy_transform(buildState):
    if buildState.isComposite:
        return buildState.compositeMask
    return buildState.donorMask

def output_transform(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    return exif_transform(buildState)

def defaultAlterComposite(buildState):
    """
    :param buildState:
    :return: updated composite mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    # change the mask to reflect the output image
    # considering the crop again, the high-lighted change is not dropped
    # considering a rotation, the mask is now rotated
    location = buildState.location()
    args = buildState.arguments()
    interpolation = args['interpolation'] if 'interpolation' in args and len(
        args['interpolation']) > 0 else 'nearest'
    orientflip, orientrotate = buildState.getExifOrientation()
    mask = alterMask(buildState.compositeMask.mask,
                              buildState.edgeMask,
                              rotation=orientrotate,
                              targetShape=buildState.targetShape,
                              interpolation=interpolation,
                              flip=orientflip,
                              location=location)
    return buildState.compositeMask.create(mask)


def defaultAlterDonor(buildState):
    """
    :param buildState:
    :return: updated/tranformed donor mask
    @type buildState: BuildState
    @rtype: CompositeImage
    """
    if buildState.donorMask is None:
        return None
    # change the mask to reflect the output image
    # considering the crop again, the high-lighted change is not dropped
    # considering a rotation, the mask is now rotated
    sizeChange = buildState.donorChange()
    location = buildState.location()
    tm = buildState.transformMatrix()
    orientflip, orientrotate = buildState.getExifOrientation()
    orientrotate = -orientrotate if orientrotate is not None else None
    tm = None if (getValue(buildState.edge,'global','no') == 'yes' and orientrotate is not None) else tm
    tm = None if orientflip else tm
    mask =  alterReverseMask(buildState.donorMask.mask,
                            buildState.edgeMask,
                            rotation=orientrotate,
                            sizeChange=sizeChange,
                            location=location,
                            flip=orientflip,
                            transformMatrix=tm,
                            targetShape=buildState.sourceShape)
    return buildState.donorMask.create(mask)


#====================================================================
#  Probe Edge Selection Functions (e.g Queries)
#====================================================================

def isEdgeNotDonorAndNotEmpty(edge_id, edge, operation):
    return edge['op'] != 'Donor' and getValue(edge,'empty mask','no') == 'no'

def isEdgeNotDonor(edge_id, edge, operation):
    return edge['op'] != 'Donor'

def isEdgeComposite(edge_id, edge, operation):
    return edge['recordMaskInComposite'] == 'yes'

def isEdgeLocalized(edge_id, edge, operation):
    """
    :param edge_id:
    :param edge:
    :param operation:
    :return:
    @type Operation
    """
    return (edge['recordMaskInComposite'] == 'yes' or \
           (edge['op'] not in ['TransformSeamCarving',
                              'TransformCrop',
                              'SelectCropFrames',
                              'Donor',
                              'TransformDownSample',
                              'TransformReverse',
                              'DeleteAudioSample'] and \
           ('empty mask' not in edge or edge['empty mask'] == 'no') and \
            getValue(edge, 'global',defaultValue='no') != 'yes')) and \
            operation.category not in ['Output','AntiForensic','PostProcessing','Laundering','TimeAlteration']

def isEdgeLocalizedWithPostProcessingAndLaundering(edge_id, edge, operation):
    """
    :param edge_id:
    :param edge:
    :param operation:
    :return:
    @type Operation
    """
    return edge['recordMaskInComposite'] == 'yes' or \
           (edge['op'] not in ['TransformSeamCarving',
                              'TransformCrop',
                              'Donor',
                              'TransformDownSample',
                              'TransformReverse',
                              'DeleteAudioSample'] and \
           ('empty mask' not in edge or edge['empty mask'] == 'no') and \
            operation.category not in ['Output','TimeAlteration'])

#====================================================================
#  Probe Infrastructure
#====================================================================

class GroupTransformFunction:

    """
    Support group operations with multiple transformation functions, running the functions in the order.

    """
    def __init__(self, functions):
        self.functions = functions if type(functions) == list else [functions]
        self.functions = [graph_rules.getRule(function) for function in self.functions]

    def __call__(self, *args, **kwargs):
        ids = range(len(self.functions))
        if args[0].donorMask is not None:
            ids = reversed(ids)
        for pos in ids:
            function = self.functions[pos]
            result = function(*args)
            if args[0].donorMask is not None:
                args[0].donorMask = result
            else:
                args[0].compositeMask = result
        return result

def _getMaskTranformationFunction(
        op,
        source,
        target,
        extractor):
    """
    @type op: Operation
    @type source: str
    @type target: str
    @type graph: MetaDataExtractor
    """
    sourceType = extractor.getNodeFileType(source)
    if op.maskTransformFunction is not None and sourceType in op.maskTransformFunction:
        return GroupTransformFunction(op.maskTransformFunction[sourceType])
    return None


def mAlterDonor(donorMask, op, source, target, edge, directory='.', pred_edges=[], graph=None, maskMemory=None,
                baseEdge=None, checkEmptyMask=True):
    remember = maskMemory[('donor', baseEdge, (source, target))] if maskMemory is not None else None
    if remember is not None:
        # print("memoize")
        return remember
    result = alterDonor(donorMask, op, source, target, edge, directory, pred_edges, graph, checkEmptyMask=checkEmptyMask)
    if maskMemory is not None:
        maskMemory[('donor', baseEdge, (source, target))] = result
    return result

def alterDonor(donorMask, op, source, target, edge, directory='.', pred_edges=[], graph=None, checkEmptyMask=True):
    """
    :param donorMask:
    :param op:  operation name
    :param source:
    :param target:
    :param edge: edge dictionary
    :param edgeMask:  composite
    :param directory:
    :param pred_edges:
    :param graph:
    :return:
    @type op: Operation
    """

    edgeMask = graph.get_edge_image(source, target, 'maskname', returnNoneOnMissing=True)

    edgeMask = edgeMask.to_array() if edgeMask is not None else None

    source_shape, target_shape = getShapes(graph,source,target,edge,edgeMask)

    buildState = BuildState(edge,
                            source,
                            target,
                            edgeMask,
                            source_shape,
                            target_shape,
                            directory=directory,
                            donorMask=donorMask if donorMask is not None else None,
                            pred_edges=pred_edges,
                            graph=graph,
                            checkEmpties=checkEmptyMask)

    transformFunction = _getMaskTranformationFunction(op, source, target, buildState.getVideoMetaExtractor())
    nodefiletype = buildState.getVideoMetaExtractor().getNodeFileType(source)

    if 'videomasks' in edge or nodefiletype in ['video','audio'] or type(donorMask) == CompositeImage:
        if transformFunction is not None:
            return transformFunction(buildState)
        return output_video_change(buildState)

    try:
        if edgeMask is None:
            raise EdgeMaskError('Missing edge mask from ' + source + ' to ' + target, (source,target))

        if transformFunction is not None:
            return transformFunction(buildState)
        return copy_transform(buildState)
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logging.getLogger('maskgen').error('Failed donor generation: {} to {} with operation {}'.format(
            source,target,edge['op']
        ))
        logging.getLogger('maskgen').info(' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        raise ex



def _getUnresolvedSelectMasksForEdge(edge):
    """
    A selectMask is a mask the is used in composite mask production, overriding the default link mask
    @rtype: dict
    """
    images = edge['selectmasks'] if 'selectmasks' in edge  else []
    sms = {}
    for image in images:
        sms[image['node']] = image['mask']
    return sms


def findBaseNodesWithCycleDetection(graph, node, excludeDonor=True):
    preds = graph.predecessors(node)
    res = [(node, 0, list())] if len(preds) == 0 else list()
    for pred in preds:
        if graph.get_edge(pred, node)['op'] == 'Donor' and excludeDonor:
            continue
        for item in findBaseNodesWithCycleDetection(graph, pred, excludeDonor=excludeDonor):
            res.append((item[0], item[1] + 1, item[2]))
    for item in res:
        item[2].append(node)
    return res


def getShapes(graph,source,target,edge, edgeMask):

    target_im, target_file= graph.get_image(target)
    source_im, source_file = graph.get_image(source)
    shapeChange = toIntTuple(edge['shape change']) if 'shape change' in edge else (0, 0)

    if target_im is not None:
        target_shape = (target_im.image_array.shape[0],target_im.image_array.shape[1])
    elif edgeMask is not None:
        target_shape = (edgeMask.shape[0] + shapeChange[0],edgeMask.shape[1] + shapeChange[1])
    elif source_im is not None:
        target_shape = (source_im.image_array.shape[0] - shapeChange[0],source_im.image_array.shape[1] - shapeChange[1])
    else:
        target_shape = (0,0)

    if source_im is not None:
        source_shape = (source_im.image_array.shape[0],source_im.image_array.shape[1])
    elif edgeMask is not None:
        source_shape = edgeMask.shape
    else:
        source_shape = (target_shape[0] - shapeChange[0], target_shape[1] - shapeChange[1])

    return source_shape,target_shape

def mAlterComposite(graph,
                    edge,
                    op,
                    source,
                    target,
                    composite,
                    directory,
                    base_id,
                    replacementEdgeMask=None,
                    maskMemory=None,
                    checkEmptyMask=True
                    ):
    remember = maskMemory[('composite', base_id, (source, target))] if maskMemory is not None else None
    if remember is not None:
        # print("memoize")
        return remember
    t = time.clock()
    result = alterComposite(graph,
                            edge,
                            op,
                            source,
                            target,
                            composite,
                            directory,
                            replacementEdgeMask,
                            checkEmptyMask=checkEmptyMask)
    logger = logging.getLogger('maskgen')
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("{} edge {} to {}: {}".format(base_id, source, target, time.clock() - t))
    if maskMemory is not None:
        maskMemory[('composite', base_id, (source, target))] = result
    return result


def alterComposite(graph,
                   edge,
                   op,
                   source,
                   target,
                   composite,
                   directory,
                   replacementEdgeMask=None,
                   checkEmptyMask=True):
    """

    :param graph:
    :param edge:
    :param op:
    :param source:
    :param target:
    :param composite:
    :param directory:
    :param replacementEdgeMask:
    :return:
    @type composite: CompositeImage
    """
    edgeMask = graph.get_edge_image(source, target, 'maskname', returnNoneOnMissing=True)\
        if replacementEdgeMask is None else ImageWrapper(replacementEdgeMask)
    edgeMask = np.asarray(edgeMask) if edgeMask is not None else None

    source_shape,target_shape = getShapes(graph,source,target,edge,edgeMask)

    buildState = BuildState(edge,
                            source,
                            target,
                            np.asarray(edgeMask) if edgeMask is not None else None,
                            source_shape,
                            target_shape,
                            compositeMask=composite,
                            directory=directory,
                            graph=graph,
                            checkEmpties= checkEmptyMask)

    transformFunction = _getMaskTranformationFunction(op, source, target, buildState.getVideoMetaExtractor())
    nodefiletype = buildState.getVideoMetaExtractor().getNodeFileType(source)

    if 'videomasks' in edge or nodefiletype in ['zip','video','audio']:
        # TODO: what to do if videomasks are not in edge for video?

        if transformFunction is not None:
            return transformFunction(buildState)

        return output_video_change(buildState)

    try:
        if edgeMask is None:
            raise EdgeMaskError('Missing edge mask from ' + source + ' to ' + target, (source,target))
        if transformFunction is not None:
            return transformFunction(buildState)
        return copy_transform(buildState)
    except Exception as ex:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        logging.getLogger('maskgen').error('Failed composite generation: {} to {} with operation {}'.format(
            source,target,edge['op']
        ))
        logging.getLogger('maskgen').info(' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
        raise ex


class CompositeDelegate:
    composite = None

    def __init__(self, edge_id, graph, gopLoader, maskMemory, notifier=None):
        """
        :param edge_id
        :param graph:
        :param gopLoader:
        @type edge_id : (str,str)
        @type graph: ImageGraph
        @type gopLoader: GroupFilterLoader
        """
        self.maskMemory= maskMemory
        self.gopLoader = gopLoader
        self.graph = graph
        self.meta_extractor = MetaDataExtractor(self.graph)
        self.edge_id = edge_id
        self.edge = graph.get_edge(edge_id[0], edge_id[1])
        if 'empty mask' in self.edge and self.edge['empty mask'] == 'yes':
            logging.getLogger('maskgen').warn('Composite constructed for empty mask {}->{}'.format(
                graph.get_node(edge_id[0])['file'],graph.get_node(edge_id[1])['file'])
            )
            self.empty = True
        else:
            self.empty = False
        baseNodeIdsAndLevels = findBaseNodesWithCycleDetection(self.graph, edge_id[0])
        self.baseNodeId, self.level, self.path = baseNodeIdsAndLevels[0] if len(baseNodeIdsAndLevels) > 0 else (
        None, None)
        self.notifier=notifier

    def _getComposites(self, keepFailures=False):
        """

        :param keepFailures:
        :return: if video masks, return the composite images by audio and video media types separately
        """
        if self.composite is not None:
            return self.composite
        op = self.gopLoader.getOperationWithGroups(self.edge['op'])
        videomasks = getValue(self.edge, 'substitute videomasks', getValue(self.edge, 'videomasks'))
        if videomasks is not None:
            if len(videomasks) == 0:
                media_types = [_guess_type(self.edge)]
            else:
                media_types = set([video_tools.get_type_of_segment(mask) for mask in videomasks])
            return [mask for mask in [_prepare_video_masks(self.meta_extractor,
                                                           videomasks,
                                                           media_type,
                                                           self.edge_id[0], self.edge_id[1],
                                                           self.edge,
                                                           fillWithUserBoundaries=True,
                                                           operation=op)
                    for media_type in media_types] if mask is not None]
        else:
            edgeMask = self.graph.get_edge_image(self.edge_id[0], self.edge_id[1],
                                                 'maskname', returnNoneOnMissing=True)
            if edgeMask is None and not keepFailures:
                raiseError('_getComposites','Edge Mask is Missing',self.edge_id)
            #INVERT SO WHITE HAS CHANGED!
            mask = edgeMask.invert().to_array()
            args = {}
            args.update(op.mandatoryparameters)
            args.update(op.optionalparameters)
            shapeChange = toIntTuple(self.edge['shape change']) if 'shape change' in self.edge else (0, 0)
            expectedShape = (mask.shape[0] + shapeChange[0], mask.shape[1] + shapeChange[1])
            for k,v in args.iteritems():
                if getValue(v,'use as composite',defaultValue=False) and \
                    getValue(self.edge,'arguments.'+k) is not None:
                    mask = openImageFile(os.path.join(self.get_dir(), getValue(self.edge,'arguments.'+k))).to_array()
                    break
            if mask.shape != expectedShape:
                mask = tool_set.applyResizeComposite(mask, expectedShape)
            return [CompositeImage(self.edge_id[0], self.edge_id[1], 'image', mask)]

    def find_donor_edges(self):
        donors = [(pred, self.edge_id[1]) for pred in self.graph.predecessors(self.edge_id[1])
                  if pred != self.edge_id[0] or self.graph.get_edge(pred, self.edge_id[1])['op'] == 'Donor']
        donors.append(self.edge_id)
        return donors

    def constructComposites(self, checkEmptyMask=False):
        results = []
        for composite in self._getComposites():
            results.extend(self.constructTransformedMask(self.edge_id, composite, checkEmptyMask=checkEmptyMask))
        return results

    def get_dir(self):
        return self.graph.dir

    def _continueIfEmpty(self, mask, source, target, op):
        """
        We will let ok masks be dropped
        :param mask:
        :param source:
        :param target:
        :param op:
        :return:
        @type mask: CompositeImage
        """
        if mask is None:
            return False

        if mask.isEmpty():
            logging.getLogger('maskgen').warn(
                "Mask is empty for {} due to edge ({},{}) using operation {}.".format(
                    str(self.edge_id), source, target, op.name
                ))
            if self.notifier is not None and not mask.ok:
                self.notifier(('empty',self.edge_id, (source,target)))
            return not mask.ok
        return True

    def constructTransformedMask(self, edge_id,
                                 compositeMask,
                                 saveTargets=False,
                                 keepFailures=False,
                                 checkEmptyMask=True,
                                 audioToVideo=False):
        """
        walks up down the tree from base nodes, assemblying composite masks
        return: list of tuples (transformed mask, final image id)
        @rtype:  list of CompositeImage
        """

        results = []
        successors = self.graph.successors(edge_id[1])
        for successor in successors:
            source = edge_id[1]
            target = successor
            edge = self.graph.get_edge(source, target)
            if edge['op'] == 'Donor':
                continue
            newMask = compositeMask
            try:
                for op in self.gopLoader.getOperationsWithinGroup(edge['op'], fake=True):
                    newMask = mAlterComposite(self.graph,
                                              edge,
                                              op,
                                              source,
                                              target,
                                              newMask,
                                              self.get_dir(),
                                              maskMemory=self.maskMemory,
                                              base_id=self.edge_id,
                                              checkEmptyMask=checkEmptyMask)
                    if newMask is None:
                        logging.getLogger('maskgen').warn("Mask is empty for {} due to edge ({},{}) using operation {}.".format(
                            str(edge_id),source,target,op.name
                        ))
                        break

                isOkToGoOn = self._continueIfEmpty(newMask, source, target, op)

                if isOkToGoOn:
                    results.extend(self.constructTransformedMask((source, target),
                                                                 newMask,
                                                                 saveTargets=saveTargets,
                                                                 keepFailures=keepFailures,
                                                                 checkEmptyMask=checkEmptyMask,
                                                                 audioToVideo=audioToVideo))

            except Exception as ex:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                logging.getLogger('maskgen').info('Failed composite generation: {} to {} for edge {} with operation {}'.format(
                    source, target,edge_id , edge['op']
                ))
                logging.getLogger('maskgen').info(
                    ' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                if keepFailures:
                    logging.getLogger('maskgen').error('{} for edge {}'.format(ex, edge_id))
                    return [self._finalizeCompositeMask(compositeMask, edge_id[1], saveTargets=saveTargets, failure=True, audioToVideo=audioToVideo)]
                raise ex
#        if len(successors) == 0 and self.edge_id == edge_id:
#            edge = self.graph.get_edge(edge_id[0], edge_id[1])
#            for op in self.gopLoader.getOperationsWithinGroup(edge['op'], fake=True):
#                compositeMask = mAlterComposite(self.graph,
#                                edge,
#                                op,
#                                edge_id[0],
#                                edge_id[1],
#                                compositeMask,
#                                self.get_dir(),
#                                maskMemory=self.maskMemory,
#                                base_id=self.edge_id)
        return results if len(successors) > 0 else [
            self._finalizeCompositeMask(compositeMask, edge_id[1], saveTargets=saveTargets, audioToVideo=audioToVideo)]

    def extendByOne(self, probes, source, target, override_args={}, checkEmptyMask=False):
        import copy
        result_probes = []
        for probe in probes:
            new_probe = copy.deepcopy(probe)
            if probe.targetVideoSegments is not None:
                media_type = 'video'
                compositeMask = compositeMaskSetFromVideoSegment(probe.targetVideoSegments)
            else:
                media_type = 'image'
                compositeMask = probe.targetMaskImage.invert().image_array
            edge = self.graph.get_edge(source, target)
            if len(override_args) > 0 and edge is not None:
                edge = copy.deepcopy(edge)
                edge.update(override_args)
            elif len(override_args) > 0:
                edge = override_args
            altered_composite = CompositeImage(source, target, media_type, compositeMask)
            for innerop in self.gopLoader.getOperationsWithinGroup(edge['op'], fake=True):
                altered_composite = mAlterComposite(self.graph,
                                                    edge,
                                                    innerop,
                                                    source,
                                                    target,
                                                    altered_composite,
                                                    self.get_dir(),
                                                    base_id=self.edge_id,
                                                    checkEmptyMask=checkEmptyMask
                                                    )
            target_mask, target_mask_filename, finalNodeId, nodetype, failure = self._finalizeCompositeMask(altered_composite,target)
            if target_mask is None:
                continue
            new_probe.targetMaskImage = target_mask.mask if nodetype == 'image' else video_tools.getSingleFrameFromMask(
                target_mask.videomasks)
            new_probe.failure = failure
            result_probes.append(new_probe)
        return result_probes

    def constructProbes(self,
                        saveTargets=True,
                        inclusionFunction=None,
                        constructDonors=True,
                        keepFailures=False,
                        exclusions={},
                        checkEmptyMask=True,
                        audioToVideo=False):
        """

        :param saveTargets:
        :return:
        %rtype: list of Probe
        """
        selectMasks = _getUnresolvedSelectMasksForEdge(self.edge)
        finaNodeIdMasks = []
        for composite in self._getComposites(keepFailures=keepFailures):
            finaNodeIdMasks.extend(self.constructTransformedMask(self.edge_id,
                                                                 composite,
                                                                 saveTargets=saveTargets,
                                                                 keepFailures=keepFailures,
                                                                 checkEmptyMask=checkEmptyMask,
                                                                 audioToVideo=audioToVideo))
        probes = []
        for target_mask, target_mask_filename, finalNodeId, media_type, failure in finaNodeIdMasks:
            donorFailure = False
            if finalNodeId in selectMasks:
                try:
                    tm = openImageFile(os.path.join(self.get_dir(),
                                                    selectMasks[finalNodeId]),
                                       isMask=True)
                    target_mask.image = tm.invert()
                    if saveTargets and target_mask_filename is not None:
                        target_mask.save(target_mask_filename, format='PNG')
                    failure=False
                except Exception as e:
                    logging.getLogger('maskgen').error('bad replacement file ' + selectMasks[finalNodeId])
            try:
                # if video, then the media type is in the composite tuple.
                # images still use an ImageWrapper for the target_mask type
                donors = self.constructDonors(saveImage=saveTargets,
                                              inclusionFunction=inclusionFunction,
                                              exclusions=exclusions,
                                              media_type=target_mask.media_type if media_type != 'image' else 'image',
                                              checkEmptyMask= checkEmptyMask
                                              ) if constructDonors else []
            except Exception as ex:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                logging.getLogger('maskgen').info(
                    ' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                if keepFailures:
                    donorFailure = True
                    logging.getLogger('maskgen').error(str(ex))
                    donors = []
                else:
                    raise ex
            self.___add_final_node_with_donors(probes,
                                               finalNodeId,
                                               self.baseNodeId,
                                               target_mask,
                                               target_mask_filename,
                                               media_type,
                                               failure,
                                               donors,
                                               donorFailure=donorFailure
                                               )
        return probes

    def _finalizeCompositeMask(self, image, finalNodeId, saveTargets=False, failure=False, audioToVideo=False):
        """
        :param mask:
        :param finalNodeId:
        :return:  mask, file name and final node id
        @type image: CompositeImage
        """
        # None in the case of empty bit plane.
        # next refactor, we fix this

        if image is None:
            target_mask_filename = os.path.join(self.get_dir(),
                                               shortenName(self.edge_id[0] + '_' + self.edge_id[1] + '_' + finalNodeId,
                                                           '_ps.png',
                                                           identifier=self.graph.nextId()))
            return image, target_mask_filename, finalNodeId, 'image',failure

        if audioToVideo and not image.isImage():
            videomasks = self.meta_extractor.create_video_for_audio(finalNodeId, image.videomasks)
            return CompositeImage(image.source,image.target,image.media_type,videomasks),\
                    None, finalNodeId, 'video', failure

        if image.isImage():
            target_mask_filename = os.path.join(self.get_dir(),
                                                shortenName(self.edge_id[0] + '_' + self.edge_id[1] + '_' + finalNodeId,
                                                            '_ps.png',
                                                            identifier=self.graph.nextId()))
            target_mask = ImageWrapper(image.mask).invert()
            if saveTargets:
                target_mask.save(target_mask_filename, format='PNG')
            return CompositeImage(image.source,image.target,image.media_type,target_mask), \
                   target_mask_filename, finalNodeId, 'image', failure

        return image, None, finalNodeId, 'video', failure

    def ___add_final_node_with_donors(self,
                                      probes,
                                      finalNodeId,
                                      baseNodeId,
                                      target_mask,
                                      target_mask_filename,
                                      media_type,
                                      failure,
                                      donors,
                                      donorFailure=False):
        """

        :param probes:
        :param edge_id:
        :param finalNodeId:
        :param baseNodeId:
        :param target_mask:
        :param target_mask_filename:
        :param level:
        :param media_type: audio,video,image
        :param donors:
        :return:
        @type donors : list[DonorImage]
        @type target_mask: CompositeImage
        """
        donormasks = [donor for donor in donors if donor[0] == self.edge_id[1]]
        if len(donormasks) > 0:
            for donortuple in donormasks:
                probes.append(Probe(self.edge_id,
                                    finalNodeId,
                                    baseNodeId,
                                    donortuple.base,
                                    targetMaskImage=target_mask.finalMask(),
                                    targetMaskFileName=target_mask_filename if target_mask_filename is not None else None,
                                    targetVideoSegments=target_mask.composeVideoSegments(),
                                    targetChangeSizeInPixels=target_mask.sizeOfChange(),
                                    donorMaskImage=donortuple.mask_wrapper if donortuple.media_type == 'image' else \
                                        (None if donortuple.mask_wrapper is None else video_tools.getSingleFrameFromMask(
                                        donortuple.mask_wrapper.videomasks)),
                                    donorMaskFileName=donortuple.mask_file_name if donortuple.media_type == 'image' else None,
                                    donorVideoSegments=_compositeImageToVideoSegment(
                                        donortuple.mask_wrapper) if donortuple.media_type != 'image' else None,
                                    level=self.level,
                                    empty=self.empty or target_mask.isEmpty(),
                                    failure=failure,
                                    donorFailure=donorFailure,
                                    finalImageFileName=os.path.basename(self.graph.get_image_path(finalNodeId)),
                                    usesSubsituteMask = target_mask.issubstitute))
        else:
            probes.append(Probe(self.edge_id,
                                finalNodeId,
                                baseNodeId,
                                None,
                                targetMaskImage=target_mask.finalMask(),
                                targetMaskFileName=target_mask_filename if target_mask_filename is not None else None,
                                targetVideoSegments=target_mask.composeVideoSegments(),
                                targetChangeSizeInPixels=target_mask.sizeOfChange(),
                                level=self.level,
                                empty=self.empty or target_mask.isEmpty(),
                                failure=failure,
                                donorFailure=donorFailure,
                                finalImageFileName=os.path.basename(self.graph.get_image_path(finalNodeId)),
                                usesSubsituteMask=target_mask.issubstitute))

    def _constructDonor(self, node, mask, media_type=None, baseEdge=None, checkEmptyMask=True):
        """
        Walks up the tree assembling donor masks
        """
        def fillEmptyMasks(pred_node, curr_node, masks):
            return [(x[0],self.__getDonorMaskForEdge((pred_node, curr_node), returnEmpty=True)
                if x[1] is None else x[1]) for x in masks]
        result = []
        preds = self.graph.predecessors(node)
        if len(preds) == 0:
            return [(node, mask)]
        pred_edges = [self.graph.get_edge(pred, node) for pred in preds]
        for pred in preds:
            edge = self.graph.get_edge(pred, node)
            if mask is None:
                donorMask = self.__getDonorMaskForEdge((pred, node), returnEmpty=False, media_type=media_type)
                baseEdge = (pred, node)
            else:
                donorMask = mAlterDonor(mask,
                                        self.gopLoader.getOperationWithGroups(edge['op'], fake=True),
                                        pred,
                                        node,
                                        edge,
                                        directory=self.get_dir(),
                                        pred_edges=[p for p in pred_edges if p != edge],
                                        graph=self.graph,
                                        maskMemory=self.maskMemory,
                                        baseEdge=baseEdge,
                                        checkEmptyMask=checkEmptyMask)
            if checkEmptyMask and donorMask.isEmpty():
                continue
            result.extend(fillEmptyMasks(pred, node, self._constructDonor(pred, donorMask, media_type=media_type,
                                                                          baseEdge=baseEdge,
                                                                          checkEmptyMask=checkEmptyMask)))
        return result

    def __getDonorMaskForEdge(self, edge_id,returnEmpty=True,media_type=None):
        edge = self.graph.get_edge(edge_id[0], edge_id[1])
        op = self.gopLoader.getOperationWithGroups(edge['op'], fake=True)
        if 'videomasks' in edge:
            return _prepare_video_masks(self.meta_extractor,
                                        edge['videomasks'],
                                        _guess_type(edge) if media_type is None else media_type,
                                        edge_id[0],
                                        edge_id[1],
                                        edge,
                                        returnEmpty=returnEmpty,
                                        fillWithUserBoundaries=True)
        startMask = self.graph.get_edge_image(edge_id[0], edge_id[1], 'maskname', returnNoneOnMissing=True)
        if startMask is None:
            raise EdgeMaskError('Missing donor mask for ' + edge_id[0] + ' to ' + edge_id[1],edge_id)
        if op.category == 'Select':
            return CompositeImage(edge_id[0], edge_id[1],'image', startMask.to_array())
        return CompositeImage(edge_id[0], edge_id[1],'image', startMask.invert().to_array())

    def __processImageDonor(self, donor_masks):
        """
        merge donors that are aligned to the same base node (through multiple paths)
        :param donor_masks:  a tuple of base node name and donor mask
        :return:
        """
        imageDonorToNodes = {}
        for donor_mask_tuple in donor_masks:
            if not donor_mask_tuple[1].isImage():
                continue
            donor_mask = donor_mask_tuple[1].mask.astype('uint8')
            if np.sum(donor_mask > 1) == 0:
                continue
            baseNode = donor_mask_tuple[0]
            if baseNode in imageDonorToNodes:
                # same donor image, multiple paths to the image.
                imageDonorToNodes[baseNode][donor_mask > 1] = 255
            else:
                imageDonorToNodes[baseNode] = donor_mask.astype('uint8')
        return imageDonorToNodes

    def __mergeVideoDonorMasks(self, mask1, mask2):
        """
        merge donors that are aligned to the same base node (through multiple paths)
        Merge to video masks
        TODO
        :param mask1:
        :param mask2:
        :return:
        """
        return mask1

    def __processVideoDonor(self, donor_masks):
        """
         merge donors that are aligned to the same base node (through multiple paths)
         :param donor_masks:  a tuple of base node name and donor mask
         :return:
        """
        videoDonorToNodes = {}
        for donor_mask_tuple in donor_masks:
            if donor_mask_tuple[1].isImage():
                continue
            baseNode = donor_mask_tuple[0]
            if baseNode in videoDonorToNodes:
                # same donor image, multiple paths to the image.
                videoDonorToNodes[baseNode] = self.__mergeVideoDonorMasks(videoDonorToNodes[baseNode],
                                                                          donor_mask_tuple[1])
            else:
                videoDonorToNodes[baseNode] = donor_mask_tuple[1]
        return videoDonorToNodes

    def __saveDonorImageToFile(self, recipientNode, baseNode, mask):
        if self.graph.has_node(recipientNode):
            fname = shortenName(recipientNode + '_' + baseNode, '_d_mask.png', identifier=self.graph.nextId())
            fname = os.path.abspath(os.path.join(self.get_dir(), fname))
            try:
                mask.save(fname)
            except IOError:
                donorMask = convertToMask(mask)
                donorMask.save(fname)
        return fname

    def __saveDonorVideoToFile(self, recipientNode, baseNode, mask):
        return None

    def __imagePreprocess(self, mask):
        return ImageWrapper(mask).invert()

    def __videoPreprocess(self, mask):
        return mask

    def __doNothingSave(self, recipientNode, baseNode, mask):
        return None

    def __saveDonors(self, target, nodeToDonorDictionary, preprocessFunction, saveFunction, media_type):
        donors = list()
        for baseNode, donor_mask in nodeToDonorDictionary.iteritems():
            mask_wrapper = preprocessFunction(donor_mask)
            fname = saveFunction(target, baseNode, mask_wrapper)
            donors.append(DonorImage(target, baseNode, mask_wrapper, fname, media_type))
        return donors

    def reconstructDonors(self, probes,
                          saveImage=True,
                          inclusionFunction=isEdgeComposite,
                          exclusions={},
                          checkEmptyMask=True
                          ):
        """
        Update donors for the associated edge of this instance
        :param probes:
        :param saveImage:
        :param inclusionFunction:
        :param exclusions:
        :return:
        """
        donors = self.constructDonors(saveImage=saveImage,
                                      inclusionFunction=inclusionFunction,
                                      errorNotifier=raiseError,
                                      exclusions=exclusions,
                                      checkEmptyMask=checkEmptyMask)
        for probe in probes:
            for donortuple in donors:
                if probe.edgeId == self.edge_id and probe.donorBaseNodeId == donortuple.base:
                    probe.donorMaskFileName = donortuple.mask_wrapper if donortuple.media_type == 'image' else \
                                (None if donortuple.mask_wrapper is None else video_tools.getSingleFrameFromMask(
                                    donortuple.mask_wrapper.videomasks))
                    probe.donorVideoSegments = _compositeImageToVideoSegment(
                                donortuple.mask_wrapper) if donortuple.media_type != 'image' else None
                    probe.donorMaskFileName = donortuple.mask_file_name if donortuple.media_type == 'image' else None

    def constructDonors(self,
                        saveImage=True,
                        inclusionFunction=isEdgeComposite,
                        errorNotifier=raiseError,
                        exclusions={},
                        media_type=None,
                        checkEmptyMask=True
                        ):
        """
          Construct donor images
          Find all valid base node, leaf node tuples
          :return computed donors in the form of tuples
          (image node id donated to, base image node, ImageWrapper mask, filename)
          @rtype list of DonorImage
        """
        donors = list()
        if getValue(exclusions, 'global.donors', False):
            return donors

        for edge_id in self.find_donor_edges():
            edge = self.graph.get_edge(edge_id[0], edge_id[1])
            startMask = None
            edgeMask = self.__getDonorMaskForEdge(edge_id, media_type=media_type)
            if edge['op'] == 'Donor':
                startMask = edgeMask
            elif len(getValue(edge,'inputmaskname',defaultValue='')) > 0 and \
                    (edge['recordMaskInComposite'] == 'yes' or
                         inclusionFunction(edge_id,edge,self.gopLoader.getOperationWithGroups(edge['op'],fake=True))):
                fullpath = os.path.abspath(os.path.join(self.get_dir(), edge['inputmaskname']))
                source =  self.graph.get_image_path(edge_id[0])
                if not os.path.exists(source):
                    startMask = None
                elif not os.path.exists(fullpath) and getValue(exclusions,'global.inputmaskname',False):
                    errorNotifier('constructDonors','Missing input mask for ' + edge_id[0] + ' to ' + edge_id[1],edge_id)
                    # we do need to invert because these masks are white=Keep(unchanged), Black=Remove (changed)
                    # we want to capture the 'unchanged' part, where as the other type we capture the changed part
                elif tool_set.fileType(fullpath) not in ['video','audio'] and tool_set.fileType(source) in ['video','audio']:
                    #undefined at this point
                    startMask = None
                elif tool_set.fileType(fullpath) in ['video','audio'] and 'videomasks' in edge:
                    startMask = _prepare_video_masks(self.meta_extractor,
                                                     video_tools.getMaskSetForEntireVideo(video_tools.FileMetaDataLocator(fullpath)),
                                                     # TODO: need to reconsider this and base the type on the videomask type
                                                     tool_set.fileType(fullpath),
                                                     edge_id[0],
                                                     edge_id[1],
                                                     edge,
                                                     returnEmpty=False,
                                                     operation=self.gopLoader.getOperationWithGroups(edge['op']))
                else:
                    startMask = self.graph.openImage(fullpath, mask=False).to_mask().to_array()
                    if startMask is not None and edgeMask.isImage() and \
                                    edgeMask.mask.shape != startMask.shape and \
                            getValue(exclusions, 'global.inputmaskname', False):
                        errorNotifier('constructDonors',
                                      'Skipping invalid sized mask for ' + edge_id[0] + ' to ' + edge_id[1], edge_id)
                        startMask = None
                    else:
                        startMask = CompositeImage(edge_id[0],edge_id[1],'image',startMask)
                if startMask is None and getValue(exclusions,'global.inputmaskname',False):
                    errorNotifier('constructDonors','Missing donor mask for ' + edge_id[0] + ' to ' + edge_id[1],edge_id)
            if startMask is not None:
                if startMask.isEmpty():
                    startMask = None
                try:
                    if getValue(exclusions, 'global.videodonors', False) and \
                        type(startMask) == CompositeImage:
                        donor_masks = {}
                    else:
                        donor_masks = self._constructDonor(edge_id[0], startMask, media_type=media_type,
                                                           baseEdge=edge_id, checkEmptyMask=checkEmptyMask)
                    imageDonorToNodes = self.__processImageDonor(donor_masks)
                    videoDonorToNodes = self.__processVideoDonor(donor_masks)
                    donors.extend(self.__saveDonors(edge_id[1], imageDonorToNodes, self.__imagePreprocess,
                                                    self.__saveDonorImageToFile if saveImage else self.__saveDonorImageToFile,
                                                    'image'))
                    donors.extend(self.__saveDonors(edge_id[1], videoDonorToNodes, self.__videoPreprocess,
                                                    self.__saveDonorVideoToFile if saveImage else self.__doNothingSave,
                                                    'video'))
                except EdgeMaskError as e:
                    errorNotifier('constructDonors',e.message,e.edge_id)
                except Exception as e:
                    exc_type, exc_value, exc_traceback = sys.exc_info()
                    logging.getLogger('maskgen').info(
                        ' '.join(traceback.format_exception(exc_type, exc_value, exc_traceback)))
                    errorNotifier('constructDonors',str(e), edge_id)
        return donors


def prepareComposite(edge_id, graph, gopLoader, memory=None, notifier=None):
    """
    Depending on the edge properties, construct the composite mask
    :param graph
    :param edge_id: edge
    :param edge:  dictionary of edge
    :return: CompositeDelegate
    @type graph: ImageGraph
    @type edge_id: (str, str)
    @type edge: dict[str,dict]
    """
    return CompositeDelegate(edge_id, graph, gopLoader, memory, notifier=notifier)


#====================================================================
# Composite Builders
#====================================================================

class CompositeBuilder:
    def __init__(self, passes, composite_type):
        self.passes = passes
        self.composite_type = composite_type

    def initialize(self, graph, probes):
        pass

    def finalize(self, probes, save=True):
        pass

    def build(self, passcount, probe, edge):
        pass

    def getComposite(self, finalNodeId):
        return None


class GraphCompositeIdAssigner:
    """
        Each edge and final node is associated with a compositeid.
        Each file node is associated with a group id.
        target ids associated with a group id are unique.
        A reset also increments the file id.
        Reset points are algorithmically determined by detected pixel
        changes for an on more than one path.
        In the future, the algorithm should get the reset points
        from the probe constuction where transforms themselves communicate
        pixel changes along a path.  HOWEVER, that interjects responsibility
        in that transformation code.  So, instead, post analysis is done here
        to maintain some abstraction over efficiency.

    """

    def __init__(self, graph):
        """
        :param graph:
        @type graph: ImageGraph
        """
        self.graph = graph

    def updateProbes(self,probes, builder):
        """
        @type probes : list of Probe
        :param builder:
        :return:
        """
        self.__buildProbeEdgeIds(probes, builder)
        return probes

    def __getProbeId(self,item, group):
        import hashlib
        key = hashlib.sha384(item).hexdigest()
        if key in group:
            tupleInGroup = group[key]
            if np.any(tupleInGroup[1] != item):
                newkey = key + '01'
                while newkey in group:
                    newkey = key + '{:02}'.format(int(newkey[-2:0]) + 1)
                return newkey
        return key

    def __buildProbeEdgeIds(self, probes,builder):
        """
         @type probes : list of Probe
        :param probes:
        :param baseNodes:
        :return:
        """
        fileid = IntObject()
        target_groups = dict()
        group_bits = {}
        # targets associated with different base nodes and shape are in a different groups
        # note: target mask images will have the same shape as their final node
        for probe in probes:
            r = np.asarray(probe.targetMaskImage,order='C')
            key = (probe.targetBaseNodeId, r.shape)
            if key not in target_groups:
                target_groups[key] = {}
                target_groups[key] = (fileid.value, {})
                group_bits[fileid.value] = IntObject()
                fileid.increment()
            if probe.edgeId not in target_groups[key][1]:
                target_groups[key][1][probe.edgeId] = {}
            probeid = self.__getProbeId(r,target_groups[key][1][probe.edgeId])
            #print str(probe.edgeId) + '-> ' + probe.finalNodeId + '=' + probeid
            if probeid not in target_groups[key][1][probe.edgeId]:
                group_bits[target_groups[key][0]].increment()
                probe.composites[builder] = {
                    'groupid': target_groups[key][0],
                    'bit number': group_bits[target_groups[key][0]].value
                }
                target_groups[key][1][probe.edgeId][probeid] = (group_bits[target_groups[key][0]].value,r)
            else:
                probe.composites[builder] = {
                    'groupid': target_groups[key][0],
                    'bit number': target_groups[key][1][probe.edgeId][probeid][0]
                }

class GraphCompositeVideoIdAssigner:
    """
        Each edge and final node is associated with a compositeid.
        Each file node is associated with a group id.
        target ids associated with a group id are unique.
        A reset also increments the file id.
        Reset points are algorithmically determined by frame rate, duration and # of frames.
    """
    def __init__(self, per_file_key=False):
        self.key_function = self._get_file_key if per_file_key else self._get_complex_key

    def updateProbes(self,probes, builder, directory = '.'):
        """
        @type probes : list of Probe
        :param builder:
        :return:
        """
        self.__buildGroups(probes, builder,directory)
        return probes

    def _get_file_key(self, segment,filename):
        return os.path.basename(filename)

    def _get_complex_key(self, segment,video_file):
        if segment is None:
            return os.path.basename(video_file)
        else:
            shape = video_tools.get_shape_of_video(video_file)
            return (video_tools.get_rate_from_segment(segment, 30),
                                video_tools.get_frames_from_segment(segment),
                                video_tools.get_end_time_from_segment(segment),
                                shape[0],
                                shape[1])

    def __buildGroups(self, probes, builder, directory):
        """
          Build the list of probes assigned to each group
               @type probes : list of Probe
              :param probes:
              :param baseNodes:
        :return:
        @type probes: list of Probe
        """
        self.group_probes = {}
        self.group_bits = {}
        self.writers = {}
        fileid = IntObject()
        for probe in probes:
            if not probe.has_masks_in_target():
                continue
            video_file = os.path.join(directory, probe.finalImageFileName)
            segment = video_tools.get_frame_count(video_file)
            key = self.key_function(segment, video_file)
            rate = video_tools.get_rate_from_segment(segment, 30) if segment is not None else 30
            if key not in self.group_probes:
                    self.writers[key] = tool_set.GrayBlockWriter(os.path.join(directory,'vmasks_{}'.format(fileid.increment())),
                                                                 rate)
                    self.group_probes[key] = []
                    self.group_bits[key] = IntObject()
            self.group_probes[key].append(probe)
            probe.composites[builder] = {
                    'groupid': key,
                    'bit number': self.group_bits[key].increment()
            }

class HDF5CompositeBuilder(CompositeBuilder):

    def __init__(self):
        self.composites = dict()
        self.group_bit_check = dict()
        CompositeBuilder.__init__(self, 1, 'hdf5')


    def _update_frame(self, frame, thisbit):
        return frame | thisbit

    def _build_id_assigner(self):
        return GraphCompositeVideoIdAssigner(False)

    def initialize(self, graph, probes):
        self.compositeIdAssigner = self._build_id_assigner()
        return self.compositeIdAssigner.updateProbes(probes,'hdf5',directory=graph.dir)

    def build(self, passcount, probe, edge):
        """

        :param passcount:
        :param probe:
        :param edge:
        :return:
        @type probe: Probe
        """
        pass

    def finalize(self, probes, save=True):
        import itertools
        results = {}
        if len(probes) == 0:
            return {}
        for group in self.compositeIdAssigner.group_probes:
            writer = self.compositeIdAssigner.writers[group]
            grouped_probes = self.compositeIdAssigner.group_probes[group]
            segments_with_probe = [[(segment_with_probe, grouped_probes[i]) for segment_with_probe in
                                    grouped_probes[i].targetVideoSegments] for i in range(len(grouped_probes))]
            segments_with_probe = list(itertools.chain(*segments_with_probe))
            segments_with_probe = sorted(segments_with_probe,
                                         key=lambda x: x[0].startframe)
            frame_no = segments_with_probe[0][0].startframe
            frame_time = segments_with_probe[0][0].starttime
            edges = set([str(probe.edgeId) for probe in grouped_probes])
            reader_managers = {id: tool_set.GrayBlockReaderManager() for id in edges}
            while len(segments_with_probe) > 0:
                segments_with_probe = [segment_with_probe for segment_with_probe in segments_with_probe if
                                            segment_with_probe[0].endframe >= frame_no]
                frame = None
                comopsite_byte_id= 0
                for segment_with_probe in segments_with_probe:
                    if frame_no >= segment_with_probe[0].startframe:
                        reader = reader_managers[str(segment_with_probe[1].edgeId)].create_reader(
                            segment_with_probe[0].filename,
                            start_frame=segment_with_probe[0].startframe,
                            start_time=segment_with_probe[0].starttime,
                            end_frame=segment_with_probe[0].endframe)
                        mask = reader.read()
                        if frame is None:
                            frame = np.zeros(mask.shape + (1,), dtype='uint8')
                        thisbit = np.zeros(mask.shape).astype('uint8')
                        bit = segment_with_probe[1].composites[self.composite_type]['bit number'] - 1
                        bitvalue = 1 << (bit % 8)
                        #MASK is BLACK, then SET BIT because black is CHANGED
                        thisbit[mask == 0] = bitvalue
                        frame[:, :, comopsite_byte_id] = self._update_frame(frame[:,:,comopsite_byte_id], thisbit)
                if frame is not None:
                    writer.write(frame, frame_time,frame_no)
                    for segment_with_probe in segments_with_probe:
                        segment_with_probe[1].composites[self.composite_type]['file name'] = writer.filename
                        results[segment_with_probe[1].composites[self.composite_type]['groupid']] = writer.filename
                frame_no += 1
                frame_time += 1000.0/segment_with_probe[0].rate
            writer.close()
        return results


class HDF5CompositeBuilderPerMedia(HDF5CompositeBuilder):
    """
    """

    def __init__(self):
        HDF5CompositeBuilder.__init__(self)

    def _build_id_assigner(self):
        return GraphCompositeVideoIdAssigner(True)

class HDF5CompositeBuilderUseLast(HDF5CompositeBuilderPerMedia):
    """
    Only used the last manipulation for any bit plane
    """

    def __init__(self):
        HDF5CompositeBuilderPerMedia.__init__(self)

    def _update_frame(self, frame, thisbit):
        return thisbit



class Jpeg2000CompositeBuilder(CompositeBuilder):
    def __init__(self):
        self.composites = dict()
        self.group_bit_check = dict()
        CompositeBuilder.__init__(self, 1, 'jp2')

    def initialize(self, graph, probes):
        compositeIdAssigner = GraphCompositeIdAssigner(graph)
        return compositeIdAssigner.updateProbes(probes, self.composite_type)

    def build(self, passcount, probe, edge):
        """

        :param passcount:
        :param probe:
        :param edge:
        :return:
        @type probe: Probe
        """
        if passcount > 0:
            return
        groupid = probe.composites[self.composite_type]['groupid']
        targetid = probe.composites[self.composite_type]['bit number']
        bit = targetid - 1
        if groupid not in self.composites:
            self.composites[groupid] = []
        composite_list = self.composites[groupid]
        composite_mask_id = (bit / 8)
        imarray = np.asarray(probe.targetMaskImage)
        sums = np.sum(255-imarray)
        if sums == 0:
            logging.getLogger('maskgen').error('Empty bit plane for edge {} to {}:{}'.format(
                str(probe.edgeId),probe.finalNodeId,probe.finalImageFileName
            ))
        # check to see if the bits are in fact the same for a group
        if (groupid, targetid) not in self.group_bit_check:
            self.group_bit_check[(groupid, targetid)] = imarray
            while (composite_mask_id + 1) > len(composite_list):
                composite_list.append(np.zeros((imarray.shape[0], imarray.shape[1])).astype('uint8'))
            thisbit = np.zeros((imarray.shape[0], imarray.shape[1])).astype('uint8')
            bitvalue = 1 << (bit % 8)
            thisbit[imarray == 0] = bitvalue
            composite_list[composite_mask_id] = composite_list[composite_mask_id] | thisbit
        else:
            check = np.all(self.group_bit_check[(groupid, targetid)] == imarray)
            if not check:
                logging.getLogger('maskgen').error('Failed assertion for edge {} to {}:{}'.format(
                  str(probe.edgeId), probe.finalNodeId,probe.finalImageFileName)
                )
            assert (check)


    def checkProbes(self,probes):
        files = {}
        import glymur
        for probe in probes:
            file =  probe.composites[self.composite_type]['file name']
            if file not in files:
                jp2 = glymur.Jp2k(file)
                files[file] = jp2[:]
            jp2img = files[file]
            bitplaneid = probe.composites[self.composite_type]['bit number'] - 1
            byteplane = jp2img[:,:,bitplaneid / 8]
            bit = 1<<(bitplaneid%8)
            img = np.ones((jp2img.shape[0], jp2img.shape[1])).astype('uint8')*255
            try:
                img[(byteplane&bit)>0]  = 0
                if not np.all(img==probe.targetMaskImage.image_array):
                    raise EdgeMaskError('Not march on {}:{}'.format(file, str(probe.edgeId)),probe.edgeId)
            except Exception as ex:
                print ex


    def finalize(self, probes, save=True):
        results = {}
        if len(probes) == 0:
            return
        dirs = [os.path.split(probe.targetMaskFileName)[0] for probe in probes if
                probe.targetMaskFileName is not None]
        dir = dirs[0] if len(dirs) > 0 else '.'
        for groupid, compositeMaskList in self.composites.iteritems():
            third_dimension = len(compositeMaskList)
            analysis_mask = np.zeros((compositeMaskList[0].shape[0], compositeMaskList[0].shape[1])).astype('uint8')
            if third_dimension == 1:
                result = compositeMaskList[0]
                analysis_mask[compositeMaskList[0] > 0] = 255
            else:
                result = np.zeros(
                    (compositeMaskList[0].shape[0], compositeMaskList[0].shape[1], third_dimension)).astype('uint8')
                for dim in range(third_dimension):
                    result[:, :, dim] = compositeMaskList[dim]
                    analysis_mask[compositeMaskList[dim] > 0] = 255
            globalchange, changeCategory, ratio = maskChangeAnalysis(analysis_mask,
                                                                     globalAnalysis=True)
            img = ImageWrapper(result, mode='JP2')
            results[groupid] = (img, globalchange, changeCategory, ratio)
            if save:
                img.save(os.path.join(dir, str(groupid) + '_c.jp2'))

        for probe in probes:
            groupid = probe.composites[self.composite_type]['groupid']
            if groupid not in results:
                continue
            finalResult = results[groupid]
            targetJP2MaskImageName = os.path.join(dir, str(groupid) + '_c.jp2')
            probe.composites[self.composite_type]['file name'] = targetJP2MaskImageName
            probe.composites[self.composite_type]['image'] = finalResult[0]

        #self.checkProbes(probes)
        return results


class EmptyCompositeBuilder(CompositeBuilder):
    def __init__(self):
        CompositeBuilder.__init__(self, 0, 'empty')

class ColorCompositeBuilder(CompositeBuilder):
    def __init__(self):
        self.composites = dict()
        self.colors = dict()
        CompositeBuilder.__init__(self, 2, 'color')

    def initialize(self, graph, probes):
        for probe in probes:
            edge = graph.get_edge(probe.edgeId[0], probe.edgeId[1])
            color = [int(x) for x in edge['linkcolor'].split(' ')]
            self.colors[probe.edgeId] = color

    def _to_color_target_name(self, name):
        return name[0:name.rfind('.png')] + '_c.png'

    def build(self, passcount, probe, edge):
        if passcount == 0:
            return self.pass1(probe, edge)
        elif passcount == 1:
            return self.pass2(probe, edge)

    def pass1(self, probe, edge):
        color = [int(x) for x in edge['linkcolor'].split(' ')]
        colorMask = maskToColorArray(probe.targetMaskImage, color=color)
        if probe.finalNodeId in self.composites:
            self.composites[probe.finalNodeId] = mergeColorMask(self.composites[probe.finalNodeId], colorMask)
        else:
            self.composites[probe.finalNodeId] = colorMask

    def pass2(self, probe, edge):
        """

        :param probe:
        :param edge:
        :return:
        @type probe: Probe
        """
        # now reconstruct the probe target to be color coded and obscured by overlaying operations
        color = [int(x) for x in edge['linkcolor'].split(' ')]
        composite_mask_array = self.composites[probe.finalNodeId]
        result = np.ones(composite_mask_array.shape).astype('uint8') * 255
        matches = np.all(composite_mask_array == color, axis=2)
        #  only contains visible color in the composite
        result[matches] = color

    def finalize(self, probes, save=True):
        results = {}
        for finalNodeId, compositeMask in self.composites.iteritems():
            result = np.zeros((compositeMask.shape[0], compositeMask.shape[1])).astype('uint8')
            matches = np.any(compositeMask != [255, 255, 255], axis=2)
            result[matches] = 255
            globalchange, changeCategory, ratio = maskChangeAnalysis(result,
                                                                     globalAnalysis=True)
            results[finalNodeId] = (ImageWrapper(compositeMask), globalchange, changeCategory, ratio)
        for probe in probes:
            if probe.finalNodeId not in results:
                continue
            finalResult = results[probe.finalNodeId]
            if probe.targetMaskFileName is not None:
                targetColorMaskImageName = self._to_color_target_name(probe.targetMaskFileName)
                probe.composites[self.composite_type] = {
                    'file name': targetColorMaskImageName,
                    'image': finalResult[0],
                    'color': self.colors[probe.edgeId]
                }
                if save:
                    finalResult[0].save(targetColorMaskImageName)
                    assert os.path.exists(targetColorMaskImageName)
            else:
                probe.composites[self.composite_type] = {
                    'image': finalResult[0],
                    'color': self.colors[probe.edgeId]
                }
        return results

