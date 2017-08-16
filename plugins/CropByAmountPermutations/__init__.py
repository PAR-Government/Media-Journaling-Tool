from PIL import Image
import numpy
from random import randint

"""
A plugin used to create a set of variable spefications for permutation groups.
"""

def transform(img,source,target,**kwargs):
    cv_image = numpy.array(img)
    shape = cv_image.shape
    snapto8 = 'eightbit_boundary' in  kwargs and kwargs['eightbit_boundary'] == 'yes'
    percentageWidth = float(kwargs['divisions_width'])
    percentageHeight = float(kwargs['divisions_height'])
    pixelWidth = int(shape[1] * percentageWidth)
    pixelHeight = int(shape[0] * percentageHeight)
    if snapto8:
        pixelWidth  = pixelWidth - pixelWidth % 8
        pixelHeight = pixelHeight - pixelHeight % 8
    crop_x = { "type": "list", "values" : [i for i in xrange(8,pixelWidth,8)]}
    crop_y = { "type": "list", "values" : [i for i in xrange(8, pixelHeight, 8)]}
    return {'crop_x':crop_x,'crop_y':crop_y, 'crop_width':pixelWidth,'crop_height':pixelHeight},None

def operation():
  return {
          'category': 'Select',
          'name': 'SelectRegion',
          'description':'Select a region to crop',
          'software':'OpenCV',
          'version':'2.4.13',
          'arguments':{'percentage_width':
                           {'type': "float[0:0.5]", 'description':'the percentage of pixels to remove horizontal'},
                       'percentage_height':
                           {'type': "float[0:0.5]", 'description':'the percentage of pixels to remove vertically'},
                       'eightbit_boundary':
                           {'type': "yesno", 'defaultvalue':'no', 'description':'Snap to 8 bit boundary'}
                       },
          'transitions': [
              'image.image'
          ]
          }
