# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
#==============================================================================
import sys
import numpy as np
from maskgen.image_wrap import openImageFile, ImageWrapper

def sign(num):
    return -1 if num < 0 else 1

def transform(img, source, target, **kwargs):
    donor = kwargs['donor'] # raise error if missing donor

    im_source = openImageFile(source).image_array
    im_donor_trace = openImageFile(donor).image_array

    if np.shape(im_source)[0:2] != np.shape(im_donor_trace)[0:2]:
        orientation_source = np.shape(im_source)[0] - np.shape(im_source)[1]
        orientation_donor = np.shape(im_donor_trace)[0] - np.shape(im_donor_trace)[1]
        if sign(orientation_source) != sign(orientation_donor):
            im_donor_trace = np.rot90(im_donor_trace, -1)
        im_source = im_source[:min(np.shape(im_donor_trace)[0],np.shape(im_source)[0]),
                              :min(np.shape(im_donor_trace)[1],np.shape(im_source)[1]),:]
        ImageWrapper(im_source).save(target, format='PNG')
    return None, None


def operation():
    return {'name':'TransformCrop',
            'category':'Transform',
            'description':'Crop to be Fit in Donor Image',
            'software':'numpy',
            'version':'1.11',
            'arguments':{
                'donor':{
                    'type':'donor',
                    'defaultvalue':None,
                    'description':'Donor Size.'
                }
            },
            'transitions':[
                'image.image'
                ]
            }

def suffix():
    return '.png'
