import cv2
from PIL import Image
import numpy

def transform(img,source,target,**kwargs):
    rgba = img.convert('RGBA')
    inputmask = Image.open(kwargs['inputmaskname'])
    if inputmask.size != rgba.size:
      rgba = rgba.resize(inputmask.size, Image.ANTIALIAS)
    cv_image = numpy.array(rgba)
    mask = numpy.array(inputmask)
    bmask = mask>0
    for i in range(4): 
      cv_image[:,:,i][bmask]=0
    Image.fromarray(cv_image,'RGBA').save(target)
    return True

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['SelectRemove','Select','Apply a mask to create an alpha channel','OpenCV','2.4.13']

def args():
  return [('inputmaskname',None)]

