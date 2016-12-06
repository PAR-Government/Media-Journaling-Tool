
from PIL import Image
import numpy
import cv2
from maskgen import tool_set,image_wrap


def transform(img,source,target,**kwargs):
  image_to_cover = numpy.asarray(img)
  kernalsize = tool_set.toIntTuple(kwargs['kernelsize']) if 'kernelsize' in kwargs else (5, 5)
  kernel = numpy.ones(kernalsize, numpy.uint8)
  if 'inputmaskname' not in kwargs:
    blurred_region = cv2.GaussianBlur(image_to_cover, kernalsize, 0)
    Image.fromarray(blurred_region).save(target)
    return None,None

  mask = tool_set.openImageFile(kwargs['inputmaskname']).to_mask().invert()
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
  return ['AdditionalEffectFilterBlur','AdditionalEffect','Gaussian Blur','OpenCV','2.4.13']

def args():
   return [('inputmaskname',None,'Mask image where black pixels identify region to blur')]

def suffix():
    return None