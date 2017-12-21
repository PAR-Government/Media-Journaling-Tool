from PIL import Image
from maskgen import exif
import numpy as np
import PIL
from maskgen.image_wrap import openImageFile, ImageWrapper

"""
Save te image as PNG. If the image has a orientation and 'Image Rotated', rotate the image according to the EXIF.
"""
def transform(img,source,target, **kwargs):
    # NOTE: arguments passed on AS IS!!
    im = openImageFile(source,args=kwargs)
    imarray = np.array(im)
    #deal with grayscale image
    if len(imarray.shape)==2:
        w, h = imarray.shape
        ret = np.empty((w, h, 3), dtype=np.uint8)
        ret[:, :, :] = imarray[:, :, np.newaxis]
        imarray = ret

    rotate=False
    if 'Image Rotated' in kwargs and kwargs['Image Rotated'] == 'yes':
        orientation = exif.getOrientationFromExif(source)
        if orientation is not None:
            rotate = exif.rotateAmount(orientation)[1] != 0.0
            imarray = exif.rotateAccordingToExif(imarray,orientation, counter=True)
    ImageWrapper(imarray).save(target,format='PNG')
    
    return {'Image Rotated': 'yes' if rotate else 'no'},None
    
def operation():
    return {'name':'OutputPng',
            'category':'Output',
            'description':'Save an image as .PNG',
            'software':'PIL',
             'version':PIL.__version__,
            'arguments':{
                'Image Rotated':{
                    'type':'yesno',
                    'defaultvalue':'no',
                    'description':'Rotate image according to EXIF'
                },
                'Bits per Channel': {
                    'type': 'list',
                    'values': ['8','16'],
                    'defaultvalue': '8',
                    'description': 'Channel bit depth'
                },
                'White Balance': {
                    'type': 'list',
                    'values': ['auto','camera','none'],
                    'defaultvalue': 'none',
                    'description': 'White Balance'
                },
                'Color Space': {
                    'type': 'list',
                    'values': ['sRGB', 'ProPhoto','Adobe','XYZ','Wide','default'],
                    'defaultvalue': 'default',
                    'description': 'Color Spaces'
                },
                'Demosaic Algorithm': {
                    'type': 'list',
                    'values' : ['default','AAHD','AFD','AMAZE','DCB','DCB','DHT','LMMSE','LINEAR','MODIFIED_AHD','PPG','VCD',
                                'VCD_MODIFIED_AHD','VNG'],
                    'defaultvalue': 'default',
                    'description': 'Rotate image according to EXIF'
                }
            },
            'transitions': [
                'image.image'
            ]
        }

def suffix():
    return '.png'
