# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from skimage.restoration import wiener
from scipy.signal import convolve2d
from skimage import color, data, restoration
import cv2
from PIL import Image
import numpy
from maskgen import tool_set



def transform(img,source,target,**kwargs):
    kernelSize = int(kwargs['kernelSize']) if 'kernelSize' in kwargs else 25
    rgb = img.convert('RGB')
    cv_image = numpy.array(rgb)
    if 'inputmaskname' in kwargs:
        mask = numpy.asarray(tool_set.openImageFile(kwargs['inputmaskname']).to_mask())
        mask[mask>0] == 1
    else:
        mask = numpy.ones((cv_image.shape[0],cv_image.shape[1])).astype('uint8')
    inverted_mask = numpy.ones((cv_image.shape[0], cv_image.shape[1])).astype('uint8')
    inverted_mask[mask==1] = 0
    side = int(kernelSize**(1/2.0))
    psf = numpy.ones((side, side)) / kernelSize
    img = color.rgb2grey(cv_image)
    deconvolved_img = restoration.wiener(img, psf, 1)[0]
    for c in range(3):
        cv_image[:,:,c] =deconvolved_img* cv_image[:,:,c] * mask + cv_image[:,:,c] * inverted_mask
    Image.fromarray(cv_image,'RGB').save(target)
    return {'Blur Type':'Wiener'}, None

def operation():
  return {
          'category': 'Filter',
          'name': 'Blur',
          'description':'Wiener Filter',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments':{
              'kernelSize': {
                  'type': 'int[1:100]',
                  'defaultValue': 25,
                  'description': 'kernel size'
              },
              'inputmaskname':{
                  'type':'imagefile',
                  'defaultvalue':None,
                  'description':'Mask image where black pixels identify region to blur'
              },
              'Blur Type': {
                  'type': 'text',
                  'defaultvalue':'Wiener',
                  'description': ''
            }},
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return None