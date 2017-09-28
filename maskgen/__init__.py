import matplotlib
matplotlib.use("TkAgg")
from pkg_resources import get_distribution
__version__ = get_distribution('maskgen').version
import logging
from loghandling import set_logging
set_logging()
import software_loader
from image_graph import igversion
logging.getLogger('maskgen').info('Version ' + igversion)

class Probe:
    edgeId = None
    targetBaseNodeId = None
    finalNodeId = None
    composites = None
    donorBaseNodeId = None
    level = 0

    """
    @type edgeId: tuple
    @type targetBaseNodeId: str
    @type targetMaskFileName: str
    @type targetMaskImage: ImageWrapper
    @type finalNodeId: str
    @type compositeFileNames: dict of str:str
    @type donorBaseNodeId: str
    @type donorMaskImage : ImageWrapper
    @type donorMaskFileName: str
    @type level: int

    The target is the node edgeId's target node (edgeId[1])--the image after the manipulation.
    The targetBaseNodeId is the id of the base node that supplies the base image for the target.
    The level is level from top to bottom in the tree.  Top is level 0
    """


    def __init__(self,
                 edgeId,
                 finalNodeId,
                 targetBaseNodeId,
                 targetMaskFileName,
                 donorBaseNodeId,
                 donorMaskFileName,
                 level=0):
        self.edgeId = edgeId
        self.finalNodeId = finalNodeId
        self.targetBaseNodeId = targetBaseNodeId
        self.targetMaskFileName = targetMaskFileName
        self.donorBaseNodeId = donorBaseNodeId
        self.donorMaskFileName = donorMaskFileName
        self.level = level
        self.composites = dict()

class ImageProbe(Probe):

    targetMaskImage = None
    donorMaskImage = None
    targetChangeSizeInPixels = 0
    targetMaskFileName = None
    donorMaskFileName = None

    """
    @type targetChangeSizeInPixels: int
    @type targeMaskImage: ImageWrapper
    @type donorMaskImage: ImageWrapper
    """


    def __init__(self, edgeId, finalNodeId, targetBaseNodeId, targetMaskImage, targetMaskFileName,
                 targetChangeSizeInPixels,
                 donorBaseNodeId, donorMaskImage, donorMaskFileName, level=0):
        Probe.__init__(self,edgeId, finalNodeId, targetBaseNodeId,
                 donorBaseNodeId,  level=level)
        self.targetChangeSizeInPixels = targetChangeSizeInPixels
        self.targeMaskImage = targetMaskImage
        self.donorMaskImage = donorMaskImage
        self.donorMaskFileName = donorMaskFileName
        self.targetMaskFileName = targetMaskFileName

class VideoSegment:
    """
      USED FOR AUDIO.
      Filename is ONLY present if there are localization tasks.

      rate = in milliseconds
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

    def __init__(self,rate, starttime, startframe, endtime,endframe, frames, filename):
        """

        :param rate:
        :param starttime:
        :param startframe:
        :param endtime:
        :param endframe:
        :param frames:
        :param filename:
        @type rate : float
        @type starttime : float
        @type startframe : int
        @type endtime : float
        @type endframe : int
        @type frames : int
        @type filename : str
        """
        self.rate = rate
        self.startframe = startframe
        self.starttime = starttime
        self.endtime = endtime
        self.endframe = endframe
        self.frames = frames
        self.filename = filename

class VideoProbe(Probe):
    targetMasks = None
    donorMasks = None
    """
    Each item of the two lists is a dictionary containing information about the segment

    @type targetMasks: list (VideoSegment)
    @type donorMasks: list (VideoSegment)
    """

    def __init__(self,
                 edgeId,
                 finalNodeId,
                 targetBaseNodeId,
                 targetMasks,
                 donorBaseNodeId,
                 donorMasks,
                 level=0):
        Probe.__init__(self, edgeId, finalNodeId, targetBaseNodeId,
                       donorBaseNodeId,  level=level)
        self.targetMasks = targetMasks
        self.donorMasks = donorMasks


import graph_rules
graph_rules.setup()
from image_wrap import  ImageWrapper



