import numpy
from maskgen.image_wrap import ImageWrapper
import cv2

def transform(img,source,target,**kwargs):
    pixelWidth = int(kwargs['pixel_width'])
    pixelHeight = int(kwargs['pixel_height'])
    x = int(kwargs['crop_x'])
    y = int(kwargs['crop_y'])
    cv_image = numpy.array(img)
    new_img = cv_image[y:(pixelHeight+y), x:(pixelWidth+x),:]
    ImageWrapper(new_img).save(target)
    return None,None

def suffix():
    return None

def operation():
  return {
          'category': 'Transform',
          'name': 'TransformCrop',
          'description':'Crop',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments':{'crop_x': {'type': "int[0:100000]", 'description':'upper left corner vertical position'},
                       'crop_y': {'type': "int[0:100000]", 'description':'upper left corner horizontal position'},
                       'pixel_width': {'type': "int[0:100000]", 'description':'amount of pixels horizontal'},
                       'pixel_height': {'type': "int[0:100000]", 'description':'amount of pixels vertically'}},
          'transitions': [
              'image.image'
          ]
          }
