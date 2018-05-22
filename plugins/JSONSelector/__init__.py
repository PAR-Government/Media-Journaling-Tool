import logging
from maskgen.image_wrap import openImageFile
import numpy as np
import os
import maskgen
import json


def transform(img, source, target, **kwargs):
    js = json.load(open(kwargs['Json File']))
    index = kwargs['index'] if 'index' in kwargs else np.random.randint(0, len(js), 1)
    dictionary = js[int(index)]
    if 'File Key' in kwargs and kwargs['File Key'] != '':
        dictionary['file'] = dictionary[kwargs['File Key']]
        #openImageFile(dictionary[kwargs['File Key']]).save(target)
    return dictionary, None


def operation():
    return {'name': 'SelectRegion',
            'category': 'Select',
            'type': 'Selector',
            'description': 'Selects a dictionary of arguments from a JSON',
            'software': 'Maskgen',
            'version': maskgen.__version__,
            'arguments': {
                'Json File': {
                    'type': 'file:json',
                    'defaultvalue': '.',
                    'description': 'JSON file containing a list dictionaries of relevant options'
                },
                'Index': {
                    'type': 'int[0:100000]',
                    'description': 'Select the dictionary from the JSON list'
                },
                'File Key':{
                    'type':'text',
                    'description':'Key referencing a file to be saved as target'
                  }
            },
            'transitions': [
                'image.image'
            ]
            }
