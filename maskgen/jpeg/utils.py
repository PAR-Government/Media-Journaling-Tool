import os
import sys
import tempfile
from bitstring import BitArray
from maskgen import exif
from PIL import Image

def check_rotate(im, jpg_file_name):
    return Image.fromarray(exif.rotateAccordingToExif(np.asarray(im),exif.getOrientationFromExif(jpg_file_name)))

def read_tables(imageTableFile, prevTableFile=None, thumbTableFile=None):
    try:
        imageTableData = open(imageTableFile)
    except IOError:
        print 'Invalid quantization tables.'
        return

    lineCount = 0
    imageTable = [[], []]
    for line in imageTableData:
        line = line.strip().split('\t')
        if lineCount < 8:
            imageTable[0].extend(map(int, line))
            lineCount += 1
        else:
            imageTable[1].extend(map(int, line))
    if len(imageTable[0]) != 64 or len(imageTable[1]) != 64:
        print 'Invalid quantization tables.'
        return

    if thumbTableFile:
        thumbTableData = open(thumbTableFile)
        lineCount = 0
        thumbTable = [[], []]
        for line in thumbTableData:
            line = line.strip().split('\t')
            if lineCount < 8:
                thumbTable[0].extend(map(int, line))
                lineCount += 1
            else:
                thumbTable[1].extend(map(int, line))
    else:
        thumbTable = None

    if prevTableFile:
        prevTableData = open(prevTableFile)
        lineCount = 0
        prevTable = [[], []]
        for line in prevTableData:
            line = line.strip().split('\t')
            if lineCount < 8:
                prevTable[0].extend(map(int, line))
                lineCount += 1
            else:
                prevTable[1].extend(map(int, line))
    else:
        prevTable = None

    return imageTable, prevTable, thumbTable

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

def write_tables(qTables):
    """
    Write the final QT tables
    :param qTables: lif of QT Tables
    :param max:
    :return:
    """
    if len(qTables) == 6:
        thumbTable = qTables[0:2]
        prevTable = qTables[2:4]
        finalTable = qTables[4:6]
    elif len(qTables) > 2 and len(qTables) < 6:
        thumbTable = qTables[0:2]
        finalTable = qTables[-2:]
    elif len(qTables) > 6:
        finalTable = qTables[-2:]
    else:
        finalTable = qTables

    fd, tempTxtTable = tempfile.mkstemp(suffix='.txt')
    os.close(fd)

    count = 0
    with open(tempTxtTable, 'w') as t:
        for table in finalTable:
            line = ''
            for val in table:
                if count == 7:
                    line+=str(val)+'\n'
                    t.write(line)
                    line = ''
                    count = 0
                else:
                    line+=str(val)+' '
                    count+=1
            t.write('\n')
    return tempTxtTable


def get_subsampling(image_file):
    """
    FInd the YCBCr subsampling for the image file
    :param image_file:
    :return: 4:2:2 if the image_file is NOne or the sampling tag is not found.
    """
    if image_file is None:
        return '4:2:2'
    ss = exif.getexif(image_file, ['-f', '-n', '-args', '-YCbCrSubsampling'], separator='=')
    # can only handle 4:4:4, 4:2:2, or 4:1:1
    yyval = ss['-YCbCrSubSampling'] if '-YCbCrSubSampling' in ss else ''
    if yyval == '2 1':
        return '4:2:2'
    elif yyval in ['4 1','2 2']:
        return '4:1:1'
    else:
        return '4:4:4'