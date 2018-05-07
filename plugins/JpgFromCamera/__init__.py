# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import os
import tempfile
import csv
import maskgen.exif
from maskgen.image_wrap import *
from maskgen.jpeg.utils import read_tables, get_subsampling
import maskgen
from maskgen.jpeg.utils import check_rotate
import logging

def check_size(image, qt):
    """
    Check size of image vs qt, error out with help if they are not the same.
    :param image: opened PIL image
    :param qt: filename of quantization table
    :return:
    """
    if qt.find('[') > -1:
        bracketContents = qt[qt.find('[') + 1:qt.find(']')].lower()
        try:
            sizeTuple = tuple(map(int, bracketContents.split('x')))
        except ValueError:
            raise Exception('JPG size could not be found in filename: ' + qt)

        if sizeTuple != image.size:
            raise Exception('Image size does not match desired JPG dimensions. Resize first, then try again.')
        else:
            return image

    else:
        raise Exception('JPG size could not be found in filename: ' + qt)




def save_as_camera(source, target, donor, imageTable, prevTable, thumbTable, qtfile,
                   rotate=False,subsampling="4:2:2",quality=0):
    import rawpy
    """
    Saves a raw format image with a particular camera's tables, from database.
    """
    # write jpeg with specified tables
    if source.lower().endswith(('tif', 'tiff', 'png', 'jpg')):
        im = openImageFile(source)
        im = im.toPIL()
    else:
        try:
            with rawpy.imread(source) as raw:
                rgb = raw.postprocess()
                im = Image.fromarray(rgb, 'RGB')
        except:
            logging.getLogger('maskgen').warn( 'Unsupported filetype. (' + source + ')')
            return

    analysis = None
    if rotate :
        im,analysis = check_rotate(im, donor)

    #check_size(im, qtfile)
    im.save(target, subsampling=subsampling, qtables=imageTable, quality=quality)
    maskgen.exif.runexif(['-overwrite_original', '-P', '-q', '-m', '-all=', target])

    if prevTable:
        im.thumbnail((128, 128))
        fd, tempFile = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            im.save(tempFile, subsampling=1, qtables=prevTable,quality=quality)
            maskgen.exif.runexif(['-overwrite_original', '-P', '-PreviewImage<=' + tempFile + '', target])
        except OverflowError:
            prevTable[:] = [[(x - 128) for x in row] for row in prevTable]
            try:
                im.save(tempFile, subsampling=1, qtables=prevTable)
                maskgen.exif.runexif(['-overwrite_original', '-P', '-PreviewImage<=' + tempFile + '', target])
            except Exception as e:
                logging.getLogger('maskgen').warn( 'Preview generation failed : {}'.format(str(e)))
        finally:
            os.remove(tempFile)

    (databaseArgs, donorArgs, calcArgs) = parse_metadata_args(qtfile, donor, target)
    maskgen.exif.runexif(
        [ '-overwrite_original','-P', '-q', '-m', '-unsafe'] + databaseArgs + donorArgs + calcArgs + [target])

    if thumbTable:
        im.thumbnail((128, 128))
        fd, tempFile = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            im.save(tempFile, subsampling=1, qtables=thumbTable)
            maskgen.exif.runexif(['-overwrite_original', '-P', '-ThumbnailImage<=' + tempFile + '', target])
        except OverflowError:
            thumbTable[:] = [[(x - 128) for x in row] for row in thumbTable]
            try:
                im.save(tempFile, subsampling=1, qtables=thumbTable)
                maskgen.exif.runexif(['-overwrite_original', '-P', '-ThumbnailImage<=' + tempFile + '', target])
            except Exception as e:
                logging.getLogger('maskgen').warn( 'Thumbnail generation failed: {}'.format(str(e)))
        finally:
            os.remove(tempFile)

    maskgen.exif.runexif(['-overwrite_original','-P', '-q', '-m', '-XMPToolkit=', target])
    return analysis


def parse_metadata_args(qtfile, source, target):
    # find metadata file
    fname = qtfile.replace('-QT.txt', '-metadata.csv')
    tagsFromDatabase = {}
    tagsFromSource = {}
    tagsCalculated = {}

    with open(fname) as csvFile:
        reader = csv.reader(csvFile)
        for line in reader:
            if line[0] == 'database':
                tagsFromDatabase[line[1]] = line[2]
            elif line[0] == 'source':
                tagsFromSource[line[1]] = line[2]
            elif line[0] == 'compute':
                tagsCalculated[line[1]] = line[2]
            else:
                logging.getLogger('maskgen').warn( 'Uknown tag source (database, source, compute): {}' .format(
                tagsCalculated[line[1]]))

    databaseArgs = []
    donorArgs = []
    calculatedArgs = []

    for tag, val in tagsFromDatabase.iteritems():
        databaseArgs.append(tag + '#=' + val)
    for tag, val in tagsFromSource.iteritems():
        donorArgs.append(get_args_donor(tag, val, source, target))
    for tag, val in tagsCalculated.iteritems():
        calculatedArgs.extend(get_args_calculated(tag, val, source, target))

    return (databaseArgs, donorArgs, calculatedArgs)


def get_args_calculated(tag, val, source, target):
    args = []
    with Image.open(target) as im:
        (width, height) = im.size
    totalSize = width*height
    if tag == '-ExifIFD:ExifImageHeight' or val in ['#ComputeHeight','#CalcHeight']:
        args.append(tag + '=' + str(height))
    elif tag == '-ExifIFD:ExifImageWidth' or val in ['#ComputeWidth','#CalcWidth']:
        args.append(tag + '=' + str(width))
    elif val == '#CalcSizePixels':
        args.append(tag + '=' + str(totalSize))
    elif val =='#CalcSizeWxH':
        args.append(tag + '=' + str(width) + 'x' + str(height))
    else:
        args.append(get_args_donor(tag, val, source, target))

    return args


def get_args_donor(tag, val, source, target):
    m = maskgen.exif.getexif(source, args=['-args', tag], separator='=')
    try:
        return tag + '=' + str(m[tag])
    except KeyError:
        # donor image does not have a value for this tag, so use database value
        return tag + '=' + val


def transform(img, source, target, **kwargs):
    imageTableFile = kwargs['qtfile']
    prevTableFile = imageTableFile.replace('-QT.txt', '-preview.txt')
    prevTableFile = prevTableFile if os.path.isfile(prevTableFile) else None
    thumbTableFile = imageTableFile.replace('-QT.txt', '-thumbnail.txt')
    thumbTableFile = thumbTableFile if os.path.isfile(thumbTableFile) else None
    # thumbTableFile = kwargs['Thumbnail QT File Name'] if 'Thumbnail QT File Name' in kwargs else None

    rotate = kwargs['rotate'] == 'yes' if 'rotate' in kwargs else False
    quality = int(kwargs['quality'])  if 'quality' in kwargs else 0

    donor = kwargs['donor'] if 'donor' in kwargs else None
    if donor is None:
        donor = source
        subsampling = "4:2:2"
    else:
        subsampling  = get_subsampling(donor)
    (imageTable, prevTable, thumbTable) = read_tables(imageTableFile, prevTableFile, thumbTableFile)

    analysis = save_as_camera(source, target, donor, imageTable, prevTable, thumbTable, imageTableFile,
                   rotate=rotate,subsampling=subsampling,quality=quality)

    return analysis ,None

def operation():
    return {'name':'AntiForensicJPGCompression',
            'category':'AntiForensic',
            'description':'Save as a JPEG using a particular camera\'s quantization tables and metadata',
            'software':'maskgen',
            'version':maskgen.__version__[0:3],
            'arguments':{
                'donor':{
                    'type':'donor',
                    'defaultValue': None,
                    'description': 'Donor quantization table file.'
                    },
                'qtfile': {
                    'type': 'fileset:plugins/JpgFromCamera/QuantizationTable',
                    'defaultValue': None,
                    'description': '(Optional) Donor for donated exif data.'
                },
                'rotate': {
                    'type': 'yesno',
                    'defaultvalue': 'no',
                    'description': 'Rotate image according to EXIF'
                },
                'quality': {
                    'type': 'int[0:100]',
                    'defaultvalue': '0',
                    'description': 'Quality Factor'
                }

            },
            'transitions':[
                'image.image'
                ]
            }



def suffix():
    return '.jpg'
