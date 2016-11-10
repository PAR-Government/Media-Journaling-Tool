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
    areas = [(cnt, cv2.contourArea(cnt)) for cnt in cnts]
    cnts = sorted(areas, key=lambda cnt: cnt[1], reverse=True)
    cnts = [cnt[0] for cnt in cnts if cnt[1] > 2.0]
    count = 0
    max_value = 0
    max_mask = None
    while count < 10:
        cnt = random.choice(cnts)
        mask = numpy.zeros(gray.shape, numpy.uint8)
        cv2.drawContours(mask, [cnt], 0, 255, -1)
        v = numpy.histogram(mask, bins=2)[0][1]
        if v > max_value:
            max_mask = mask
            max_value  = v
        count += 1
    rgba = numpy.asarray(img.convert('RGBA'))
    rgba = numpy.copy(rgba)
    rgba[:,:,3] = max_mask
    ImageWrapper(rgba).save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return ['SelectRegion','Select','Apply a mask to create an alpha channel','OpenCV','2.4.13']

def args():
  return []

def suffix():
    return None