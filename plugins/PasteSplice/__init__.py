from PIL import Image
import numpy
import cv2
import random
from maskgen.image_wrap import ImageWrapper

def transform(img,source,target,**kwargs):
    gray = numpy.asarray( img.convert('L')).astype('uint8')
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    edged = cv2.Canny(gray, 30, 200)
    (cnts, _) = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)
    cnt = random.choice(cnts)
    mask = numpy.zeros(gray.shape, numpy.uint8)
    cv2.drawContours(mask, [cnt], 0, 255, -1)
    rgba = numpy.asarray(img.convert('rgba'))
    rgba[:,:,3] = mask
    ImageWrapper(rgba).save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['PasteSplice','Paste','Apply a mask to create an alpha channel','OpenCV','2.4.13']

def args():
  return [('inputimagename',None,'Mask to set alpha channel to 0')]

def suffix():
    return None