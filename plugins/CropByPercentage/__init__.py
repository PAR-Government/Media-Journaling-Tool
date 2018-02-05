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
    # only percentages are too big
    if pixelHeight > shape[0] / 2:
        pixelHeight = shape[0] / 2 - 8
    if pixelWidth > shape[1] / 2:
        pixelWidth = shape[1] / 2 - 8

    start_y = 0
    end_y = shape[0]
    start_x = 0
    end_x = shape[1]
    if snapto8:
        pixelWidth = (pixelWidth + (8 - pixelWidth % 8))
        pixelHeight = (pixelHeight + (8 - pixelHeight % 8))

    # case where width is not cropped
    if pixelWidth > 0:
        if snapto8:
            start_x = randint(1, pixelWidth / 8 - 1) * 8  if pixelWidth > 8 else 0
        else:
            start_x = randint(1, pixelWidth - 1) if pixelWidth > 1 else 0
        end_x = -(pixelWidth - start_x)

    if pixelHeight > 0:
        if snapto8:
            start_y = randint(1, pixelHeight / 8  - 1) * 8  if pixelHeight > 8 else 0
        else:
            start_y = randint(1, pixelHeight - 1) if pixelHeight > 1 else 0
        end_y = -(pixelHeight - start_y)

    new_img = cv_image[start_y:end_y, start_x:end_x, :]
    ImageWrapper(new_img).save(target)
    return {'crop_x':start_x,'crop_y':start_y, 'crop_width':pixelWidth,'crop_height':pixelHeight},None

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
