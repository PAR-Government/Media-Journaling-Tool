# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import cv2
from PIL import Image
import numpy
from maskgen import tool_set

def transform(img,source,target,**kwargs):
    kernelSize = 25
    mask = numpy.asarray(tool_set.openImageFile(kwargs['inputmaskname']).to_mask())
    rgb = img.convert('RGB')
    cv_image = numpy.array(rgb)
    blur_image = cv2.medianBlur(cv_image,kernelSize)
    cv_image_copy = numpy.copy(cv_image)
    cv_image_copy[mask == 255] = blur_image[mask == 255]
    Image.fromarray(cv_image_copy,'RGB').save(target)
    return None,None

def operation():
  return {
          'category': 'Filter',
          'name': 'Blur',
          'description':'Median Filter',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments':{
              'inputmaskname':{
                  'type':'imagefile',
                  'defaultvalue':None,
                  'description':'Mask image where black pixels identify region to blur'
              },
              'Blur Type': {
                  'type': 'text',
                  'defaultvalue':'Median',
                  'description': ''
            }},
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return None
