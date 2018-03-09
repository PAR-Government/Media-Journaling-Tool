# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================

from maskgen import image_wrap,cv2api
import numpy as np
import cv2

"""
Functions to support working with segmented images
"""

def find_segmentation_classifier(image_name,segmentation_directory):
    import os
    real_name = os.path.split(image_name)[0]
    dotpos = min(33,real_name.find('.'))
    real_name = real_name[0:dotpos]
    segment_name = os.path.join(segmentation_directory,real_name + '.png')
    return image_wrap.openImageFile(segment_name) if os.path.exists(segment_name) else None

def segmentation_classification(segmentation_directory, color):
    import os
    import csv
    fn = os.path.join(segmentation_directory,'classifications.csv')
    if os.path.exists(fn):
        with open(fn,'r') as fp:
            reader = csv.reader(fp)
            for line in reader:
                if line[0].replace(' ','') == str(color).replace(' ',''):
                    return line[1]
    return 'other'

def convert_color(color):
    import re
    if color is None  or color == 'None':
        return None
    strcolor = str(color)
    strcolor = re.sub('[\[\]\,]', ' ',strcolor)
    strcolor.replace('[]',' ')
    return [ int(item) for item in strcolor.split(' ') if item != '']

def select_region(img, mask, color=None):
    """
    Given a color mask and image and a given color,
    create an alpha channel on the given image, exposing only the regions
    associated with the color mask matching the given color.
    If the color is not provided, choose one of the available colors in the mask.
    Return the RGBA image and the color.
    :param img:
    :param mask:
    :return:
    @type img: image_wrap.ImageWrapper
    @type mask: image_wrap.ImageWrapper
    """
    rgba = img.convert('RGBA').to_array()
    mask = mask.to_array()
    channel = np.zeros((mask.shape[0],mask.shape[1])).astype('uint8')
    if color is None or color == 'None':
        colors = np.unique(np.vstack(mask).view([('', mask.dtype)] * np.prod(np.vstack(mask).shape[1])))
        colors = [color for color in colors.tolist()]
        colors.remove((0, 0, 0))
        color = colors[np.random.randint(0,len(colors)-1)]

    channel[np.all(mask==[color[0],color[1],color[2]],axis=2)] = 255
    (contours, _) = cv2api.findContours(channel.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    for cnt in contours:
        if len(cnt) > 3:
            channel = np.zeros((mask.shape[0], mask.shape[1])).astype('uint8')
            cv2.fillConvexPoly(channel,cnt,255)
            break
    rgba[:,:,3] = channel
    return image_wrap.ImageWrapper(rgba),color