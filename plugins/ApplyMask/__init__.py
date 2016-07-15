import cv2
from PIL import Image
import numpy

def transform(img,**kwargs):
    rgba = img.convert('RGBA')
    inputmask = Image.open(kwargs['inputmaskpathname'])
    if inputmask.size != rgba.size:
      rgba = rgba.resize(inputmask.size, Image.ANTIALIAS)
    cv_image = numpy.array(rgba)
    mask = numpy.array(inputmask)
    bmask = mask>0
    for i in range(4): 
      cv_image[:,:,i][bmask]=0
    return Image.fromarray(cv_image,'RGBA')

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['SelectRemove','Select','Apply a mask to create an alpha channel','OpenCV','2.4.13']

def args():
  return [('inputmaskpathname',None)]

