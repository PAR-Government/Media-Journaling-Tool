import cv2
from PIL import Image
import numpy

kernel = numpy.ones((5,5),numpy.float32)/25

def transform(img):
    rgb = img.convert('RGBA')
    cv_image = numpy.array(rgb)
    return Image.fromarray(cv2.filter2D(cv_image,-1,kernel),'RGBA')

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['ColorColorBalance','Color','Average convolution over the RGB values of an image given a 5x5 convolution']

