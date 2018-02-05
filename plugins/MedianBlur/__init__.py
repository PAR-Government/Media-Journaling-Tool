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
from random import randint

def transform(img,source,target,**kwargs):
    kernelSize = int(kwargs['kernelSize']) if 'kernelSize' in kwargs else 25
    percentageChange = float(kwargs['percentageChange']) if 'percentageChange' in kwargs else 1
    rgb = img.convert('RGB')
    cv_image = numpy.array(rgb)
    size_w = int(percentageChange * float(cv_image.shape[1]))
    size_h = int(percentageChange *  float(cv_image.shape[0]))
    try:
        r_w = randint(1, cv_image.shape[1] - size_w)
        r_h = randint(1, cv_image.shape[0] - size_h)
    except:
        r_w = 0
        r_h = 0
    roi = cv_image[r_h:r_h + size_h, r_w:r_w + size_w, ]
    blur_roi = cv2.medianBlur(roi, kernelSize)
    cv_image[r_h:r_h + size_h, r_w:r_w + size_w] = blur_roi
    Image.fromarray(cv_image, 'RGB').save(target)
    return None, None

# the actual link name to be used. 
# the category to be shown
def operation():
  return {
          'category': 'Filter',
          'name': 'Blur',
          'description':'Median Filter',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments': { 
              'kernelSize': {
                'type': 'int[1:100]',
                'defaultValue':25,
                'description': 'kernel size'
              },
              'percentageChange': {
                  'type': 'float[0.01:1]',
                  'defaultValue': 1,
                  'description': 'The size of the randomly chosen area to blur. 1 for the whole image'
              },
              'Blur Type': {
                  'type': 'text',
                  'defaultvalue':'Median Smoothing',
                  'description': ''
              }
          },
          'transitions': [
              'image.image'
          ]
          }
