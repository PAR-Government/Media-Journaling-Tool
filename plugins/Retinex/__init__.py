# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from maskgen import image_wrap
import numpy
from maskgen import __version__ as mversion
from maskgen.algorithms.retinex import *

def transform(img,source,target,**kwargs):
    source_im = numpy.asarray(img)

    def toColorBalanceFromPercentage(val):
        return (float(val),1.0-(val))

    algorithm = MultiScaleResinexChromaPerservation if 'algorithm' in kwargs and \
                                                       kwargs['algorithm'] == 'Chroma Preserving' else MultiScaleResinexLab


    colorBalance = toColorBalanceFromPercentage(float(kwargs['color balance'])) if 'color balance' in kwargs else (0.01, 0.99)

    algorithm_instance = algorithm([15, 80, 125],
                                   G=30,
                                   b=-6,
                                   alpha=125.0,
                                   beta=1.0,
                                   colorBalance=colorBalance
                                   )
    image_wrap.ImageWrapper(algorithm_instance(source_im)).save(target)

    return None,None

def operation():
  return {
          'category': 'Intensity',
          'name': 'Contrast',
          'description':'Color Constancy',
          'software':'maskgen',
          'version':mversion,
          'arguments':{
              'color balance':{
                  'type':'float[0.0:1.0]',
                  'defaultvalue':0.01,
                  'description':'The amount of intensity values clip on either end of the distribution prior to normalization'
              },
	          'algorithm':{
                  'type': 'list',
                  'values' : ['Chroma Preserving', 'Lab'],
                  'defaultvalue':'Lab',
                  'description':'Chroma Preserving averages the intensity across RGB. Lab uses the LAB color space.'
              }},
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return None