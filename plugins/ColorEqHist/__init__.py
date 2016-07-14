import cv2
from PIL import Image
import numpy

def transform(img):
  img = img.convert("RGB")
  img_yuv = cv2.cvtColor(numpy.asarray(img), cv2.COLOR_RGB2YUV)
  # equalize the histogram of the Y channel
  img_yuv[:,:,0] = cv2.equalizeHist(img_yuv[:,:,0])
  # convert the YUV image back to RGB format
  return Image.fromarray(cv2.cvtColor(img_yuv, cv2.COLOR_YUV2RGB))

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['ColorColorBalance','Color','Equalize Colors using Histogram over the Chrominance Channel','OpenCV','2.4.13']

