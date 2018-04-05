import numpy as np
import os
from maskgen.image_wrap import openImageFile,ImageWrapper
import cv2

"""
Convert a gray image into a single color channel.
"""

def transform(img, source, target, **kwargs):
    channel_map = {
        "red":0,
        "green":1,
        "blue":2
    }
    donor = kwargs['mask'] if 'mask' in kwargs else source
    channel_name = kwargs['channel'] if 'channel' in kwargs else "green"
    img = openImageFile(donor)
    color_im = np.zeros((img.size[1],img.size[0],3),dtype=np.uint8)
    color_im [:,:,channel_map[channel_name]]  = img.image_array
    ImageWrapper(color_im).save(target)
    return None,None

def operation():
    return {'name':'Blend',
          'category':'Layer',
          'description':'Convert a gray image into a single color channel',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments': {
              "channel" : {
                  "type":"list",
                  "defaultvalue":"green",
                  "values": ["red","green","blue"],
                  "description": "which channel is set to the gray image"
              },
              "mode": { "type": "text",  "defaultvalue":"Color" }
          },
          'transitions': [
              'image.image'
          ]
          }


def suffix():
    return '.png'
