"""
PAR Government Systems

compress_as takes in two JPEG images, and compresses the first with the q tables of the second

"""

import os
import tempfile
from PIL import Image
import numpy as np
from bitstring import BitArray
import maskgen.exif


def parse_tables(imageFile):
    """
    Grab all quantization tables from jpg header
    :param imageFile: string containing jpg image filename
    :return: list of lists of unsorted quantization tables
    """

    # open the image and scan for q table marker "FF DB"
    s = open(imageFile, 'rb')
    b = BitArray(s)
    ffdb = b.findall('0xffdb', bytealigned=True)

    # grab the tables, based on format
    tables = []
    for start in ffdb:
        subset = b[start + 5 * 8:start + 134 * 8]
        check = subset.find('0xff', bytealigned=True)
        if check:
            subsubset = subset[0:check[0]]
            tables.append(subsubset)
        else:
            tables.append(subset[0:64 * 8])
            tables.append(subset[65 * 8:])

    # concatenate the tables, and convert them from bitarray to list
    finalTable = []
    for table in tables:
        tempTable = []

        bi = table.bin
        for i in xrange(0, len(bi), 8):
            byte = bi[i:i + 8]
            val = int(byte, 2)
            tempTable.append(val)
        finalTable.append(tempTable)
    s.close()
    return finalTable

def sort_tables(tablesList):
    """
    Un-zigzags a list of quantization tables
    :param tablesList: list of lists of unsorted quantization tables
    :return: list of lists of sorted quantization tables
    """

    # hardcode order, since it will always be length 64
    indices = [0,1,5,6,14,15,27,28,2,4,7,13,16,26,29,42,3,8,12,17,25,30,41,43,
               9,11,18,24,31,40,44,53,10,19,23,32,39,45,52,54,20,22,33,38,46,
               51,55,60,21,34,37,47,50,56,59,61,35,36,48,49,57,58,62,63]

    newTables = []
    for listIdx in xrange(len(tablesList)):
        if len(tablesList[listIdx]) == 64:
            tempTable = []
            for elmIdx in xrange(0,64):
                tempTable.append(tablesList[listIdx][indices[elmIdx]])
            newTables.append(tempTable)
    return newTables

def check_rotate(im, jpg_file_name):
    return Image.fromarray(maskgen.exif.rotateAccordingToExif(np.asarray(im),maskgen.exif.getOrientationFromExif(jpg_file_name)))

def cs_save_as(source, target, donor, qTables,rotate):
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
    if len(qTables) > 2:
        thumbTable = qTables[0:2]
        finalTable = qTables[-2:]
    elif len(qTables) < 2:
        finalTable = [qTables, qTables]
    else:
        finalTable = qTables

    # write jpeg with specified tables
    with open(source,'rb') as fp:
        im = Image.open(fp)
        im.load()
    if rotate:
      im = check_rotate(im,donor) 
    im.save(target, subsampling=1, qtables=finalTable)
    width, height = im.size
    maskgen.exif.runexif(['-overwrite_original', '-q', '-all=', target])
    maskgen.exif.runexif(['-P', '-q', '-m', '-TagsFromFile', donor, '-all:all', '-unsafe', target])
    if thumbTable:
        im.thumbnail((128, 128))
        fd, tempFile = tempfile.mkstemp(suffix='.jpg')
        os.close(fd)
        try:
            im.save(tempFile, subsampling=1, qtables=thumbTable)
            maskgen.exif.runexif(['-overwrite_original', '-P',  '-ThumbnailImage<=' + tempFile + '', target])
        except OverflowError:
            thumbTable[:] = [[(x - 128) for x in row] for row in thumbTable]
            try:
                im.save(tempFile, subsampling=1, qtables=thumbTable)
                maskgen.exif.runexif(['-overwrite_original', '-P', '-ThumbnailImage<=' + tempFile + '', target])
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
    
    tables_zigzag = parse_tables(donor[1])
    tables_sorted = sort_tables(tables_zigzag)
    cs_save_as(source, target, donor[1], tables_sorted,rotate)
    
    return None,None
    
def operation():
    return {'name':'AntiForensicExifQuantizationTable',
            'category':'AntiForensicExif',
            'description':'Save as a JPEG using original tables and EXIF',
            'software':'PIL',
            'version':'1.1.7',
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
                }
            },
            'transitions': [
                'image.image'
            ]
            }

def suffix():
    return '.jpg'
