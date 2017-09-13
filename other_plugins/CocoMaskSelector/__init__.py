import maskgen
from maskgen_coco import createMaskImageWithParams
import sys
from maskgen.image_wrap import ImageWrapper
"""
Selects a Mask from Coco presegmented images
"""


def transform(img, source, target, **kwargs):
    areaConstraints = (int(kwargs['area.lower.bound']) if 'area.lower.bound' in kwargs else 0,
                       int(kwargs['area.upper.bound']) if 'area.upper.bound' in kwargs else sys.maxint)
    annotation,mask =createMaskImageWithParams(np.asarray(img), source, kwargs, areaConstraint=areaConstraints)
    ImageWrapper(mask).save(target)
    return {'subject':annotation},None


def operation():
    return {'name': 'SelectRegion',
            'category': 'Select',
            'software': 'maskgen',
            'version': maskgen.__version__[0:6],
            'arguments': {
                'coco': {
                    "type": "str",
                    "description": "Coco Object."
                },
                'coco.index': {
                    "type": "str",
                    "description": "Coco file->id Dictionary"
                },
                'area.lower.bound': {
                    "type": "int[0:100000000000]",
                    "description": "lower bound on area of segment in pixels"
                },
                'area.upper.bound': {
                    "type": "int[0:100000000000]",
                    "description": "upper bound on area of segment in pixels"
                }
            },
            'description': 'Create a limited selection in a donor image.  The provided inputmask is placed as the alpha channel of the result image',
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return '.png'
