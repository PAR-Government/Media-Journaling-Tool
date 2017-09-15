import shutil
import maskgen

"""
Simply copy of the blended image passed in as an argument.
Designed to be used with PasteOverlay.
"""
def transform(img,source,target, **kwargs):
    shutil.copy(kwargs['Final Image'], target)
    return None,None
    
def operation():
    return {'name':'Blend',
            'category':'Layer',
            'software':'maskgen',
            'version':maskgen.__version__[0:3],
            'arguments':{
                'Final Image': {
                    "type": "file:image",
                    "description": "Final Result of the manipulation."
                },
                'purpose': {
                    'type': 'text',
                    'description': 'type of manipulation performed'
                }
            },
            'description': 'Save the blended image.',
            'transitions': [
                  'image.image'
             ]
         }

def suffix():
    return None
