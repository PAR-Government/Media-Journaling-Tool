import cv2
from PIL import Image
import numpy

kernel = numpy.ones((5,5),numpy.float32)/25

def transform(img,imgfilename,**kwargs):
    rgb = img.convert('RGBA')
    cv_image = numpy.array(rgb)
    Image.fromarray(cv2.filter2D(cv_image,-1,kernel),'RGBA').save(imgfilename)
    return True

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['ColorColorBalance','Color','Average convolution over the RGB values of an image given a 5x5 convolution','OpenCV','2.4.13']

def args():
  return None

