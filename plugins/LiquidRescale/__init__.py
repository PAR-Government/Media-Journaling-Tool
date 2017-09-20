from __future__ import division
from maskgen.image_wrap import ImageWrapper,openImageFile
import subprocess

"""
Convert donor to png and resize to fit source dimensions
using Liquid Rescale plugin of GIMP.
"""

gimpfile = "gimp-2.8"
quitstring = '"(gimp-quit 0)"'


def resizeUsingLQR(fpn, sizeNew):
    # Compose command line string that calls GIMP plugin Liquid Rescale
    commandLineInterior = '{} -i -f -b (batch-gimp-lqr {} {} {})' -b
    commandLineInterior += '\\\" ' + sizeNew[0].__str__() + ' ' + sizeNew[1].__str__()
    commandLineInterior += ' \\"\\"\\"\\"\\"\\")\"'
    LQRCommandLine = [gimpfile, '-i', '-f', '-b', commandLineInterior, '-b', quitstring]
    subprocess.call(" ".join(LQRCommandLine), shell=True)


def valtestExcludeSameSize(sizSource=(0, 0), sizDonor=(0, 0)):
    if sizSource == sizDonor:
        raise ValueError('LQR images are the same size')


def valtestExcludeSizeNotWithinPercent(sizSource=(0, 0), sizDonor=(0, 0), nPercent=20):
    if abs((sizSource[0] - sizDonor[0]) / sizSource[0]) > nPercent / 100.0:
        raise ValueError('LQR image sizes are too different')
    if abs((sizSource[1] - sizDonor[1]) / sizSource[1]) > nPercent / 100.0:
        raise ValueError('LQR image sizes are too different')


def validateImageSizes(sizSource=(0, 0), sizDonor=(0, 0), nPercent=20):
    valtestExcludeSameSize(sizSource, sizDonor)
    valtestExcludeSizeNotWithinPercent(sizSource, sizDonor, 20)

def transform(img, source, target, **kwargs):
    donor = kwargs['donor']
    sizSource = img.size
    sizDonor = openImageFile(donor).size
    validateImageSizes(sizSource, sizDonor)
    # Use Liquid Rescale to resize donor image
    # to size of source image.
    resizeUsingLQR(target, sizDonor)
    return None, None


def operation():
    return {'name': 'TransformSeamCarving',
            'category': 'Transform',
            'description': 'Resize donor to size of Input using LQR',
            'software': 'GIMP',
            'version': '2.8.20',
            'arguments': {
                'donor': {
                    'type': 'donor',
                    'defaultvalue': None,
                    'description': 'png that contributes size info'
                },
                'percentage bounds': {
                    'type': 'int',
                    'defaultvalue': 20,
                    'description': 'Proximity '
                }
            },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return '.png'
