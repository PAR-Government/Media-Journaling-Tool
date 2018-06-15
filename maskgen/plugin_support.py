# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
from maskgen.cv2api import cv2api_delegate
from maskgen.image_wrap import ImageWrapper
import numpy as np
from maskgen.tool_set import fileType

"""JT code only used for plugin conversion"""


def ImagePluginWriter(filename, img):
    ImageWrapper(np.clip(img,0,255).astype('uint8')).save(filename)

class ImagePluginReader:

    def __init__(self, image, use_16=False):
        self.image = image
        self.use_16 = use_16

    def __call__(self, *args, **kwargs):
        i =  self.image
        self.image = None
        return (i.astype('uint8') if not self.use_16 else i.astype('int16')) if i is not None else None

class VideoPluginReader:

    def __init__(self, name, frames=-1, use_16=False):
        self.reader = cv2api_delegate.videoCapture(name)
        self.frames = frames
        self.count = 0
        self.use_16 = use_16

    def __call__(self, *args, **kwargs):
        if self.count > self.frames and self.frames > 0:
            return None
        self.count += 1
        ret_one, frame_one = self.reader.read()
        return (frame_one if not self.use_16 else frame_one.astype('int16')) if ret_one else None if ret_one else None

    def close(self):
        self.reader.release()

    def getWriter(self,name,codec):
        width = int(self.reader.get(cv2api_delegate.prop_frame_width))
        height = int(self.reader.get(cv2api_delegate.prop_frame_height))
        fourcc = cv2api_delegate.get_fourcc(codec) if codec != 'RAW' else 0
        return VideoPluginWriter(cv2api_delegate.videoWriter(name, fourcc, (self.reader.get(cv2api_delegate.prop_fps)), (width, height)),
                                 clip=self.use_16)

class VideoPluginWriter:

    def __init__(self,writer, clip=False):
        """
        :param writer:
        @type writer: cv2.VideoWriter
        """
        self.writer = writer
        self.clip=clip

    def __call__(self, *args, **kwargs):
        img = args[0]
        if self.clip:
            img = np.clip(img, 0, 255)
        self.writer.write(img.astype('uint8'))

    def close(self):
        self.writer.release()

def run_plugin(imgreader, imgwriter, processor):
    while True:
        img = imgreader()
        if img is None:
            break
        imgwriter(processor(img))