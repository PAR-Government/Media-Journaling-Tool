import os
import csv
import maskgen
from maskgen.external.api import BrowserAPI

"""
Pick an image from the browser .
Used with batch project's ImageSelectionPluginOperation
"""

def loadExclusions(filename):
    import json
    with open(filename,'r') as fp:
        return json.load(fp, encoding='utf-8')['data']

def transform(img, source, target, **kwargs):
    import json
    api = BrowserAPI()
    prefix = kwargs['prefix'] if 'prefix' in  kwargs['prefix'] else 'images'
    directory = kwargs['directory'] if 'directory' in kwargs else '.'
    query_param = kwargs['query json'] if 'query json' in kwargs else '{}'
    query = query_param if type(query_param) == dict else json.loads(query_param)
    exclusions = None
    skip = set()
    if 'exclusions file' in kwargs:
        source_name = os.path.basename(source)
        exclusions_map = loadExclusions(kwargs['exclusions file'])
        for k,v in exclusions_map.iteritems():
            skip.add(k)
            if  source_name[0:len(k)] == k:
                exclusions = v
    return {'file': api.pull(query, directory=directory, exclusions=exclusions,prefix = prefix)}, None


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
                          'exclusions file': {
                                     'type': "text",
                                     'description': "location of file with exclusions"},
                          'query json': {'type': "text",
                                     'description': "JSON queru"}
                          },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return None
