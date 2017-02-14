from PIL import Image
from maskgen import exif
import numpy as np

def transform(im, source, target, **kwargs):

    im = Image.open(source)
    if 'Image Rotated' in kwargs and kwargs['Image Rotated'] == 'yes':
        orientation = exif.getOrientationFromExif(source)
        if orientation is not None:
            im = Image.fromarray(exif.rotateAccordingToExif(np.asarray(im), orientation, counter=True))
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
                }
            },
            'transitions':[
                'image.image'
            ]
            }

def suffix():
    return '.bmp'
