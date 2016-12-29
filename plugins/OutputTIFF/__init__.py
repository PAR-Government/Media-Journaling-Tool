"""
PAR Government Systems

Two TIFF images, and compresses the first with the configuration from the second

"""

import maskgen.exif
from maskgen.tool_set import *
import numpy as np

def check_rotate(im, donor_img, jpg_file_name):
    return ImageWrapper(maskgen.exif.rotateAccordingToExif(np.asarray(im),maskgen.exif.getOrientationFromExif(jpg_file_name)))

def tiff_save_as(source_img, source, target, donor_file, rotate):
    """
    Saves image file using the same image compression
    :param source: string filename of source image
    :param target: string filename of target (result)
    :param donor: string filename of donor TIFF
    :param rotate: boolean True if counter rotation is required
    """
    donor_img = openImageFile(donor_file)
    if rotate:
        source_img = check_rotate(source_img, donor_img,donor_file)
    source_img.save(target, format='TIFF', **donor_img.info)
    width, height = source_img.size
    maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-XMPToolkit=', target])
    maskgen.exif.runexif(['-q', '-all=', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor_file, '-all:all', '-unsafe', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-XMPToolkit=',
                 '-ExifImageWidth=' + str(width),
                 '-ImageWidth=' + str(width),
                 '-ExifImageHeight=' + str(height),
                 '-ImageHeight=' + str(height),
                 target])
    createtime = maskgen.exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        maskgen.exif.runexif(['-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target])


def transform(source_img,source,target, **kwargs):
    donor = kwargs['donor']
    rotate = 'rotate' in kwargs and kwargs['rotate'] == 'yes'
    tiff_save_as(source_img , source, target, donor, rotate)
    
    return None,None
    
def operation():
    return {'name':'AntiForensicExifQuantizationTable',
            'category':'AntiForensic',
            'description':'Save as a TIFF using original tables and EXIF',
            'software':'PIL',
            'version':'1.1.7',
            'arguments':{
                'donor':{
                    'type':'donor',
                    'defaultvalue':None,
                    'description':'TIFF with donor EXIF'
                },
                'rotate':{'type':'yesno',
                          'defaultvalue':None,
                          'description':'Answer yes if the image should be counter rotated according to EXIF Orientation'
                          }
            },
            'transitions': [
                'image.image'
            ]
            }

def suffix():
    return '.TIF'
