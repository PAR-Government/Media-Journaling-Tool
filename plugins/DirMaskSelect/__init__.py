import os
import glob
import maskgen


def transform(img, source, target, **kwargs):
    dirname = kwargs['directory']
    filename = os.path.basename(os.path.splitext(source)[0])
    mask = glob.glob(os.path.join(dirname, filename) + '*')[0]
    return {'override_target': mask}, None


def operation():
    return {
        'category': 'Select',
        'name': 'SelectRegion',
        'description': 'Mask Selector: ',
        'software': 'Maskgen',
        'version': maskgen.__version__,
        'arguments': {'directory': {'type': "text", 'description': 'Directory of Masks'}},
        'transitions': [
            'image.image'
        ]
    }


def suffix():
    return '.png'
