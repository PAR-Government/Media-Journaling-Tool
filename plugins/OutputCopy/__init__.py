from PIL import Image
from maskgen import exif
import numpy as np

"""
Export the image or video in the in the same format. Used to branch off a final image  node
"""
def transform(img,source,target, **kwargs):
    return None,None
    
def operation():
    return {'name':'OutputCopy',
            'category':'Output',
            'description':'Export the image in the in the same format. Used to branch off a final image  node"',
            'software':'PIL',
            'version':'1.1.7',
            'arguments':{
            },
            'transitions': [
                'image.image',
                'video.video'
            ]
        }

def suffix():
    return None
