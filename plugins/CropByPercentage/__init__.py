from PIL import Image
import numpy
from random import randint
from maskgen.image_wrap import  ImageWrapper

def transform(img,source,target,**kwargs):
    cv_image = numpy.array(img)
    shape = cv_image.shape
    snapto8 = 'eightbit_boundary' in  kwargs and kwargs['eightbit_boundary'] == 'yes'
    percentageWidth = float(kwargs['percentage_width'])
    percentageHeight = float(kwargs['percentage_height'])
    pixelWidth = int(shape[1] * percentageWidth)
    pixelHeight = int(shape[0] * percentageHeight)
    if snapto8:
        pixelWidth  = pixelWidth - pixelWidth % 8
        pixelHeight = pixelHeight - pixelHeight % 8
    r_x = randint(1,  pixelWidth) if pixelWidth > 1 else 1
    r_y = randint(1,  pixelHeight) if pixelHeight > 1 else 1
    if snapto8:
      r_x = r_x + (8 - r_x % 8)
      r_y = r_y + (8 - r_y % 8)
    cv_image = numpy.copy(img)
    new_img = cv_image[r_y:-(pixelHeight - r_y), r_x:-(pixelWidth - r_x), :]
    ImageWrapper(new_img).save(target)
    return {'crop_x':r_x,'crop_y':r_y, 'crop_width':pixelWidth,'crop_height':pixelHeight},None

def operation():
  return {
          'category': 'Transform',
          'name': 'TransformCrop',
          'description':'Crop',
          'software':'OpenCV',
          'version':'2.4.13',
          'type': 'selector',
          'arguments':{'percentage_width':
                           {'type': "float[0:0.99]", 'description':'the percentage of pixels to remove horizontal'},
                       'percentage_height':
                           {'type': "float[0:0.99]", 'description':'the percentage of pixels to remove vertically'},
                       'eightbit_boundary':
                           {'type': "yesno", 'defaultvalue':'no', 'description':'Snap to 8 bit boundary'}
                       },
          'transitions': [
              'image.image'
          ]
          }
