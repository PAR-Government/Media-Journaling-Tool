from PIL import Image
import numpy
from random import randint

def transform(img,source,target,**kwargs):
    cv_image = numpy.array(img)
    shape = cv_image.shape
    percentageWidth = float(kwargs['percentage_width'])
    percentageHeight = float(kwargs['percentage_height'])
    pixelWidth = int(shape[1] * percentageWidth)
    pixelHeight = int(shape[0] * percentageHeight)
    r_x = randint(1,  pixelWidth) if pixelWidth > 1 else 1
    r_y = randint(1,  pixelHeight) if pixelHeight > 1 else 1

    mask = numpy.zeros((cv_image.shape[0], cv_image.shape[1]))
    mask[r_y:-(pixelHeight-r_y), r_x:-(pixelWidth-r_x)] = 255
    Image.fromarray(mask.astype('uint8')).save(target)
    return {'crop_x':r_x,'crop_y':r_y, 'crop_width':pixelWidth,'crop_height':pixelHeight},None

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
                           {'type': "float[0:0.5]", 'description':'the percentage of pixels to remove vertically'}},
          'transitions': [
              'image.image'
          ]
          }
