from __future__ import division
from maskgen.image_wrap import ImageWrapper
import os
import numpy as np
from maskgen.tool_set import shortenName,uniqueId,getValue
import maskgen

from maskgen.algorithms.seam_carving import SeamCarver, SobelFunc, \
ScharrEnergyFunc,base_energy_function,foward_base_energy_function


"""
Seam Carving: Calculate the final mask from seam carving.
"""

def carveSeams(source,target,shape,mask_filename, approach='backward', energy='Sobel', keep_size=False):
    """
    :param img:
    :return:
    @type img: ImageWrapper
    """
    import traceback
    import sys
    try:
        sc = SeamCarver(source, shape=shape,
                        energy_function=SobelFunc() if energy == 'Sobel' else ScharrEnergyFunc(),
                        mask_filename=mask_filename,
                        keep_size = keep_size,
                        seam_function=foward_base_energy_function if approach == 'forward' else base_energy_function)
        image, mask = sc.remove_seams()
    except IndexError as ex:
        texc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_traceback, limit=10, file=sys.stdout)
        raise ex
    maskname = os.path.join(os.path.dirname(source),shortenName(os.path.basename(source),'_real_mask.png', id=uniqueId()))
    adjusternames= os.path.join(os.path.dirname(source),shortenName(os.path.basename(source), '.png',id=uniqueId()))
    finalmaskname = os.path.join(os.path.dirname(source),shortenName(os.path.basename(source), '_final_mask.png',id=uniqueId()))
    ImageWrapper(mask).save(os.path.join(os.path.dirname(source), maskname))
    adjusternames_row, adjusternames_col = sc.mask_tracker.save_adjusters(adjusternames)
    sc.mask_tracker.save_neighbors_mask(finalmaskname)
    ImageWrapper(image).save(target)
    return {'neighbor mask': finalmaskname,
            'column adjuster':adjusternames_col,
            'row adjuster': adjusternames_row,
            'plugin mask': maskname}


def transform(img, source, target, **kwargs):
    img = np.asarray(img)
    sizeSource = img.shape
    percentageWidth = float(kwargs['percentage_width'])
    percentageHeight = float(kwargs['percentage_height'])
    pixelWidth = int(sizeSource[1] * percentageWidth)
    pixelHeight = int(sizeSource[0] * percentageHeight)
    keepSize = 'keepSize' in kwargs and kwargs['keepSize'] == 'yes'
    if not keepSize:
        if percentageWidth != 1.0:
            pixelWidth = pixelWidth - pixelWidth % 4
        if  percentageHeight != 1.0:
            pixelHeight = pixelHeight - pixelHeight % 4
    sizeDonor = (pixelHeight, pixelWidth)
    keepSize = 'keepSize' in kwargs and kwargs['keepSize'] == 'yes'
    return {'output_files': carveSeams(source, target, sizeDonor,
                                       kwargs['inputmaskname'] if 'inputmaskname' in kwargs else None,
                                       keep_size=not keepSize,
                                       approach=getValue(kwargs,'approach',defaultValue="backward"),
                                       energy=getValue(kwargs, 'energy', defaultValue="Sobel"))}, None


def operation():
    return {'name': 'TransformSeamCarving',
            'category': 'Transform',
            'description': 'Resize donor to size of Input using LQR. Requires GIMP.  Set environment variable MASKGEN_GIMP to the gimp binary',
            'software':'maskgen',
            'version':maskgen.__version__[0:3],
            'arguments': {
                'donor': {
                    'type': 'donor',
                    'defaultvalue': None,
                    'description': 'png that contributes size info'
                },
                'percentage_width': {
                    'type': 'float[0.5:1.0]',
                    'defaultvalue': 1,
                    'description': 'The percentage of size to keep'
                },
                'percentage_height': {
                    'type': 'float[0.5:1.0]',
                    'defaultvalue': 1,
                    'description': 'The percentage of size to keep'
                },
                'approach': {
                    'type': 'list',
                    "values" : ["forward","backward"],
                    'defaultvalue': 'backward',
                    'description': 'See literature.'
                },
                'energy': {
                    'type': 'list',
                    "values": ["Sobel", "Scharr"],
                    'defaultvalue': 'Sobel',
                    'description': 'See literature.'
                },
                'keepSize': {
                    'type': 'yesno',
                    'defaultvalue': 'no',
                    'description': 'After object removal, retain current size or add seams back to restore original size.'
                }
            },
            'transitions': [
                'image.image'
            ]
            }


def suffix():
    return '.png'
