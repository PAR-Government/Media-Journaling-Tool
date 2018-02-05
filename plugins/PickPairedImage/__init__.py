import os
import csv
import maskgen

"""
Pick an image given the source image name.
Used with batch project's ImageSelectionPluginOperation
"""


def transform(img, source, target, **kwargs):
    pair_file = kwargs['pairing'] if 'pairing' in kwargs else 'pairing.csv'
    dir = kwargs['directory'] if 'directory' in kwargs else '.'
    pairingid = kwargs['pairingid']
    if not os.path.exists(pair_file):
        raise ValueError('Cannot find pairing file {}'.format(pair_file))
    filename = os.path.split(source)[1] if pairingid is None else pairingid
    with open(pair_file) as fp:
        reader = csv.reader(fp)
        pairs = [row[1] for row in reader if row[0] == filename]
    if len(pairs) == 0:
        raise ValueError('Pairing not found for {}'.format(filename))
    if not os.path.exists(os.path.join(dir, pairs[0])):
        raise ValueError('Pairing file {} not found for {}'.format(pairs[0], filename))
    return {'file': os.path.join(dir, pairs[0])}, None


def operation():
    return {'name': 'SelectFile',
            'category': 'Select',
            'description': 'Select image based on a pairing to an existing image.',
            'software': 'maskgen',
            'version': maskgen.__version__[0:3],
            'arguments': {'pairing': {'type': "text",
                                      'description': "name of CSV file containing the pairs image to image"},
                          'directory': {'type': "text",
                                        'description': "location of the paired images"},
                          'pairingid': {'type': "text",
                                        'defaultvalue': None,
                                        'description': "optional"}
                          },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return None
