"""
hp_data

tool for bulk renaming of files to standard
"""

import argparse
import shutil
import os
import change_all_metadata
import datetime
import sys
import csv
import boto3
import botocore
import hashlib
import subprocess
from PIL import Image, ImageStat


exts = ('.jpg', '.jpeg', '.tif', '.tiff', '.nef', '.cr2', '.avi', '.mov', '.mp4')
orgs = {'RIT':'R', 'Drexel':'D', 'U of M':'M', 'PAR':'P'}
codes = ['R', 'D', 'M', 'P']

def copyrename(image, path, usrname, org, seq, other):
    """
    Performs the copy/rename operation
    :param image: original filename (full path)
    :param path: destination path
    :param usrname: username for new filename
    :param org: organization code for new filename
    :param seq: sequence # for new filename
    :param other: other info for new filename
    :return: full path of new file
    """
    newNameStr = datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                    org + usrname + '-' + seq
    if other:
        newNameStr = newNameStr + '-' + other

    currentExt = os.path.splitext(image)[1]
    newPathName = os.path.join(path, newNameStr + currentExt)
    shutil.copy2(image, newPathName)
    return newPathName


def parse_prefs(data):
    """
    Parse preferences file
    :param data: string containing path to preferences file
    :return: dictionary containing preference option and setting (e.g. {username:AS...})
    """
    newData = {}
    # open text file
    try:
        with open(data) as f:
            for line in f:
                line = line.rstrip('\n')
                (tag, descr) = line.split('=')
                newData[tag.lower()] = descr
    except IOError:
        print('Input file: ' + data + ' not found. ' + 'Please try again.')
        sys.exit()

    try:
        (newData['organization'] and newData['username'])
    except KeyError:
        print 'Must specify ''username'' and ''organization'' in preferences file'
        sys.exit(0)

    # convert to single-char organization code
    if len(newData['organization']) > 1:
        try:
            newData['organization'] = orgs[newData['organization']]
        except KeyError:
            print 'Error: organization: ' + newData['organization'] + ' not recognized'
            sys.exit(0)
    elif len(newData['organization']) == 1:
        if newData['organization'] not in codes:
            print 'Error: organization code: ' + newData['organization'] + ' not recognized'
            sys.exit(0)

    return newData


def pad_to_5_str(num):
    """
    Converts an int to a string, and pads to 5 chars (1 -> '00001')
    :param num: int to be padded
    :return: padded string
    """

    return '{:=05d}'.format(num)


def grab_individuals(files):
    """
    Grab individual files. Probably unnecessary,
    but it's nice to have things consistent
    :param files: filenames
    :return: list of filenames
    """
    imageList = []
    for f in files:
        imageList.append(f)
    return imageList


def grab_range(files):
    """
    Grabs a range of filenames
    :param files: list of two filenames
    :return: list of all files between them, inclusive
    """
    if os.path.isabs(files[0]):
        path = os.path.dirname(files[0])
    else:
        path = os.getcwd()

    allFiles = sorted(grab_dir(path))
    start = allFiles.index(files[0])
    end = allFiles.index(files[1])

    return allFiles[start:end+1]


def grab_dir(path, r=False):
    """
    Grabs all image files in a directory
    :param path: path to directory of desired files
    :param r: Recursively grab images from all subdirectories as well
    :return: list of images in directory
    """
    imageList = []
    if r:
        for dirname, dirnames, filenames in os.walk(path):
            for filename in filenames:
                if filename.lower().endswith(exts):
                    imageList.append(os.path.join(dirname, filename))
    else:
        names = os.listdir(path)
        for f in names:
            if f.lower().endswith(exts):
                imageList.append(os.path.join(path, f))

    return imageList


def write_seq(prefs, newSeq):
    """
    Updates the sequence value in a file
    :param prefs: the file to be updated
    :param newSeq: string containing the new 5-digit sequence value (e.g. '00001'
    :return: None
    """
    f = open(prefs, 'r')
    data = f.read()
    f.close()

    i = data.find('seq=')
    currentSeq = data[i + 4:i + 10]
    newData = data.replace(currentSeq, newSeq)
    f = open(prefs, 'w')
    f.write(newData)
    f.close()


def add_seq(filename):
    """
    Appends a sequence field and an initial sequence to a file
    (Specifically, adds '\nseq=00000'
    :param filename: file to be edited
    :return: None
    """
    with open(filename, 'ab') as f:
        f.write('\nseq=00000')


def build_keyword_file(image, keywords, csvFile):
    """
    Adds keywords to specified file
    :param image: image filename that keywords apply to
    :param keywords: list of keywords
    :param csvFile: csv file to store information
    :return: None
    """
    with open(csvFile, 'a') as csv_keywords:
        keywordWriter = csv.writer(csv_keywords, lineterminator='\n')
        for word in keywords:
            keywordWriter.writerow([image, word])


def build_xmetadata_file(image, data, csvFile):
    """
    Adds external metadata to specified file.
    Assumes headers (keys) are already written - use parse_extra for this
    :param image: image filename that x metadata applies to
    :param data: list of list of values
    :param csvFile: csv file to store information
    :return: None
    """
    fullData = [image] + data
    with open(csvFile, 'a') as csv_metadata:
        xmetadataWriter = csv.writer(csv_metadata, lineterminator='\n')
        xmetadataWriter.writerow(fullData)


def build_rit_file(imageList, newNameList, info, csvFile):
    """
    Creates an easy-to-follow history for keeping record of image names
    oldImageFile --> newImageFile
    :param image: old image file
    :param newName: new image file
    :param info: list of information fitting the headings described in below
    :param csvFile: csv file to store information
    :return: None
    """

    with open(csvFile, 'a') as csv_history:
        historyWriter = csv.writer(csv_history, lineterminator='\n')
        historyWriter.writerow(['Original Name', 'New Name', 'MD5', 'Serial Number', 'Local ID', 'Lens ID',
                                'HD Location', 'Shutter Speed', 'FNumber', 'Exposure Comp', 'ISO', 'Noise Reduction',
                                'White Balance', 'Exposure Mode', 'Flash', 'Autofocus', 'KValue', 'Location', 'Bit Depth'])
        for imNo in range(len(imageList)):
            md5 = hashlib.md5(open(imageList[imNo], 'rb').read()).hexdigest()
            historyWriter.writerow([imageList[imNo], newNameList[imNo], md5] + info[imNo])


def build_history_file(imageList, newNameList, csvFile):
    """
    Creates an easy-to-follow history for keeping record of image names
    oldImageFile --> newImageFile
    :param image: old image file
    :param newName: new image file
    :param csvFile: csv file to store information
    :return: None
    """

    with open(csvFile, 'a') as csv_history:
        historyWriter = csv.writer(csv_history, lineterminator='\n')
        historyWriter.writerow(['Original Name', 'New Name', 'MD5'])
        for imNo in range(len(imageList)):
            md5 = hashlib.md5(open(imageList[imNo], 'rb').read()).hexdigest()
            historyWriter.writerow([imageList[imNo], newNameList[imNo], md5])

def parse_extra(data, csvFile):
    """
    Parse key-value pairs of extra/external metadata, and initializes
    csv file with keys as headers.
    :param data:
    :param csvFile:
    :return:
    """
    keys = ['Filename'] + data[::2]
    values = data[1::2]
    #if valid_keys(keys):
    with open(csvFile, 'w') as csv_metadata:
        xmetadataWriter = csv.writer(csv_metadata, lineterminator='\n')
        xmetadataWriter.writerow(keys)
    return values


def load_keys():
    """
    load keyword validation file
    :return: list valid keys
    """
    keys = []
    try:
        with open('extra.csv') as csvFile:
            keyReader = csv.reader(csvFile)
            for row in keyReader:
                keys.append(row[0])
    except IOError:
        print 'No key validation file found'
        sys.exit()
    return keys


def valid_keys(testKeys):
    """
    check if user keys are in the master list
    :param testKeys: keys to check
    :return: Boolean describing whether keys are valid
    """
    trueKeys = load_keys()
    if set(testKeys).issubset(trueKeys):
        return True
    else:
        return False


def get_id(image):
    """
    Check exif data for camera serial number
    :param image: image filename to check
    :return: string with serial number ID
    """
    exiftoolOutput = subprocess.Popen(['exiftool', '-SerialNumber', image],
                                        stdout=subprocess.PIPE).communicate()[0]
    if exiftoolOutput:
        return exiftoolOutput.split(':',1)[1].strip()
    else:
        return 'N/A'


def get_lens_id(image):
    """
    Check exif data for camera lens serial number
    :param image: image filename to check
    :return: string with serial number ID
    """
    exiftoolOutput = subprocess.Popen(['exiftool', '-LensSerialNumber', image],
                                      stdout=subprocess.PIPE).communicate()[0]
    if exiftoolOutput:
        return exiftoolOutput.split(':', 1)[1].strip()
    else:
        return 'N/A'

def tally_images(data, csvFile):
    final = []
    try:
        with open(csvFile, 'rb+') as csv_tally:
            tallyReader = csv.reader(csv_tally, lineterminator='\n')
            next(tallyReader, None) # skip header
            for row in tallyReader:
                final.append(row[:-1])
                final.append(int(row[-1]))
    except IOError:
        print 'No tally file found. Creating...'

    with open(csvFile, 'wb') as csv_tally:
        tallyWriter = csv.writer(csv_tally, lineterminator='\n')
        tallyWriter.writerow(['Serial Number', 'Local ID', 'Lens ID', 'Extension',
                                  'Shutter Speed', 'FNumber', 'ISO', 'Bit Depth', 'Tally'])
        for line in data:
            trueLine = line[0:3] + [line[16]] + [line[4]] + [line[5]] + [line[7]] + [line[15]]
            if trueLine not in final:
                final.append(trueLine)
                final.append(1)
            else:
                lineIdx = final.index(trueLine)
                #final[lineIdx + 1] = int(final[lineIdx + 1] + 1
                final[lineIdx + 1] += 1
        i = 0
        while i < len(final):
            tallyWriter.writerow(final[i] + [final[i+1]])
            i += 2

def s3_prefs(values, upload=False):
    """
    Parse S3 data and download/upload preferences file
    :param values: bucket/path of s3
    :param upload: Will upload pref file if specified, download otherwise
    :return: None
    """
    s3 = boto3.client('s3', 'us-east-1')
    BUCKET = values[0][0:values[0].find('/')]
    DIR = values[0][values[0].find('/') + 1:]
    if upload:
        try:
            s3.upload_file('preferences.txt', BUCKET, DIR + '/preferences.txt')
        except WindowsError:
            sys.exit('local file preferences.txt not found!')
    else:
        s3.download_file(BUCKET, DIR + '/preferences.txt', 'preferences.txt')


def parse_image_info(imageList, camera, localid, lens, hd, sspeed, fnum, expcomp, iso, noisered, whitebal,
                     expmode, flash, autofocus, kvalue, location):
    """
    Prepare list of values about the specified image.
    If an argument is entered as an empty string, will check image's exif data for it.
    :param image: filename of image to check
    ...
    :return: list containing only values of each argument. The value will be N/A if empty string
    is supplied and no exif data can be found.

    GUIDE of INDICES: (We'll make this a dictionary eventually)
    0: camera serial number
    1: local ID number (e.g. RIT Cage #)
    2: Lens serial number
    3: Hard Drive Location
    4: Shutter Speed
    5: F-Number
    6: Exposure Compensation
    7: ISO
    8: Noise Reduction
    9: White Balance
    10: Exposure Mode
    11: Flash
    12: Autofocus
    13: K-Value
    14: Location
    15: Bit Depth
    16: File extension
    """
    exiftoolstr = ''
    data = []
    master = ['N/A', localid, 'N/A', hd] + ['N/A'] * 9 + [kvalue, location, 'N/A', 'N/A']
    missingIdx = []

    if camera:
        master[0] = camera
    else:
        exiftoolstr += '-SerialNumber '
        missingIdx.append(0)

    if lens:
        master[2] = camera
    else:
        exiftoolstr += '-LensSerialNumber '
        missingIdx.append(2)

    if sspeed:
        master[4] = sspeed
    else:
        exiftoolstr += '-ExposureTime '
        missingIdx.append(4)

    if fnum:
        master[5] = fnum
    else:
        exiftoolstr += '-FNumber '
        missingIdx.append(5)

    if expcomp:
        master[6] = expcomp
    else:
        exiftoolstr += '-ExposureCompensation '
        missingIdx.append(6)

    if iso:
        master[7] = iso
    else:
        exiftoolstr += '-ISO '
        missingIdx.append(7)

    if noisered:
        master[8] = noisered
    else:
        exiftoolstr += '-NoiseReduction '
        missingIdx.append(8)

    if whitebal:
        master[9] = whitebal
    else:
        exiftoolstr += '-WhiteBalance '
        missingIdx.append(9)

    if expmode:
        master[10] = expmode
    else:
        exiftoolstr += '-ExposureMode '
        missingIdx.append(10)

    if flash:
        master[11] = flash
    else:
        exiftoolstr += '-Flash '
        missingIdx.append(11)

    if autofocus:
        master[12] = autofocus
    else:
        exiftoolstr += '-FocusMode '
        missingIdx.append(12)

    exiftoolstr += '-BitsPerSample '
    missingIdx.append(15)

    if exiftoolstr:
        for imageIdx in xrange(len(imageList)):
            data.append(master[:])
            exifData = subprocess.Popen('exiftool -f ' + exiftoolstr + imageList[imageIdx], stdout=subprocess.PIPE).communicate()[0]
            exifList = exifData[:-1].replace('\r', '').split('\n')
            newExifList = []
            for item in exifList:
                newExifItem = item.split(':', 1)
                #key = newExifItem[0].strip()
                val = newExifItem[1].strip()
                if val == '-':
                    val = 'N/A'
                newExifList.append(val)
            j=0
            for dataIdx in missingIdx:
                data[imageIdx][dataIdx] = newExifList[j]
                j += 1
            extension = os.path.splitext(imageList[imageIdx])[1].strip()
            data[imageIdx][16] = extension

    return data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', '--dir',              default=os.getcwd(),            help='Specify directory')
    parser.add_argument('-R', '--recursive',        action='store_true',            help='Operate on subdirectories')
    parser.add_argument('-f', '--files',                                            help='Specify certain files')
    parser.add_argument('-r', '--range',                                            help='Specify range of files')
    parser.add_argument('-m', '--metadata',         default='metadata.txt',         help='Specify metadata txt file')
    parser.add_argument('-X', '--extraMetadata',    nargs='+',                      help='Additional non-standard metadata')
    parser.add_argument('-K', '--keywords',         nargs='+',                      help='Keywords for later searching')
    parser.add_argument('-S', '--secondary',        default=os.getcwd(),            help='Secondary storage location for copies')
    parser.add_argument('-P', '--preferences',      default='preferences.txt',      help='User preferences file')
    parser.add_argument('-A', '--additionalInfo',   default='',                     help='User preferences file')
    parser.add_argument('-B', '--s3Bucket',         default ='',                    help='S3 bucket/path')

    parser.add_argument('-T', '--rit',              action='store_true',            help='Produce output for RIT')
    parser.add_argument('-i', '--id',               default='',                     help='Camera serial #')
    parser.add_argument('-o', '--lid',              default='N/A',                  help='Local ID no. (cage #, etc.)')
    parser.add_argument('-L', '--lens',             default='',                     help='Lens serial #')
    parser.add_argument('-H', '--hd',               default='N/A',                  help='Hard drive location letter')
    parser.add_argument('-s', '--sspeed',           default='',                     help='Shutter Speed')
    parser.add_argument('-N', '--fnum',             default='',                     help='f-number')
    parser.add_argument('-e', '--expcomp',          default='',                     help='Exposure Compensation')
    parser.add_argument('-I', '--iso',              default='',                     help='ISO')
    parser.add_argument('-n', '--noisered',         default='',                     help='Noise Reduction')
    parser.add_argument('-w', '--whitebal',         default='',                     help='White Balance')
    parser.add_argument('-k', '--kvalue',           default='N/A',                  help='KValue')
    parser.add_argument('-E', '--expmode',          default='',                     help='Exposure Mode')
    parser.add_argument('-F', '--flash',            default='',                     help='Flash Fired')
    parser.add_argument('-a', '--autofocus',        default='',                     help='autofocus')
    parser.add_argument('-l', '--location',         default='N/A',                  help='location')


    args = parser.parse_args()
    if args.s3Bucket:
        try:
            s3_prefs([args.s3Bucket])
        except botocore.exceptions.ClientError:
            try:
                s3_prefs([args.s3Bucket], upload=True)
            except botocore.exceptions.ClientError:
                sys.exit('Bucket/path not found!')
        prefs = parse_prefs('preferences.txt')
    else:
        prefs = parse_prefs(args.preferences)

    print 'Successfully pulled preferences'

    # grab files
    imageList = []

    if args.files:
        imageList.extend(grab_individuals(args.files))
    elif args.range:
        fRange = args.range.split(' ')
        imageList.extend(grab_range(fRange))
    else:
        imageList.extend(grab_dir(args.dir, args.recursive))
    print 'Successfully grabbed images'

    print 'Collecting image data, this will take time for large amounts of images...'
    imageInfo = parse_image_info(imageList, args.id, args.lid, args.lens, args.hd, args.sspeed, args.fnum,
                            args.expcomp, args.iso, args.noisered, args.whitebal, args.expmode, args.flash,
                            args.autofocus, args.kvalue, args.location)
    print 'Successfully built image info!'

    # copy
    try:
        count = int(prefs['seq'])
    except KeyError:
        count = 0
        add_seq(args.preferences)


    csv_keywords = os.path.join(args.secondary, 'keywords.csv')
    csv_metadata = os.path.join(args.secondary, 'xdata.csv')
    try:
        extraValues = parse_extra(args.extraMetadata, csv_metadata)
    except TypeError:
        extraValues = None

    print 'Copying files...'
    newNameList = []
    for image in imageList:
        newName = copyrename(image, args.secondary, prefs['username'], prefs['organization'], pad_to_5_str(count), args.additionalInfo)
        if args.keywords:
            build_keyword_file(newName, args.keywords, csv_keywords)
        if args.extraMetadata:
            build_xmetadata_file(newName, extraValues, csv_metadata)
        newNameList += [newName]
        count += 1
    print 'Successfully copy and rename of files'

    write_seq(args.preferences, pad_to_5_str(count))
    if args.s3Bucket:
        s3_prefs([args.s3Bucket], upload=True)
    print 'Successful preferences update'

    # change metadata of copies
    print 'Updating metadata...'
    newData = change_all_metadata.parse_file(args.metadata)
    change_all_metadata.process(newNameList, newData, quiet=True)


    if args.rit:
        csv_rit = os.path.join(args.secondary, 'rit.csv')
        build_rit_file(imageList, newNameList, imageInfo, csv_rit)

    # history file:
    csv_history = os.path.join(args.secondary, 'history.csv')
    build_history_file(imageList, newNameList, csv_history)
    print 'Successfully built history'

    # write final csv
    csv_tally = os.path.join(args.secondary, 'tally.csv')
    tally_images(imageInfo, csv_tally)
    print 'Successfully tallied image data'

if __name__ == '__main__':
    main()