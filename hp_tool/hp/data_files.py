import os

"""
Contains easy method for accessing data files throughout the hp tool.
"""

_ROOT = os.path.abspath(os.path.dirname(__file__))
def get_data(path):
    return os.path.join(_ROOT, 'data', path)
def get_home(path):
    return os.path.join(os.path.expanduser('~'), path)

_REDX = get_data('RedX.png')
_APPS = get_data('apps.csv')
_DB = get_data('db.csv')
_DEVICES = get_data('devices.json')
_LOCALDEVICES = get_home('.hpdevices')
_FIELDNAMES = get_data('fieldnames.json')
_HEADERS = get_data('headers.json')
_HPTABS = get_data('hptabs.json')
_IMAGEKEYWORDS = get_data('ImageKeywords.csv')
_KINEMATICS = get_data('Kinematics.csv')
_LENSFILTERS = get_data('LensFilters.csv')
_PRNUVOCAB = get_data('prnu_vocab.csv')
_COLLECTIONS = get_data('collections.json')
