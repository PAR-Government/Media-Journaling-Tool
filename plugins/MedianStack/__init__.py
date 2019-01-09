import logging
import os

from maskgen import exif
import maskgen
import numpy as np

from maskgen.algorithms.opencv_registration import OpenCVECCRegistration
from maskgen.image_wrap import ImageWrapper
from maskgen.tool_set import ZipCapture
from maskgen.support import getValue


def transform(img, source, target, **kwargs):
    # source = zip of images
    if 'Registration Type' in kwargs:
        reg_type = kwargs['Registration Type']
    else:
        reg_type = 'ECC'
    zipf = ZipCapture(source)
    imgs = []
    logger = logging.getLogger("maskgen")

    retrieved, zip_image = zipf.read()
    if not retrieved:
        raise ValueError("Zip File {0} is empty".format(os.path.basename(source)))

    registrar = {'ECC': OpenCVECCRegistration(os.path.join(zipf.dir, zipf.names[0]))}
    reg_tool = registrar[reg_type]

    if 'Image Rotated' in kwargs and kwargs['Image Rotated'] == 'yes':
        try:
            orientation = getValue(zipf.get_exif(), 'Orientation', None)
        except KeyError:
            orientation = None
    else:
        orientation = None

    logger.debug("Beginning image alignment for " + os.path.basename(source))
    while retrieved:
        aligned = reg_tool.align(zip_image)
        imgs.append(aligned)
        retrieved, zip_image = zipf.read()
    logger.debug(os.path.basename(source) + " alignment complete")

    if not imgs:
        return None, False

    stacks = np.stack(np.asarray(imgs))
    median_img = np.median(stacks, 0)

    analysis = {'Merge Operation': 'Median Pixel'}
    if orientation is not None:
        analysis.update(exif.rotateAnalysis(orientation))
        median_img = exif.rotateAccordingToExif(median_img, orientation, counter=True)

    ImageWrapper(median_img).save(target, format='PNG')
    analysis['Image Rotated'] = 'yes' if 'rotation' in analysis else 'no'

    return analysis, None


def operation():
    return {'name': 'MediaStacking',
            'category': 'Output',
            'description': 'Save an image with median pixel values taken from a zip of images.',
            'software': 'maskgen',
            'version': maskgen.__version__[:3],
            'arguments': {
                'Image Rotated': {
                    'type': 'yesno',
                    'defaultvalue': 'no',
                    'description': 'Rotate image according to EXIF'
                },
                'Registration Type': {
                    'type': 'text',
                    'value': 'ECC',
                    'description': 'Type of registration used to align images.',
                    'visible': False
                }
            },
            'transitions': [
                'zip.image'
            ]
            }


def suffix():
    return '.png'
