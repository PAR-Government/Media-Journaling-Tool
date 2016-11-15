
from PIL import Image
import numpy
import cv2
from maskgen import tool_set,image_wrap


def transform(img,source,target,**kwargs):
  img_array = numpy.asarray(img)

  mask = image_wrap.ImageWrapper(tool_set.openImageFile(kwargs['inputmaskname'])).to_mask().invert() \
     if 'inputmaskname' in kwargs else image_wrap.ImageWrapper(numpy.ones(img_array.shape)*255)

  kernalsize = tool_set.toIntTuple(kwargs['kernelsize']) if 'kernelsize' in kwargs else (5,5)
  mask_array = numpy.asarray(mask)

  kernel = numpy.ones(kernalsize,numpy.uint8)
  mask_array = cv2.dilate(mask_array, kernel, iterations=5)
  region_to_blur = cv2.bitwise_and(img_array, img_array, mask=mask_array)
  region_to_keep = cv2.bitwise_and(img_array, img_array, mask=255-mask_array)
  blurred_region = cv2.GaussianBlur(region_to_blur, kernalsize, 0)
  image_array = cv2.bitwise_or(blurred_region, region_to_keep)
  Image.fromarray(image_array).save(target)
  return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['AdditionalEffectFilterBlur','AdditionalEffect','Gaussian Blur','OpenCV','2.4.13']

def args():
  return None

def suffix():
    return None