import shutil
import os
import maskgen

"""
Convenience plugin to combine donation and splice connecting in one operation.
"""


def transform(img, source, target, **kwargs):
    if 'Final Image ' in kwargs:
        shutil.copy(kwargs['Final Image'], target)
        return {'rename_target': os.path.split(kwargs['Final Image'])[1]}, None
    else:
        return None, None


def operation():
    return {'name': 'PasteSplice',
            'category': 'Paste',
            'software': 'maskgen',
            'version': maskgen.__version__[0:3],
            'arguments': {
                'donor': {
                    "type": "donor",
                    "description": "Image to paste."
                },
                'Final Image': {
                    "type": "file:image",
                    "description": "Final Result of the manipulation."
                }
            },
            'description': 'Paste Splice Convenience Filter to combine paste splice and donation connections in one step.',
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return None
