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
    percentageWidth = float(kwargs['percentage_width'])
    percentageHeight = float(kwargs['percentage_height'])
    divisionsWidth = float(kwargs['divisions_width'] if 'divisions_width' in kwargs else shape[1])
    divisionsHeight = float(kwargs['divisions_height'] if 'divisions_height' in kwargs else shape[0])
    pixelWidth = int(shape[1] * percentageWidth)
    pixelHeight = int(shape[0] * percentageHeight)
    if snapto8:
        pixelWidth  = pixelWidth - pixelWidth % 8
        pixelHeight = pixelHeight - pixelHeight % 8
    incrementsWidth = max(8,int(pixelWidth/divisionsWidth))
    incrementsHeight = max(8,int(pixelHeight/divisionsHeight))
    crop_x = { "type": "list", "values" : [i for i in xrange(incrementsWidth,pixelWidth,incrementsWidth)]}
    crop_y = { "type": "list", "values" : [i for i in xrange(incrementsHeight, pixelHeight, incrementsHeight)]}
    return {'crop_x':crop_x,'crop_y':crop_y, 'crop_width':pixelWidth,'crop_height':pixelHeight},None

def operation():
  return {
          'category': 'Select',
          'name': 'SelectRegion',
          'description':'Select a region to crop',
          'software':'OpenCV',
          'version':'2.4.13',
          'type':'selector',
          'arguments':{'percentage_width':
                           {'type': "float[0:0.5]", 'description':'the percentage of pixels to remove horizontal'},
                       'percentage_height':
                           {'type': "float[0:0.5]", 'description':'the percentage of pixels to remove vertically'},
                       'divisions_width':
                           {'type': "int[0:100000]", 'description': 'the number samples in the x direction'},
                       'divisions_height':
                           {'type': "int[0:100000]", 'description': 'the number of samples in the y direction'},
                       'eightbit_boundary':
                           {'type': "yesno", 'defaultvalue':'no', 'description':'Snap to 8 bit boundary'}
                       },
         'output':
              {'crop_x': {
                  'type': 'list',
                  'description': 'upper corner pixel location to start crop'
              },
              'crop_y': {
                  'type': 'list',
                  'description': 'upper corner pixel location to start crop'
              }
              ,
              'crop_width': {
                  'type': 'int',
                  'description': 'witdh in pixels of crop region'
              },
              'crop_height': {
                  'type': 'int',
                  'description': 'witdh in pixels of crop region'
              }
          },
          'transitions': [
              'image.image'
          ]
          }
