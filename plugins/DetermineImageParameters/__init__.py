from maskgen import image_wrap
import numpy as np
import maskgen
from maskgen.jpeg import utils

"""
Determine new parameters based on an image's current metrics (qualify factor, size, etc.).
Returns selected_width,selected_height and quality_factor.
"""

def transform(img, source, target, **kwargs):
    qf_donor = source
    if 'donor' in kwargs:
        qf_donor = kwargs['donor']
        img = image_wrap.openImageFile(kwargs['donor'])
    w_c = float(kwargs['percentage_width'])
    h_c = float(kwargs['percentage_height'])
    qf_c = float(kwargs['percentage_qf']) if 'percentage_qf' in kwargs else 1.0
    qf = int(kwargs['quality_factor']) if 'quality_factor' in kwargs else None
    cv_image = np.asarray(img.to_array())
    h = int(cv_image.shape[0] * h_c)
    w = int(cv_image.shape[1] * w_c)
    w = w + (8 - w % 8)
    h = h + (8 - h % 8)
    if qf is None:
        qf = utils.estimate_qf(qf_donor)
    return {'selected_width': w, 'selected_height': h, 'quality_factor': int(qf*qf_c)}, None

def operation():
    return {
        'category': 'Select',
        'name': 'SelectRegion',
        'type':'selector',
        'description': 'Select image parameters selected_width,selected_height, and quality_factor for use by other plugins',
        'software': 'maskgen',
        'version': maskgen.__version__[0:3],
        'arguments': {'percentage_width': {'type': "float[0.01:2]", 'description': 'percentage change'},
                      'percentage_height': {'type': "float[0.01:2]", 'description': 'percentage change'},
                      'percentage_qf': {'type': "float[0.7:1]", 'description': 'percentage change  in quality factory'},
                      'quality_factor': {'type': "int[50:100]", 'description': 'override quality factor'}
                      },
        'transitions': [
            'image.image'
        ]
    }


def suffix():
    return '.png'
