import maskgen
from maskgen_coco import createMaskImageWithParams
import sys
from maskgen.image_wrap import ImageWrapper
import numpy as np
from maskgen import exif
import os

"""
Select the size of an image based on make and model
"""

cameraData = {}
global cameraData

def loadCameraData(cameraDataFile):
    import json
    global cameraData
    absfile = os.path.abspath(cameraDataFile)
    if absfile  in cameraData:
        return cameraData[absfile]
    cameraData[absfile] = dict()
    with open(cameraDataFile) as fp:
        data = json.load(fp)
        for camera in data['data']:
            make = camera['make'].lower()
            if make not in cameraData:
                cameraData[absfile][make] = {}
                cameraData[absfile][make].update({camera['camera'].lower() : camera})
    return cameraData[absfile]

def getMakeAndModel(source):
    data = exif.getexif(source,['-make','-model'])
    if 'Make' not in data or 'Camera Model Name' not in data:
        return None,None
    return data['Make'],data['Camera Model Name']

def findSizes(source,cameraDataFile,format='jpeg'):
    cameraDB = loadCameraData(cameraDataFile)
    make,model = getMakeAndModel(source)
    if make is None:
        return None
    sizes = []
    if make.lower() in cameraDB:
        models = cameraDB[make.lower()]
        for cmodel, cinfo in models.iteritems():
            if model.lower() in cmodel and 'format' in cinfo and cinfo['format'] == format:
                sizes.append((cinfo['width'],cinfo['height']))
    return sizes if len(sizes) > 0 else None


def transform(img, source, target, **kwargs):
    sizes = findSizes(source, kwargs['cameraDataFile'])
    if sizes is None:
        return None, 'Camera data not found'
    if kwargs['pickOne'] == 'yes':
        for size in np.random.permutation(sizes):
            if size[0] != img.size[1] or size[1] != img.size[0]:
                return {'width':size[0],'height':size[1]}, None
    else:
        return {'sizes':[{'width':size[0],'height':size[1]} for size in np.random.permutation(sizes)
                if size[0] != img.size[1] or size[1] != img.size[0]]},None


def operation():
    return {'name': 'SelectRegion',
            'category': 'Select',
            'software': 'maskgen',
            'version': maskgen.__version__[0:6],
            'arguments': {
                'cameraDataFile': {
                    "type": "file:json",
                    "description": "JSON Camera Data File location."
                },
                'pickOne': {
                    "type": "yesno",
                    "defaultValue": "yes",
                    "description": "Randomly pick one size or return tuples"
                }
            },
            'description': 'Lookup possible image sizes',
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return '.png'
