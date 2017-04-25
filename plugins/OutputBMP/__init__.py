from PIL import Image
from maskgen import exif
import numpy as np
from maskgen.tool_set import *


def check_rotate(im, jpg_file_name):
    return ImageWrapper(exif.rotateAccordingToExif(np.asarray(im),exif.getOrientationFromExif(jpg_file_name)))

def transform(im, source, target, **kwargs):
    if 'donor' in kwargs and 'Image Rotated' in kwargs and kwargs['Image Rotated'] == 'yes':
        im = check_rotate(im, kwargs['donor'])
    else:
        im = Image.open(source)
    im.save(target, format='BMP')

    if 'donor' in kwargs:
        donor = kwargs['donor']
        exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-XMPToolkit=', target])
        exif.runexif(['-q', '-all=', target])
        exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor, '-all:all', '-unsafe', target])
    createtime = exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        exif.runexif(['-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target])
    return None, None

def operation():
    return {'name':'OutputBmp',
            'category':'Output',
            'description':'Output as BMP and copy metadata, if supplied.',
            'software':'PIL',
            'version':'1.1.7',
            'arguments':{
                'donor':{
                    'type':'donor',
                    'defaultvalue':None,
                    'description':'BMP file with desired metadata.'
                },
                'Image Rotated': {
                    'type': 'yesno',
                    'defaultvalue': None,
                    'description': 'Answer yes if the image should be counter rotated according to EXIF Orientation.'
                }
            },
            'transitions':[
                'image.image'
            ]
            }

def suffix():
    return '.bmp'
