import cv2
from PIL import Image
import numpy

kernel = numpy.ones((5,5),numpy.float32)/25

def transform(img,source,target,**kwargs):
    rgb = img.convert('RGBA')
    cv_image = numpy.array(rgb)
    Image.fromarray(cv2.filter2D(cv_image,-1,kernel),'RGBA').save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return {'name':'ColorBalance',
          'category':'Color',
          'description':'Average convolution over the RGB values of an image given a 5x5 convolution',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments': None,
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return None


