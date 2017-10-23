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
    media_type = None

    def __init__(self,rate, starttime, startframe, endtime,endframe, frames, filename, media_type):
        """

        :param rate:
        :param starttime:
        :param startframe:
        :param endtime:
        :param endframe:
        :param frames: number frames affected by manipulation in this segment
        :param filename: may not be present without mask, otherwise this is an HDF5 file
        :param media_type: one of 'audio','video'
        @type rate : float
        @type starttime : float
        @type startframe : int
        @type endtime : float
        @type endframe : int
        @type frames : int
        @type filename : str
        @type media_type : str
        """
        self.rate = rate
        self.startframe = startframe
        self.starttime = starttime
        self.endtime = endtime
        self.endframe = endframe
        self.frames = frames
        self.filename = filename
        self.media_type = media_type

class Probe:
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

    """
    @type edgeId: tuple
    @type targetBaseNodeId: str
    @type targetMaskFileName: str
    #type targetChangeSizeInPixels: size
    @type targetMaskImage: ImageWrapper
    @type finalNodeId: str
    @type compositeFileNames: dict of str:str
    @type donorBaseNodeId: str
    @type donorMaskFileName: str
    @type donorMaskImage: ImageWrapper
    @type donorVideoSegments: list (VideoSegment)
    @type level: int
    @type targetVideoSegments: list (VideoSegment)

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
                 level=0):
        self.edgeId = edgeId
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
        self.composites = dict()

import graph_rules
graph_rules.setup()
from image_wrap import  ImageWrapper



