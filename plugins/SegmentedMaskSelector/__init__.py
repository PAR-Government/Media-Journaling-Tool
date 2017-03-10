import numpy
import cv2
import random
from maskgen.image_wrap import ImageWrapper
from skimage.restoration import denoise_tv_bregman
from skimage.segmentation import felzenszwalb
import math
from random import choice,randint

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

    dims = (math.ceil(denoise_img.shape[0] / 500.0) * 500.0,math.ceil(denoise_img.shape[1] / 500.0) * 500.0)
    sigma = max(0.75,math.log10(dims[0]*dims[1]/10000.0) - 0.5)
    min_size = max(100.0,math.ceil(sigma*10.0)*10)
    segments_fz = felzenszwalb(gray, scale=min_size, sigma=sigma, min_size=int(min_size))

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
    max_mask = numpy.zeros((denoise_img.shape[0],denoise_img.shape[1]), numpy.uint8)
    cv2.fillPoly(max_mask, pts=[cnt[0]], color=255)
    rgba = numpy.asarray(img.convert('RGBA'))
    rgba = numpy.copy(rgba)
    rgba[max_mask != 255] = 0
    ImageWrapper(rgba).save(target)

    shape = rgba.shape
    x, y, w, h = cv2.boundingRect(cnt[0])
    trial_boxes = [
        [0, 0, x , shape[0] - h],
        [0, 0, shape[1] - w, y],
        [x + w, 0, shape[1] - w, shape[0] - h],
        [0, y + h, shape[1] - w, shape[0] - h]
    ]

    boxes = [box for box in trial_boxes \
             if (box[2] - box[0]) > 0 and (box[3] - box[1]) > 0]

    maxbox = 0
    maxboxid = 0
    pos = 0
    for box in trial_boxes:
        area = (box[2] - box[0]) * (box[3] - box[1])
        if area > maxbox:
            maxbox = area
            maxboxid = pos
        pos += 1

    box = choice(boxes) if len(boxes) > 0 else trial_boxes[maxboxid]

    new_position_x = randint(box[0], box[2])
    new_position_y = randint(box[1], box[3])
    return {'paste_x': new_position_x, 'paste_y': new_position_y}, None


# the actual link name to be used. 
# the category to be shown
def operation():
  return {'name':'SelectRegion',
          'category':'Select',
          'description':'Apply a mask to create an alpha channel for an auto-selected region',
          'software':'OpenCV',
          'version':'2.4.13',
          'arguments': None,
          'transitions': [
              'image.image'
              ]
          }

def suffix():
    return None
