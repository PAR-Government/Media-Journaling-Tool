
from PIL import Image
import numpy
import cv2
from maskgen import tool_set,image_wrap


def transform(img,source,target,**kwargs):
  image_to_cover = numpy.asarray(img)
  kernalsize = (int(kwargs['kernelsize']),int(kwargs['kernelsize'])) if 'kernelsize' in kwargs else (5, 5)
  kernel = numpy.ones(kernalsize, numpy.uint8)
  if 'inputmaskname' not in kwargs:
    blurred_region = cv2.GaussianBlur(image_to_cover, kernalsize, 0)
    Image.fromarray(blurred_region).save(target)
    return None,None

  mask = tool_set.openImageFile(kwargs['inputmaskname']).to_mask()
  mask_array = numpy.asarray(mask)
  mask_array = cv2.dilate(mask_array, kernel, iterations=5)
  region_to_blur = cv2.bitwise_and(image_to_cover, image_to_cover, mask=mask_array)
  #region_to_keep = cv2.bitwise_and(image_to_cover, image_to_cover, mask=255-mask_array)
  blurred_region = cv2.GaussianBlur(region_to_blur, kernalsize, 0)
  mask_array = cv2.erode(mask_array, kernel, iterations=3)
  flipped_mask= 255-mask_array
  #image_to_cover =cv2.bitwise_or(blurred_region,region_to_keep)
  image_to_cover =  numpy.copy(image_to_cover)
  for c in range(0, 3):
    image_to_cover[:, :, c] = \
      image_to_cover[:, :, c] * \
      (flipped_mask[:, :] / 255) + \
      blurred_region[:, :, c] * \
      (mask_array[:, :]/255)
  Image.fromarray(image_to_cover).save(target)
  return None,None

# the actual link name to be used.
# the category to be shown
def operation():
  return {'name':'Blur',
          'category':'Filter',
          'description':'Gaussian Blur',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments':{
              'inputmaskname':{
                  'type':'imagefile',
                  'defaultvalue':None,
                  'description':'Mask image where black pixels identify region to blur'
              },
              'kernelsize': {
                  'type': 'int[3:101]',
                  'defaultvalue': 5,
                  'description': 'Kernel Size (integer)'
              },
              'Blur Type': {
                  'type': 'text',
                  'defaultvalue': 'Gaussian',
                  'description': ''
          }},
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return None