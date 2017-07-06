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
Return variables paste_x and paste_y for placement in the same image (e.g. paste clone).
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
    mask = numpy.zeros((denoise_img.shape[0],denoise_img.shape[1]), numpy.uint8)
    cv2.fillPoly(mask, pts=[cnt[0]], color=255)
    if 'alpha' not in kwargs or kwargs['alpha'] == 'yes':
        rgba = numpy.asarray(img.convert('RGBA'))
        rgba = numpy.copy(rgba)
        rgba[mask != 255] = 0
        ImageWrapper(rgba).save(target)
    else:
        ImageWrapper(mask.astype('uint8')).save(target)

    shape = mask.shape
    x, y, w, h = cv2.boundingRect(cnt[0])
    trial_boxes = [
        [0, 0, x, shape[0] - h],
        [0, 0, shape[1] - w, y],
        [x + w, 0, shape[1] - w, shape[0] - h],
        [0, y + h, shape[1] - w, shape[0] - h]
    ]

    boxes = [box for box in trial_boxes \
             if (box[2] - box[0]) > 0 and (box[3] - box[1]) > 0]

    if len(boxes) == 0:
        box = [1, 1, shape[1] - w, shape[0] - h]
    else:
        box = choice(boxes)

    new_position_x = randint(box[0], box[2])
    new_position_y = randint(box[1], box[3])
    return {'paste_x': new_position_x, 'paste_y': new_position_y}, None

# the actual link name to be used. 
# the category to be shown
def operation():
  return {'name':'SelectRegion',
          'category':'Select',
          'description':'Denoise and segment the image to find selection from the image. Output the image using the alpha channel indicating the selection.',
          'software':'OpenCV',
          'version':'2.4.13',
          'arguments': {'alpha': {'type' : "yesno",
                                      "defaultvalue": "yes",
                                      'description': "If yes, save the image with an alpha channel instead of the mask."}},
          'transitions': [
              'image.image'
              ]
          }

def suffix():
    return None

