# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

# Compress_as takes in two JPEG images, and compresses the first with the q tables of the second

import maskgen
import logging



def cs_save_as(img,source, target, donor, qTables,rotate,quality, color_mode):
    import os
    import tempfile
    from PIL import Image
    import numpy as np
    from maskgen.jpeg.utils import get_subsampling, parse_tables, sort_tables, check_rotate
    import maskgen.exif
    import maskgen
    from maskgen import image_wrap

    """
    Saves image file using quantization tables
    :param ImageWrapper
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

    if img.mode == 'RGBA':
        im = Image.fromarray(np.asarray(img.convert('RGB')))
    else:
        im = Image.fromarray(np.asarray(img))

    if color_mode == 'from donor':
        donor_img = image_wrap.openImageFile(donor)
        if donor_img.mode != img.mode:
            im = Image.fromarray(np.asarray(img.convert(donor_img.mode)))

    analysis = None
    if rotate:
      im,analysis = check_rotate(im,donor)
    sbsmp = get_subsampling(donor)
    try:
        if len(finalTable) > 0:
            im.save(target, subsampling=sbsmp, qtables=finalTable,quality=quality)
        else:
            im.save(target, subsampling=sbsmp,quality=quality if quality > 0 else 100)
    except:
        im.save(target)
    width, height = im.size
    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target])
    maskgen.exif.runexif([ '-overwrite_original', '-P', '-q', '-m', '-tagsFromFile', donor, '-all:all>all:all', '-unsafe', target])

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
                logging.getLogger('maskgen').error('Preview generation failed {}'.fomat(str(e)))
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
                logging.getLogger('maskgen').error('Thumbnail generation failed {}'.fomat(str(e)))
        finally:
            os.remove(tempFile)
    maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-XMPToolkit=',
                                        '-ExifImageWidth=' + str(width),
                                        '-ImageWidth=' + str(width),
                                        '-ExifImageHeight=' + str(height),
                                        '-ImageHeight=' + str(height),
                                        target])
    createtime = maskgen.exif.getexif(target, args=['-args', '-System:FileCreateDate'], separator='=')
    if '-FileCreateDate' in createtime:
        maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-System:fileModifyDate=' + createtime['-FileCreateDate'], target])
    return analysis

def transform(img,source,target, **kwargs):
    from maskgen.jpeg.utils import  parse_tables, sort_tables

    donor = kwargs['donor']
    rotate = kwargs['rotate'] == 'yes'
    quality = int(kwargs['quality']) if 'quality' in kwargs else 0
    color_mode = kwargs['color mode'] if 'color mode' in kwargs else 'from donor'
    
    tables_zigzag = parse_tables(donor)
    tables_sorted = sort_tables(tables_zigzag)
    analysis = cs_save_as(img,source, target, donor, tables_sorted,rotate, quality, color_mode)
    
    return analysis , None
    
def operation():
    return {'name':'AntiForensicExifQuantizationTable',
            'category':'AntiForensic',
            'description':'Save as a JPEG using original tables and EXIF',
            'software':'maskgen',
            'version':maskgen.__version__[0:3],
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
                },
                'color mode':{
                    'type': 'list',
                    'values': ['from donor', 'from source'],
                    'defaultvalue': 'from donor',
                    'description': "Which image's color space will inform the color space of the output file."
                }
            },
            'transitions': [
                'image.image'
            ]
            }

def suffix():
    return '.jpg'
