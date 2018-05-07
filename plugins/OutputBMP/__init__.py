# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from PIL import Image
from maskgen import exif
import numpy as np
from maskgen.tool_set import *
from maskgen.jpeg.utils import check_rotate


def transform(im, source, target, **kwargs):
    analysis= {}
    if 'donor' in kwargs and 'Image Rotated' in kwargs and kwargs['Image Rotated'] == 'yes':
        im, analysis = check_rotate(im, kwargs['donor'])
    else:
        im = Image.fromarray(np.asarray(im))
    im.save(target, format='BMP')

    if 'donor' in kwargs:
        donor = kwargs['donor']
        exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-XMPToolkit=', target])
        exif.runexif(['-overwrite_original','-q', '-all=', target])
        exif.runexif(['-overwrite_original','-P', '-q', '-m', '-TagsFromFile', donor, '-all:all', '-unsafe', target])
    createtime = exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        exif.runexif(['-overwrite_original','-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target])
    analysis['Image Rotated'] = 'yes' if 'rotation' in analysis else 'no'
    return analysis , None

def operation():
    return {'name':'OutputBmp',
            'category':'Output',
            'description':'Output as BMP and copy metadata, if supplied.',
            'software':'maskgen',
            'version':'0.4',
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
