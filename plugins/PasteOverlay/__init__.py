from maskgen.image_wrap import ImageWrapper, openImageFile
import numpy as np
import maskgen

"""
Create an intermediate image given the final image, after a paste splice blend, source image and a mask.
"""
def transform(img,source,target, **kwargs):
    pastemask = openImageFile(kwargs['inputmaskname']).to_array()
    finalimage = openImageFile(kwargs['Final Image']).to_array()
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
    return None,None
    
def operation():
    return {'name':'PasteSplice',
            'category':'Paste',
            'software': 'maskgen',
            'version': maskgen.__version__[0:2],
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
