import numpy
import cv2
import random
from maskgen.image_wrap import ImageWrapper
from skimage.restoration import denoise_tv_bregman
from skimage.segmentation import felzenszwalb

"""
Select region from the image.
Add an alpha channel to the image.
Set the alpha channel pixels to 0 for the unselected portion of the image.
"""

def transform(img,source,target,**kwargs):
    denoise_img = denoise_tv_bregman(numpy.asarray(img), weight=0.4)
    denoise_img = (denoise_img * 255).astype('uint8')
    gray = cv2.cvtColor(denoise_img, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    segments_fz = felzenszwalb(denoise_img, scale=100, sigma=0.5, min_size=50)

    cnts = []
    for label in numpy.unique(segments_fz):
        mask = numpy.zeros(gray.shape, dtype="uint8")
        mask[segments_fz == label] = 255
        cnts.extend(cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,
                                     cv2.CHAIN_APPROX_SIMPLE)[-2])


    areas = [(cnt, cv2.contourArea(cnt)) for cnt in cnts
              if  cv2.moments(cnt)['m00'] > 2.0 ]
    cnts = sorted(areas, key=lambda cnt: cnt[1], reverse=True)
    cnts = cnts[0: min(15,len(cnts))]
    cnt = random.choice(cnts)
    max_mask = numpy.zeros(denoise_img.shape, numpy.uint8)
    cv2.fillPoly(max_mask, pts=[cnt[0]], color=(255, 255, 255))
    rgba = numpy.asarray(img.convert('RGBA'))
    rgba = numpy.copy(rgba)
    rgba[numpy.all(max_mask!=[255,255,255],axis=2),3] = 0
    ImageWrapper(rgba).save(target)
    return None,None

# the actual link name to be used. 
# the category to be shown
def operation():
  return {'name':'SelectRegion',
          'category':'Select',
          'description':'Apply a mask to create an alpha channel',
          'software':'OpenCV',
          'version':'2.4.13',
          'arguments': None,
          'transitions': [
              'image.image'
              ]
          }

# def args():
#   return []

def suffix():
    return None

