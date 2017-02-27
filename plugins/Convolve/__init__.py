import cv2
from PIL import Image, ImageFilter
from maskgen import image_wrap
import itertools

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
        k = get_kernel(f)

    if len(k) == 9:
        sz = (3,3)
    elif len(k) == 25:
        sz = (5,5)
    else:
        raise ValueError('Kernel must be length 3x3 (9) or 5x5 (25)')

    kernel = ImageFilter.Kernel(sz, k)

    out = im.toPIL().filter(kernel)

    out.save(target)

    return None, None

def operation():
    return {'name':'FilterConvolutionKernel',
            'category':'Filter',
            'description':'Apply a custom convolution kernel to an image.',
            'software':'PIL',
            'version':'1.1.7',
            'arguments':{
                "convolutionkernel": {
                    "type": "fileset:",
                    "description": "Text file containing 3x3 or 5x5 convolution kernel, separated by spaces and/or newlines."
                }
            },
            'transitions':[
                'image.image'
                ]
            }

def suffix():
    return None