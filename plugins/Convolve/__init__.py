import cv2
from PIL import Image, ImageFilter
from maskgen import image_wrap
import itertools
import numpy as np
import math

def get_kernel(data):
    k = []
    for line in data:
        line = line.replace(',', ' ')
        line = line.split()
        if line:
            line = [float(i) for i in line]
            k.append(line)

    return list(itertools.chain(*k))

def transform(im, source, target, **kwargs):
    with open(kwargs['convolutionkernel']) as f:
        k = np.asarray(get_kernel(f))

    # kernel should be dimensions ZxZ
    sz = int(math.sqrt(k.size))
    try:
        k = np.reshape(k, (sz,sz))
    except ValueError:
        # kernel was not square
        raise ValueError('Kernel must be square (2x2, 3x3, etc).')

    # openCV filter2D actually does correlation, not convolution. Flip the kernel to do convolution.
    k = cv2.flip(k, 0)

    res = cv2.filter2D(im.image_array, -1, k)
    res_bgr = cv2.cvtColor(res, cv2.COLOR_RGB2BGR)
    cv2.imwrite(target, res_bgr)

    return None, None

def operation():
    return {'name':'FilterConvolutionKernel',
            'category':'Filter',
            'description':'Apply a custom convolution kernel to an image.',
            'software':'OpenCV',
            'version':cv2.__version__,
            'arguments':{},
            'transitions':[
                'image.image'
                ]
            }

def suffix():
    return None