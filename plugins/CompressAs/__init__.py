"""
PAR Government Systems

compress_as takes in two JPEG images, and compresses the first with the q tables of the second
possible future features:
-create/compress thumbnail as well

"""

import os
import tempfile
from PIL import Image
import numpy as np
from bitstring import BitArray
from subprocess import call,Popen, PIPE


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

def runexiftool(args):
  exifcommand = os.getenv('MASKGEN_EXIFTOOL','exiftool')
  command = [exifcommand]
  command.extend(args)
  try:
    p = Popen(command,stdout=PIPE,stderr=PIPE)
    try:
      while True:
        line = p.stdout.readline()
        if line is None or len(line) == 0:
           break
        print line
    finally:
      p.stdout.close()
      p.stderr.close()
  except OSError as e:
    print "Exiftool not installed"
    raise e

def check_rotate(im, jpg_file_name):
    """
    1 = Horizontal (normal)
    2 = Mirror horizontal
    3 = Rotate 180
    4 = Mirror vertical
    5 = Mirror horizontal and rotate 270 CW
    6 = Rotate 90 CW
    7 = Mirror horizontal and rotate 90 CW
    8 = Rotate 270 CW
    """
    exifcommand = os.getenv('MASKGEN_EXIFTOOL','exiftool')
    rotateStr = Popen([exifcommand, '-n', '-Orientation', jpg_file_name],
                        stdout=PIPE).communicate()[0]#

    
    rotation = rotateStr.split(':')[1].strip() if rotateStr.rfind(':') > 0 else '-'

    if rotation == '-':
        return im

    arr = np.array(im)
    if rotation == '2':
        rotatedArr = np.fliplr(arr)
    elif rotation == '3':
        rotatedArr = np.rot90(arr,2)
    elif rotation == '4':
        rotatedArr = np.flipud(arr)
    elif rotation == '5':
        rotatedArr = np.fliplr(arr)
        rotatedArr = np.rot90(rotatedArr,3)
    elif rotation == '6':
        rotatedArr = np.rot90(arr)
    elif rotation == '7':
        rotatedArr = np.fliplr(arr)
        rotatedArr = np.rot90(rotatedArr)
    elif rotation == '8':
        rotatedArr = np.rot90(arr, 3)
    else:
        rotatedArr = arr

    rotatedIm = Image.fromarray(rotatedArr)
    return rotatedIm

def save_as(source, target, donor, qTables,rotate):
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
    im = Image.open(source)
    if rotate:
      im = check_rotate(im,donor) 
    im.save(target, subsampling=1, qtables=finalTable)
    width, height = im.size
    if thumbTable:
        im.thumbnail((128,128))
        fd, tempFile = tempfile.mkstemp(suffix='.jpg')
        try:
            im.save(tempFile, subsampling=1, qtables=thumbTable)
        except OverflowError:
            thumbTable[:] = [[(x - 128) for x in row] for row in thumbTable]
            im.save(tempFile, subsampling=1, qtables=thumbTable)
        try:
          runexiftool(['-overwrite_original','-P','-m','-"ThumbnailImage<=' + tempFile + '"',target])
        finally:
          os.close(fd)
          os.remove(tempFile)
    runexiftool(['-overwrite_original','-q','-all=', target])
    runexiftool(['-P', '-q', '-m', '-TagsFromFile',  donor, '-all:all', '-unsafe', target])
    runexiftool(['-P', '-q', '-m', '-XMPToolkit=',
                                        '-ExifImageWidth=' + str(width),
                                        '-ImageWidth=' + str(width),
                                        '-ExifImageHeight=' + str(height),
                                        '-ImageHeight=' + str(height),
                                        target])

    im.close()


def transform(img,source,target, **kwargs):
    donor = kwargs['donor']
    rotate = kwargs['rotate'] == 'yes'
    
    tables_zigzag = parse_tables(donor[1])
    tables_sorted = sort_tables(tables_zigzag)
    save_as(source, target, donor[1], tables_sorted,rotate)
    
    return False,None
    
def operation():
    return ['AntiForensicExifQuantizationTable','AntiForensicExif', 
            'Save as a JPEG using original tables and EXIF', 'PIL', '1.1.7']
    
def args():
    return [('donor', None, 'JPEG with donor QT'),
            ('apply rotation', 'yes', 'JPEG with donor QT')]

def suffix():
    return '.jpg'
