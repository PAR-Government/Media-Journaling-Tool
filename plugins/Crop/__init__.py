import numpy
from maskgen.image_wrap import ImageWrapper

def transform(img,source,target,**kwargs):
    pixelWidth = int(kwargs['pixel_width'])
    pixelHeight = int(kwargs['pixel_height'])
    x = int(kwargs['crop_x'])
    y = int(kwargs['crop_y'])
    cv_image = numpy.array(img)
    #new_img = numpy.zeros((cv_image.shape[0]-pixelWidth, cv_image.shape[1]-pixelHeight,cv_image.shape[2])).astype('uint8')
    new_img = cv_image[y:-(pixelHeight-y), x:-(pixelWidth-x),:]
    ImageWrapper(new_img).save(target)
    return None,None

def operation():
  return {
          'category': 'Transform',
          'name': 'TransformCrop',
          'description':'Crop',
          'software':'OpenCV',
          'version':'2.4.13',
          'arguments':{'crop_x': {'type': "int[0:100000]", 'description':'upper left corner vertical position'},
                       'crop_y': {'type': "int[0:100000]", 'description':'upper left corner horizontal position'},
                       'pixel_width': {'type': "int[0:100000]", 'description':'amount of pixels to remove horizontal'},
                       'pixel_height': {'type': "int[0:100000]", 'description':'amount of pixels to remove vertically'}},
          'transitions': [
              'image.image'
          ]
          }
