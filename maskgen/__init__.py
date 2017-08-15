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
    targetMaskImage = None
    targetMaskFileName = None
    composites = None
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
    @type compositeFileNames: dict of str:str
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
        self.composites = dict()

import graph_rules
graph_rules.setup()
from image_wrap import  ImageWrapper



