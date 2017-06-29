from PIL import Image
from maskgen import exif
import numpy as np

"""
Save the image as PDF. If the image has a orientation and 'Image Rotated', rotate the image according to the EXIF.
"""
def transform(img,source,target, **kwargs):
    if 'resolution' in kwargs:
        res = float(int(kwargs['resolution']))
    else:
        res = 200.0
    im = img.convert('RGB').to_array()
    Image.fromarray(im).save(target,format='PDF',resolution=res)
    
    return None,None
    
def operation():
    return {'name':'OutputPDF',
            'category':'Output',
            'description':'Save an image as .pdf',
            'software':'PIL',
            'version':'1.1.7',
            'arguments':{
                'resolution':{
                    'type':'int',
                    'defaultvalue':'100',
                    'description':'DPI'
                }
            },
            'transitions': [
                'image.image'
            ]
        }

def suffix():
    return '.pdf'
