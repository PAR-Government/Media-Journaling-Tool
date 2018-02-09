import os
import csv
import maskgen
from maskgen.external.api import BrowserAPI

"""
Pick an image from the browser .
Used with batch project's ImageSelectionPluginOperation
"""


def transform(img, source, target, **kwargs):
    import json
    api = BrowserAPI()
    prefix = kwargs['prefix'] if 'prefix' in  kwargs['prefix'] else 'images'
    directory = kwargs['directory'] if 'directory' in kwargs else '.'
    query_param = kwargs['query json'] if 'query json' in kwargs else '{}'
    query = query_param if type(query_param) == dict else json.loads(query_param)
    return {'file': api.pull(query, directory=directory, prefix = prefix)}, None


def operation():
    return {'name': 'SelectFile',
            'category': 'Select',
            'description': 'Select image based on a pairing to an existing image.',
            'software': 'maskgen',
            'version': maskgen.__version__[0:3],
            'arguments': {'directory': {'type': "text",
                                        'description': "location of the paired images"},
                          'prefix': {'type': "list",
                                     'values': ['images','videos'],
                                        'description': "type"},
                          'query json': {'type': "text",
                                     'description': "JSON queru"}
                          },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return None
