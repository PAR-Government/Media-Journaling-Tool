import PIL
import numpy as np
from maskgen import exif
from maskgen.image_wrap import openImageFile, ImageWrapper
from maskgen.tool_set import getExifDimensions

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

    analysis = {}
    if 'Crop' in kwargs and kwargs['Crop'] == 'yes':
        dims = getExifDimensions(source,crop=True)
        if len(dims) > 0 and imarray.shape[0] != dims[0][0]:
            h = int(imarray.shape[0]-dims[0])/2
            w = int(imarray.shape[1]-dims[1])/2
            imarray = imarray[h:-h,w:-w]
            analysis['location']  = str((h,w))
    if 'Image Rotated' in kwargs and kwargs['Image Rotated'] == 'yes':
        orientation = exif.getOrientationFromExif(source)
        if orientation is not None:
            analysis.update( exif.rotateAnalysis(orientation))
            imarray = exif.rotateAccordingToExif(imarray,orientation, counter=True)
    ImageWrapper(imarray).save(target,format='PNG')
    analysis['Image Rotated']  = 'yes' if 'rotation' in analysis else 'no'
    return analysis,None
    
def operation():
    return {'name': 'OutputPng',
            'category': 'Output',
            'description': 'Save an image as .PNG',
            'software': 'PIL',
            'version': PIL.__version__,
            'arguments': {
                'Image Rotated': {
                    'type': 'yesno',
                    'defaultvalue': 'no',
                    'description': 'Rotate image according to EXIF'
                },
                "Crop": {
                    "type": "yesno",
                    "defaultvalue": "no",
                    "description": "Cropped according to camera?"
                },
                'Bits per Channel': {
                    'type': 'list',
                    'values': ['8', '16'],
                    'defaultvalue': '8',
                    'description': 'Channel bit depth'
                },
                'White Balance': {
                    'type': 'list',
                    'values': ['auto', 'camera', 'none'],
                    'defaultvalue': 'none',
                    'description': 'White Balance'
                },
                'Color Space': {
                    'type': 'list',
                    'values': ['sRGB', 'ProPhoto', 'Adobe', 'XYZ', 'Wide', 'default'],
                    'defaultvalue': 'default',
                    'description': 'Color Spaces'
                },
                'Demosaic Algorithm': {
                    'type': 'list',
                    'values': ['default', 'AAHD', 'AFD', 'AMAZE', 'DCB', 'DCB', 'DHT', 'LMMSE', 'LINEAR',
                               'MODIFIED_AHD', 'PPG', 'VCD',
                               'VCD_MODIFIED_AHD', 'VNG'],
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
