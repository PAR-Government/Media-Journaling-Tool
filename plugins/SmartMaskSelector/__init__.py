from maskgen import image_wrap
import numpy as np
from random import randint
from skimage import segmentation

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

    while label_counts[segInd] > size_constraint * 1.5 and label_counts[segInd] < size_constraint * .5 and count < 20:
        tempsegInd = randint(0, len(unique_labels) - 1)
        tempsegVal = unique_labels[tempsegInd]
        if label_counts[segInd] > label_counts[tempsegInd]:
            segVal = tempsegVal
            segInd = tempsegInd
        count = count + 1

    mask = np.zeros((shape[0], shape[1]))
    mask[segment_labels == segVal] = 255

    indices = np.where(mask == 255)
    pixelWidth = abs(max(indices[1]) - min(indices[1]))
    pixelHeight = abs(max(indices[0]) - min(indices[0]))

    new_position_x = randint(1, abs(shape[1] - pixelWidth))
    new_position_y = randint(1, abs(shape[0] - pixelHeight))
    return new_position_x, new_position_y, mask

def build_mask_slic(img, size,W,H):
    shape = img.shape
    imgsize=img.shape[0]*img.shape[1]
    numsegments = imgsize / size
    segment_labels = segmentation.slic(img, compactness=5, n_segments=numsegments)
    unique_labels, label_counts = np.unique(segment_labels,return_counts=True)
    if len(unique_labels) < 10:
        new_position_x,new_position_y ,mask =  build_mask_box(W,H,shape)
    else:
        new_position_x, new_position_y, mask =  build(img, segment_labels, unique_labels,label_counts,size)

    return new_position_x, new_position_y, mask

def transform(img,source,target,**kwargs):
    smallw = int(kwargs['smallw'])
    smallh = int(kwargs['smallh'])
    mediumw = int(kwargs['mediumw'])
    mediumh = int(kwargs['mediumh'])
    largew = int(kwargs['largew'])
    largeh = int(kwargs['largeh'])
    size = int(kwargs['size'])
    op = int(kwargs['op'])

    if size ==1:
        W=smallw
        H=smallh
    elif size ==2:
        W=mediumw
        H=mediumh
    else:
        W=largew
        H=largeh
    cv_image = np.asarray(img.to_array())
    if op==1:
      new_position_x,new_position_y,mask= build_mask_box(W,H,cv_image.shape)
    else:
      area = W*H
      new_position_x,new_position_y,mask= build_mask_slic(cv_image,area,W,H)

    if 'alpha' in kwargs and kwargs['alpha'] == 'yes':
        rgba = np.asarray(img.convert('RGBA'))
        rgba = np.copy(rgba)
        rgba[mask != 255] = 0
        image_wrap.ImageWrapper(rgba).save(target)
    else:
        image_wrap.ImageWrapper(mask.astype('uint8')).save(target)
    return {'paste_x': new_position_x, 'paste_y': new_position_y},None

def operation():
  return {
          'category': 'Select',
          'name': 'SelectRegion',
          'description':'Select from a region from a segmented image to produce a selection mask. Can used with paste splice and paste clone.  In the later case, paste_x and paste_y variables are returned indicating a suitable  upper left corner paste position in the source image. ',
          'software':'skimage',
          'version':'2.4.13',
          'arguments':{'smallw': {'type': "int[32:64]", 'description':'small mask size'},
                       'smallh': {'type': "int[32:64]", 'description':'small mask size'},
                       'mediumw': {'type': "int[64:128]", 'description':'medium mask size'},
                       'mediumh': {'type': "int[64:128]", 'description':'medium mask size'},
                       'largew': {'type': "int[128:1000]", 'description':'large mask size'},
                       'largeh': {'type': "int[128:1000]", 'description':'large mask size'},
                       'size': {'type': "int[1:4]", 'description':'mask size 1=small, 2=med, 3=large'},
                       'op': {'type': "int[1:3]", 'description':'op 1=box, 2=segmentation boundry'},
                       'alpha': {'type' : "yesno",
                                      "defaultvalue": "no",
                                      'description': "If yes, save the image with an alpha channel instead of the mask."}
                       },
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return '.png'
