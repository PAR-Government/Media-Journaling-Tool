# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from maskgen import image_wrap
import numpy as np
from random import randint
from skimage import segmentation
import skimage
import math

"""
Select from a region from a segmented image to produce a selection mask. Can used with paste splice and paste clone.
In the later case, paste_x and paste_y values are returned indicating a suitable  upper left corner paste position in the source image.
"""

def build_mask_box(pixelWidth, pixelHeight, shape):

    if pixelWidth> shape[1]/2:
       pixelWidth=shape[1]/2-1

    if pixelHeight> shape[0]/2:
       pixelHeight=shape[0]/2-1
    
    r_x = randint(1, abs(shape[1] - pixelWidth)-1)
    r_y = randint(1, abs(shape[0] - pixelHeight)-1)

    mask = np.zeros((shape[0], shape[1]))
    mask[r_y:r_y + pixelHeight, r_x:r_x + pixelWidth] = 255

    new_position_x = randint(1, abs(shape[1] - pixelWidth))
    new_position_y = randint(1, abs(shape[0] - pixelHeight))

    return new_position_x,new_position_y, mask


def build(img, segment_labels, unique_labels, label_counts, size_constraint):
    shape = img.shape
    count = 0
    segInd = randint(0, len(unique_labels) - 1)
    segVal = unique_labels[segInd]

    diffs = abs(label_counts - size_constraint)
    best = np.where(diffs==min(diffs))

    segInd = best[0][0]
    segVal = unique_labels[segInd]

    mask = np.zeros((shape[0], shape[1]))
    mask[segment_labels == segVal] = 255

    indices = np.where(mask == 255)
    pixelWidth = abs(max(indices[1]) - min(indices[1]))
    pixelHeight = abs(max(indices[0]) - min(indices[0]))

    if pixelWidth> shape[1]/2:
       pixelWidth=shape[1]/2-1

    if pixelHeight> shape[0]/2:
       pixelHeight=shape[0]/2-1

    new_position_x = randint(1, abs(shape[1] - pixelWidth))
    new_position_y = randint(1, abs(shape[0] - pixelHeight))
    return new_position_x, new_position_y, mask

def build_mask_slic(img, size,W,H):
    shape = img.shape
    imgsize=img.shape[0]*img.shape[1]
    numsegments = imgsize / size
    numsegments = max(numsegments,1)
    segment_labels = segmentation.slic(img, compactness=5, n_segments=numsegments)
    unique_labels, label_counts = np.unique(segment_labels,return_counts=True)
    if len(unique_labels) < 10:
        new_position_x,new_position_y ,mask =  build_mask_box(W,H,shape)
    else:
        new_position_x, new_position_y, mask =  build(img, segment_labels, unique_labels,label_counts,size)
    return new_position_x, new_position_y, mask

def transform(img,source,target,**kwargs):
    smallw = int(kwargs['smallw']) if 'smallw' in  kwargs else 32
    smallh = int(kwargs['smallh']) if 'smallh' in  kwargs else 32
    mediumw = int(kwargs['mediumw']) if 'mediumw' in  kwargs else 64
    mediumh = int(kwargs['mediumh']) if 'mediumh' in  kwargs else 64
    largew = int(kwargs['largew']) if 'largew' in  kwargs else 128
    largeh = int(kwargs['largeh']) if 'largeh' in  kwargs else 128
    size = int(kwargs['size']) if 'size' in  kwargs else 1
    # to support the test, used the abbreviate version
    pasteregionsize = kwargs['region'] if 'region' in kwargs else 1.0
    pasteregionsize = kwargs['region size'] if 'region size' in kwargs else pasteregionsize
    color = map(int,kwargs['savecolor'].split(',')) if 'savecolor' in kwargs and kwargs['savecolor']  is not 'none' else None
    op = kwargs['op'] if 'op' in kwargs else 'box'
    if size ==1:
        W=smallw
        H=smallh
    elif size ==2:
        W=mediumw
        H=mediumh
    else:
        W=largew
        H=largeh
    cv_image = img.to_array()


    if pasteregionsize < 1.0:
        dims = (int(img.size[1] * pasteregionsize), int(img.size[0] * pasteregionsize))
    else:
        dims = (img.size[1], img.size[0])
    x = (img.size[1]-dims[0])/2
    y = (img.size[0]-dims[1])/2
    if len(cv_image.shape) > 2:
        cv_image = cv_image[x:dims[0]+x,y:dims[1]+y,:]
    else:
        cv_image = cv_image[x:dims[0]+x, y:dims[1]+y]

    imgsize = cv_image.shape[0] * cv_image.shape[1]
    
    area = W * H
    if area < (imgsize/2):
        W=smallw
        H=smallh
    
    if op == 'box':
        new_position_x,new_position_y,mask= build_mask_box(W,H,cv_image.shape)
    else:
        new_position_x,new_position_y,mask= build_mask_slic(cv_image,area,W,H)

    if pasteregionsize < 1.0:
        mask2 =np.zeros((img.to_array().shape[0],img.to_array().shape[1]),dtype=np.uint8)
        if len(mask2.shape) > 2:
            mask2[x:dims[0]+x, y:dims[1]+y, :] = mask
        else:
            mask2[x:dims[0]+x, y:dims[1]+y] = mask
        mask = mask2
        new_position_x+=x
        new_position_y+=y
    
    if 'alpha' in kwargs and kwargs['alpha'] == 'yes':
        rgba = np.asarray(img.convert('RGBA'))
        rgba = np.copy(rgba)
        rgba[mask != 255] = 0
        image_wrap.ImageWrapper(rgba).save(target)
    elif color is not None:
        rgb = np.zeros((mask.shape[0],mask.shape[1],3),dtype=np.uint8)
        for channel in range(3):
            rgb[:,:,channel] = (mask/255)*color[channel]
        image_wrap.ImageWrapper(rgb).save(target)
    else:
        image_wrap.ImageWrapper(mask.astype('uint8')).save(target)
    return {'paste_x': new_position_x, 'paste_y': new_position_y},None

def operation():
  return {
          'category': 'Select',
          'name': 'SelectRegion',
          'description':'Select from a region from a segmented image to produce a selection mask. Can used with paste splice and paste clone.  In the later case, paste_x and paste_y variables are returned indicating a suitable  upper left corner paste position in the source image. ',
          'software':'skimage',
          'version':skimage.__version__,
          'arguments':{'smallw': {'type': "int[32:64]", 'defaultValue': 32, 'description':'small mask width size'},
                       'smallh': {'type': "int[32:64]",  'defaultValue': 32,'description':'small mask height size'},
                       'mediumw': {'type': "int[64:128]",  'defaultValue': 64, 'description':'medium mask width size'},
                       'mediumh': {'type': "int[64:128]", 'defaultValue': 64, 'description':'medium mask width size'},
                       'largew': {'type': "int[128:1000]",'defaultValue': 128, 'description':'large mask width size'},
                       'largeh': {'type': "int[128:1000]", 'defaultValue': 128,'description':'large mask width size'},
                       'size': {'type': "int[1:4]",'defaultValue': 1, 'description':'mask size 1=small, 2=med, 3=large'},
                       'op': {'type': 'list', 'values' : ['slic', 'box'], 'description':'selection algorithm to use'},
                       'alpha': {'type' : "yesno",
                                      "defaultvalue": "no",
                                      'description': "If yes, save the image with an alpha channel instead of the mask."},
                       "savecolor": {'type' : "text",
                                      "defaultvalue": "none",
                                      'description': "color value in rgb 100,100,100  for color mask generation."}
                       },
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return '.png'
