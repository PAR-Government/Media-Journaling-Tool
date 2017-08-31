"""
PAR Government Systems

compress_as takes in two JPEG images, and compresses the first with the q tables of the second

"""

import os
import tempfile
from PIL import Image
import numpy as np
from maskgen.jpeg.utils import get_subsampling,parse_tables,sort_tables,check_rotate
import maskgen.exif
import maskgen



def cs_save_as(source, target, donor, qTables,rotate,quality):
    """
    Saves image file using quantization tables
    :param source: string filename of source image
    :param target: string filename of target (result)
    :param donor: string filename of donor JPEG
    :param qTables: list of lists containing jpg quantization tables
    :param rotate: boolean True if counter rotation is required
    """

    # much of the time, images will have thumbnail tables included.
    # from what I've seen the thumbnail tables always come first...
    thumbTable = []
    prevTable = []
    if len(qTables) == 6:
        thumbTable = qTables[0:2]
        prevTable = qTables[2:4]
        finalTable = qTables[4:6]
    elif len(qTables) > 2 and len(qTables) < 6:
        thumbTable = qTables[0:2]
        finalTable = qTables[-2:]
    else:
        finalTable = qTables

    # write jpeg with specified tables
    with open(source,'rb') as fp:
        im = Image.open(fp)
        im.load()
    if rotate:
      im = check_rotate(im,donor)
    sbsmp = get_subsampling(donor)
    try:
        im.save(target, subsampling=sbsmp, qtables=finalTable,quality=quality)
    except:
        im.save(target)
    width, height = im.size
    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor, '-all:all>all:all', '-unsafe', target])

    # Preview is not well standardized in JPG (unlike thumbnail), so it doesn't always work.
    if prevTable:
        im.thumbnail((320,320))
        fd, tempFile = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            im.save(tempFile, subsampling=sbsmp, qtables=prevTable,quality=quality)
            maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-PreviewImage<=' + tempFile + '', target])
        except OverflowError:
            prevTable[:] = [[(x - 128) for x in row] for row in prevTable]
            try:
                im.save(tempFile, subsampling=sbsmp, qtables=prevTable,quality=quality)
                maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-PreviewImage<=' + tempFile + '', target])
            except Exception as e:
                print 'Preview generation failed'
                print e
        finally:
            os.remove(tempFile)

    if thumbTable:
        im.thumbnail((128, 128))
        fd, tempFile = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            im.save(tempFile, subsampling=sbsmp, qtables=thumbTable,quality=quality)
            maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-ThumbnailImage<=' + tempFile + '', target])
        except OverflowError:
            thumbTable[:] = [[(x - 128) for x in row] for row in thumbTable]
            try:
                im.save(tempFile, subsampling=sbsmp, qtables=thumbTable,quality=quality)
                maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-ThumbnailImage<=' + tempFile + '', target])
            except Exception as e:
                print 'thumbnail generation failed'
                print e
        finally:
            os.remove(tempFile)
    maskgen.exif.runexif(['-P', '-q', '-m', '-XMPToolkit=',
                                        '-ExifImageWidth=' + str(width),
                                        '-ImageWidth=' + str(width),
                                        '-ExifImageHeight=' + str(height),
                                        '-ImageHeight=' + str(height),
                                        target])
    createtime = maskgen.exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        maskgen.exif.runexif(['-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target])

def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    rotate = kwargs['rotate'] == 'yes'
    quality = int(kwargs['quality']) if 'quality' in kwargs else 0
    
    tables_zigzag = parse_tables(donor)
    tables_sorted = sort_tables(tables_zigzag)
    cs_save_as(source, target, donor, tables_sorted,rotate, quality)
    
    return None,None
    
def operation():
    return {'name':'AntiForensicExifQuantizationTable',
            'category':'AntiForensic',
            'description':'Save as a JPEG using original tables and EXIF',
            'software':'maskgen',
            'version':maskgen.__version__[0:2],
            'arguments':{
                'donor':{
                    'type':'donor',
                    'defaultvalue':None,
                    'description':'JPEG with donor QT'
                },
                'rotate':{
                    'type':'yesno',
                    'defaultvalue':'yes',
                    'description':'Answer yes if the image should be counter rotated according to EXIF Orientation field'
                },
                'quality': {
                    'type': 'int[0:100]',
                    'defaultvalue': '0',
                    'description': "Quality Factor overrides the donor.  The default value of 0 indicates using the donor image's quality factor."
                }
            },
            'transitions': [
                'image.image'
            ]
            }

def suffix():
    return '.jpg'
