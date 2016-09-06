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

def parse_GPS(coordinate):
    coord = coordinate.split(' ')
    whole = float(coord[0])
    direction = coord[-1]
    min = float(coord[2][:-1])
    sec = float(coord[3][:-1])

    dec = min + (sec/60)
    dd = round(whole + dec/60, 6)

    if direction == 'S' or direction == 'W':
        dd *= -1

    return str(dd)

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
    names = os.listdir(path)
    if r:
        for dirname, dirnames, filenames in os.walk(path, topdown=True):
            for filename in filenames:
                if filename.lower().endswith(exts):
                    imageList.append(os.path.join(dirname, filename))
    else:
        for f in names:
            if f.lower().endswith(exts):
                imageList.append(os.path.join(path, f))

    return sorted(imageList, key=str.lower)


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


def build_rit_file(imageList, info, csvFile, newNameList=None):
    """
    Records detailed image info
    oldImageFile --> newImageFile
    :param imageList: list of old image names
    :param newNameList: list of new image names
    :param info: list of information fitting the headings described below
    :param csvFile: csv file to store information
    :return: None
    """

    with open(csvFile, 'a') as csv_history:
        historyWriter = csv.writer(csv_history, lineterminator='\n')
        historyWriter.writerow(['ImageFilename', 'CollectionRequestID', 'HDLocation', 'OriginalImageName', 'MD5',
                                'DeviceSN', 'DeviceLocalID', 'LensSN', 'LensLocalId', 'FileType', 'JpgQuality',
                               'ShutterSpeed', 'Aperture', 'ExpCompensation', 'ISO', 'NoiseReduction', 'WhiteBalance',
                               'DegreesKelvin', 'ExposureMode', 'FlashFired', 'FocusMode', 'CreationDate', 'Location',
                               'GPSLatitude', 'OnboardFilter', 'GPSLongitude', 'BitDepth', 'ImageWidth', 'ImageHeight'])
        if newNameList:
            for imNo in xrange(len(imageList)):
                md5 = hashlib.md5(open(imageList[imNo], 'rb').read()).hexdigest()
                historyWriter.writerow([newNameList[imNo], info[imNo][0], info[imNo][1], imageList[imNo], md5] + info[imNo][2:])
        else:
            for imNo in xrange(len(imageList)):
                md5 = hashlib.md5(open(imageList[imNo], 'rb').read()).hexdigest()
                historyWriter.writerow(['', info[imNo][0:2], imageList[imNo], md5] + info[imNo][2:])


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
        tallyWriter.writerow(['DeviceSN', 'DeviceLocalID', 'LensSN', 'LocalLensID', 'Extension',
                                'ShutterSpeed', 'Aperture', 'ISO', 'BitDepth', 'Tally'])
        for line in data:
            trueLine = line[2:6] + [line[6]] + [line[8]] + [line[9]] + [line[11]] + [line[23]]
            if trueLine not in final:
                final.append(trueLine)
                final.append(1)
            else:
                lineIdx = final.index(trueLine)
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


def parse_image_info(imageList, path='', rec=False, collReq='', camera='', localcam='', lens='', locallens='', hd='',
                     sspeed='', fnum='', expcomp='', iso='', noisered='', whitebal='', expmode='', flash='',
                     focusMode='', kvalue='', location='', obfilter=''):
    """
    Prepare list of values about the specified image.
    If an argument is entered as an empty string, will check image's exif data for it.
    :param imageList: list of images to examine
    :param path: base image directory
    ...
    :return: list containing only values of each argument. The value will be N/A if empty string
    is supplied and no exif data can be found.

    GUIDE of INDICES: (We'll make this a dictionary eventually)
    0: CollectionRequestID
    1: HD Location
    2. DeviceSN
    3. DeviceLocalID
    4. LensSN
    5. LensLocalID
    6. FileType
    7. JPGQuality
    8. ShutterSpeed
    9. Aperture
    10. ExpCompensation
    11. ISO
    12. NoiseReduction
    13. WhiteBalance
    14. DegreesKelvin
    15. ExposureMode
    16. FlashFired
    17. FocusMode
    18. CreationDate
    19. Location
    20. GPSLatitude
    21. OnboardFilter
    22. GPSLongitude
    23. BitDepth
    24. ImageWidth
    25. ImageHeight
    """
    exiftoolstr = ''
    data = []
    master = [collReq, hd, '', localcam, '', locallens] + [''] * 8 + [kvalue] + [''] * 4 + [location, '', obfilter] + [''] * 4
    missingIdx = []

    if camera:
        master[2] = camera
    else:
        exiftoolstr += '-SerialNumber '
        missingIdx.append(2)

    if lens:
        master[4] = lens
    else:
        exiftoolstr += '-LensSerialNumber '
        missingIdx.append(4)

    exiftoolstr += '-JPEG_Quality '
    missingIdx.append(7)

    if sspeed:
        master[8] = sspeed
    else:
        exiftoolstr += '-ExposureTime '
        missingIdx.append(8)

    if fnum:
        master[9] = fnum
    else:
        exiftoolstr += '-FNumber '
        missingIdx.append(9)

    if expcomp:
        master[10] = expcomp
    else:
        exiftoolstr += '-ExposureCompensation '
        missingIdx.append(10)

    if iso:
        master[11] = iso
    else:
        exiftoolstr += '-ISO '
        missingIdx.append(11)

    if noisered:
        master[12] = noisered
    else:
        exiftoolstr += '-NoiseReduction '
        missingIdx.append(12)

    if whitebal:
        master[13] = whitebal
    else:
        exiftoolstr += '-WhiteBalance '
        missingIdx.append(13)

    if expmode:
        master[15] = expmode
    else:
        exiftoolstr += '-ExposureMode '
        missingIdx.append(15)

    if flash:
        master[16] = flash
    else:
        exiftoolstr += '-Flash '
        missingIdx.append(16)

    if focusMode:
        master[17] = focusMode
    else:
        exiftoolstr += '-FocusMode '
        missingIdx.append(17)


    exiftoolstr += '-BitsPerSample -GPSLatitude -GPSLongitude -CreateDate -ImageWidth -ImageHeight '
    missingIdx.extend([23, 20, 22, 18, 24, 25])

    if exiftoolstr:
        counter = 0
        exifDataStr = ''
        exifData = []
        if path:
            if rec:
                exifDataStr += subprocess.Popen('exiftool -f -r ' + exiftoolstr + path, stdout=subprocess.PIPE).communicate()[0]
            else:
                exifDataStr += subprocess.Popen('exiftool -f ' + exiftoolstr + path, stdout=subprocess.PIPE).communicate()[0]
            exifData = exifDataStr.split('\r\n')[:-3]
        else:
            while counter < len(imageList):
                if len(imageList) - counter > 500:
                    exifDataStr += subprocess.Popen('exiftool -f ' + exiftoolstr + ' '.join(imageList[counter:counter+500]),
                                                stdout=subprocess.PIPE).communicate()[0]
                elif len(imageList) - counter <= 500:
                    exifDataStr += subprocess.Popen('exiftool -f ' + exiftoolstr + ' '.join(imageList[counter:]),
                                                stdout=subprocess.PIPE).communicate()[0]
                exifDataList = exifDataStr.split('\r\n')[:-2]
                exifData.extend(exifDataList[:])
                counter += 500

        sub = '====='
        imageIndices = []
        newExifData = []
        for idx, item in enumerate(exifData):
            if sub in item:
                imageIndices.append(idx)
            else:
                val = item.split(':', 1)[1].strip()
                if val == '-':
                    val = ''
                newExifData.append(val)
        data = []
        diff = imageIndices[1] - imageIndices[0] - 1
        j = 0
        for i in xrange(len(imageList)):
            data.append(master[:])
            data[i][6] = os.path.splitext(imageList[i])[1]
            newExifSubset = newExifData[j:j + diff]
            k = 0
            for dataIdx in missingIdx:
                data[i][dataIdx] = newExifSubset[k]
                k += 1
            j += diff
            if data[i][20] and data[i][22]:
                data[i][20] = parse_GPS(data[i][20])
                data[i][22] = parse_GPS(data[i][22])

    return data

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', '--dir',              default='',                     help='Specify directory')
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

    parser.add_argument('-T', '--tally',            action='store_true',            help='Produce tally output')
    parser.add_argument('-i', '--id',               default='',                     help='Camera serial #')
    parser.add_argument('-o', '--localid',          default='',                     help='Local ID no. (cage #, etc.)')
    parser.add_argument('-L', '--lens',             default='',                     help='Lens serial #')
    parser.add_argument('-O', '--locallens',        default='',                     help='Lens local ID')
    parser.add_argument('-H', '--hd',               default='',                     help='Hard drive location letter')
    parser.add_argument('-s', '--sspeed',           default='',                     help='Shutter Speed')
    parser.add_argument('-N', '--fnum',             default='',                     help='f-number')
    parser.add_argument('-e', '--expcomp',          default='',                     help='Exposure Compensation')
    parser.add_argument('-I', '--iso',              default='',                     help='ISO')
    parser.add_argument('-n', '--noisered',         default='',                     help='Noise Reduction')
    parser.add_argument('-w', '--whitebal',         default='',                     help='White Balance')
    parser.add_argument('-k', '--kvalue',           default='',                     help='KValue')
    parser.add_argument('-E', '--expmode',          default='',                     help='Exposure Mode')
    parser.add_argument('-F', '--flash',            default='',                     help='Flash Fired')
    parser.add_argument('-a', '--focusmode',        default='',                     help='Focus Mode')
    parser.add_argument('-l', '--location',         default='',                     help='location')
    parser.add_argument('-c', '--filter',           default='',                     help='On-board filter')
    parser.add_argument('-C', '--collection',       default='',                     help='Collection Req #')

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
    imageInfo = parse_image_info(imageList, path=args.dir, rec=args.recursive, collReq=args.collection,
                                 camera=args.id, localcam=args.localid, lens=args.lens, locallens=args.locallens,
                                 hd=args.hd, sspeed=args.sspeed, fnum=args.fnum, expcomp=args.expcomp,
                                 iso=args.iso, noisered=args.noisered, whitebal=args.whitebal,
                                 expmode=args.expmode, flash=args.flash, focusMode=args.focusmode,
                                 kvalue=args.kvalue, location=args.location, obfilter=args.filter)
    print 'Successfully built image info!'

    # copy
    try:
        count = int(prefs['seq'])
    except KeyError:
        count = 0
        add_seq(args.preferences)


    csv_keywords = os.path.join(args.secondary, datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                    prefs['organization'] + prefs['username'] + '-' + 'keywords.csv')
    csv_metadata = os.path.join(args.secondary, datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                    prefs['organization'] + prefs['username'] + '-' + 'xdata.csv')
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
    if args.dir:
        change_all_metadata.process(args.secondary, newData, quiet=True)
    else:
        change_all_metadata.process(newNameList, newData, quiet=True)


    print 'Building RIT file'
    csv_rit = os.path.join(args.secondary, os.path.basename(newNameList[0])[0:11] + 'rit.csv')
    build_rit_file(imageList, imageInfo, csv_rit, newNameList=newNameList)
    'Success'

    # history file:
    print 'Building history file'
    csv_history = os.path.join(args.secondary, os.path.basename(newNameList[0])[0:11] + 'history.csv')
    build_history_file(imageList, newNameList, csv_history)

    if args.tally:
        # write final csv
        print 'Building tally file'
        csv_tally = os.path.join(args.secondary, os.path.basename(newNameList[0])[0:11] + 'tally.csv')
        tally_images(imageInfo, csv_tally)
        print 'Successfully tallied image data'

    print 'Complete!'

if __name__ == '__main__':
    main()
