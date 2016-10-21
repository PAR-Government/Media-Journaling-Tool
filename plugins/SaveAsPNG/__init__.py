from PIL import Image
from maskgen import exif
import numpy as np

def transform(img,source,target, **kwargs):

    im = Image.open(source)
    if 'Image Rotated' in kwargs and kwargs['Image Rotated'] == 'yes':
        orientation = exif.getOrientationFromExif(source)
        if orientation is not None:
            im = Image.fromarray(exif.rotateAccordingToExif(np.asarray(im),orientation, counter=True))
    im.save(target,format='PNG')
    
    return None,None
    
def operation():
    return ['OutputPng','Output', 
            'Save an image as .PNG', 'PIL', '1.1.7']
    
def args():
    return [('Image Rotated','no','Rotate image according to EXIF')]

def suffix():
    return '.png'
