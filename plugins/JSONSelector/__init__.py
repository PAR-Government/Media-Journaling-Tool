from maskgen.image_wrap import openImageFile
import numpy as np
import os
import maskgen
import json
js = None
jsName = None

def transform(img, source, target, **kwargs):
    global js,jsName
    if kwargs['Json File'] != jsName:
        js = json.load(open(kwargs['Json File']))
        jsName = kwargs['Json File']
    index = kwargs['index'] if 'index' in kwargs else np.random.randint(0, len(js), 1)[0] #use given, if none given, pick.

    dictionary = None
    if str(index).isdigit(): #see if we are trying to reference by index, else search through values.
        dictionary = js[int(index)]
    else:
        if index in js:
            dictionary = js[index]
        else:
            for d in js:
                if str(index) in d or d in index:
                    dictionary = js[d]
                    break
    if not dictionary:
        raise ValueError("{0} not found in {1}".format(index, jsName))

    result = {}
    result.update(dictionary)
    if 'File Key' in kwargs and kwargs['File Key'] != '':
        if os.path.isfile(dictionary[kwargs['File Key']]):
            openImageFile(dictionary[kwargs['File Key']]).save(target)
            result['file'] = dictionary[kwargs['File Key']]
    return result, None


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
                    'description': 'JSON file containing a list of dictionaries of relevant options'
                },
                'Index': {
                    'type': 'text',
                    'description': 'Select the dictionary from the JSON list'
                },
                'File Key':{
                    'type':'text',
                    'description':'Key referencing a file to save as target'
                  }
            },
            'transitions': [
                'image.image'
            ]
            }
