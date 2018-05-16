import logging
from maskgen import video_tools
import numpy as np
import os
import maskgen
import json


def transform(img, source, target, **kwargs):
    js = json.load(kwargs['Json File'])
    index = kwargs['index'] if 'index' in kwargs else np.random.randint(0, len(js), 1)
    return js[index], None


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
                    'type': 'text',
                    'description': 'Select the dictionary from the JSON list'
                }
            },
            'transitions': [
                'video.video'
                'image.image'
            ]
            }
