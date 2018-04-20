# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from maskgen.image_wrap import ImageWrapper, openImageFile
import numpy as np
import maskgen
from maskgen.tool_set import createMask
import logging
import os
"""
Create an intermediate image given the final image, after a paste splice blend, source image and a mask.
"""
def transform(img,source,target, **kwargs):
    finalimage = openImageFile(kwargs['Final Image'])
    output  = None
    if 'inputmaskname' not in kwargs:
        pastemask, analsys, error = createMask(img,finalimage)
        if error:
            logging.getLogger('maskgen').error("Error creating inputmask " + error)
        splits = os.path.split(source)
        pastemask.invert()
        pastemask.save(splits[0] + '_inputmask.png')
        pastemask = pastemask.to_array()
        output = {'inputmaskname':splits[0] + '_inputmask.png'}
    else:
        pastemask = openImageFile(kwargs['inputmaskname']).to_array()
    finalimage = finalimage.to_array()
    sourceimg = np.copy(img.to_array()).astype('float')
    if len(pastemask.shape) > 2:
        if pastemask.shape[2] > 3:
            mult = pastemask[:,:,3]/255.0
        else:
            mult = pastemask[:,:,1]/255.0
    else:
        mult = pastemask / 255.0
    for dim in range(sourceimg.shape[2]):
        sourceimg[:,:,dim] = \
             (sourceimg[:,:,dim]*(1.0-mult)).astype('uint8') + \
             (finalimage[:,:,dim]*(mult)).astype('uint8')
    ImageWrapper(sourceimg.astype('uint8')).save(target)
    return output,None
    
def operation():
    return {'name':'PasteSplice',
            'category':'Paste',
            'software': 'maskgen',
            'version': maskgen.__version__[0:3],
            'arguments':{
                'inputmaskname': {
                    "type": "file:image",
                    "description": "An image file containing a mask describing the area pasted into."
                },
                'donor': {
                    "type": "donor",
                    "description": "Image to paste."
                },
                'Final Image': {
                    "type": "file:image",
                    "description": "Final Result of the manipulation."
                },
                'purpose': {
                    'type':'list',
                    'values': ['blend'],
                    'defaultvalue' : 'blend',
                    'visible': False
                },
                'mode': {
                    'type': 'text',
                    'defaultvalue':'Luminosity'
                }
           },
           'description': 'Create an intermediate image given the final image, after a paste splice blend, source image and a mask.',
            'transitions': [
                'image.image'
            ]
         }

def suffix():
    return None
