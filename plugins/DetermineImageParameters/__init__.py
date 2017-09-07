from maskgen import image_wrap
import numpy as np
import maskgen

"""
Determine new parameters based on an image's current metrics (qualify factor, size, etc.)
"""


def transform(img,source,target,**kwargs):
    if 'donor' in kwargs:
        img = image_wrap.openImageFile(kwargs['donor'])
    w_c = float(kwargs['percentage_width'])
    h_c = float(kwargs['percentage_height'])
    cv_image = np.asarray(img.to_array())
    h = int (cv_image.shape[0] * h_c)
    w = int(cv_image.shape[1] * w_c)
    return {'selected_width': w, 'selected_height': h, 'quality_factor': 80},None

def operation():
  return {
          'category': 'Select',
          'name': 'SelectRegion',
          'description':'Select from a region from a segmented image to produce a selection mask. Can used with paste splice and paste clone.  In the later case, paste_x and paste_y variables are returned indicating a suitable  upper left corner paste position in the source image. ',
          'software':'maskgen',
          'version':maskgen.__version__,
          'arguments':{'percentage_width': {'type': "float[0.01:2]", 'description':'percentage change'},
                       'percentage_height': {'type': "float[0.01:2]", 'description': 'percentage change'}
                       },
          'transitions': [
              'image.image'
          ]
          }

def suffix():
    return '.png'
