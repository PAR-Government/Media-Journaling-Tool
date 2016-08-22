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


def build_history_file(image, newName, csvFile):
    """
    Creates an easy-to-follow history for keeping record of image names
    oldImageFile --> newImageFile
    :param image: old image file
    :param newName: new image file
    :param csvFile: csv file to store information
    :return: None
    """
    md5 = hashlib.md5(open(image, 'rb').read()).hexdigest()
    with open(csvFile, 'a') as csv_history:

        historyWriter = csv.writer(csv_history, lineterminator='\n')
        historyWriter.writerow([image, newName, md5])


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
    if valid_keys(keys):
        with open(csvFile, 'w') as csv_metadata:
            xmetadataWriter = csv.writer(csv_metadata, lineterminator='\n')
            xmetadataWriter.writerow(keys)
        return values


def load_keys():
    keys = []
    try:
        with open('key_value_pairs.csv') as csvFile:
            keyReader = csv.reader(csvFile)
            for row in keyReader:
                keys.append(row[0])
    except IOError:
        print 'No key validation file found'
        sys.exit()
    return keys


def valid_keys(testKeys):
    trueKeys = load_keys()
    if set(testKeys).issubset(trueKeys):
        return True
    else:
        return False


def get_id(image):

    exiftoolOutput = subprocess.Popen(['exiftool', '-SerialNumber', image],
                                        stdout=subprocess.PIPE).communicate()[0]
    if exiftoolOutput:
        return exiftoolOutput.split(':',1)[1].strip()
    else:
        sys.exit('Error: A camera serial number was not provided and none could be found in image data.')


def get_lens_id(image):
    exiftoolOutput = subprocess.Popen(['exiftool', '-SerialNumber', image],
                                      stdout=subprocess.PIPE).communicate()[0]
    if exiftoolOutput:
        return exiftoolOutput.split(':', 1)[1].strip()
    else:
        return 'builtin'


def tally_images(filenames, model, localId,  lens, csvFile):
    if lens is None:
        lens = get_lens_id(filenames)
    if localId is None:
        localId = 'null'

    finalList = []
    for filename in filenames:
        with Image.open(filename) as im:
            width, height = im.size
            im.convert('L')
            imStat = ImageStat.Stat(im)
            avgLum = imStat.mean[0]

        if avgLum < 85:
            lum = 'low'
        elif avgLum >= 85 and avgLum <= 170:
            lum = 'medium'
        else:
            lum = 'high'

        ext = os.path.splitext(filename)[1]
        # headers = ['Model', 'Lens', 'Extension', 'Size (px)', 'Luminance', 'F#',
        #            'Exposure Time', 'ISO', 'Bit Depth', 'Count']
        imageChars = ['Model: ' + model, 'LocalID: '+ localId, 'Lens: ' + lens,  'Extension: ' + ext,
                        'Size: ' + str(width * height), 'Luminance: ' + lum]

        exifData = subprocess.Popen(['exiftool', '-FNumber', '-ExposureTime', '-ISO', '-BitsPerSample', '-Make', filename],
                                        stdout=subprocess.PIPE).communicate()[0]
        # parse exiftool output string intolist
        exifList = exifData[:-1].replace('\r', '').split('\n')
        keyList = []
        for item in exifList:
            data = item.split(':', 1)
            key = data[0].strip()
            val = data[1].strip()
            imageChars += [key + ': ' + val]
            keyList += [key]

        if exifList in finalList:
            incrIdx = finalList.index([exifList]) + 1
            finalList[incrIdx] = finalList[incrIdx] + 1
        else:
            finalList.append(imageChars)
            finalList.append(1)

    with open(csvFile, 'ab') as csv_tally:
        tallyWriter = csv.writer(csv_tally, lineterminator='\n')
        #tallyWriter.writerow(headers)
        i = 0
        while i < len(finalList):
            tallyWriter.writerow(finalList[i] + ['Count:' + str(finalList[i+1])])
            i += 2


def s3_prefs(values, upload=False):
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
    parser.add_argument('-B', '--s3Bucket',                                         help='S3 bucket/path')
    parser.add_argument('-i', '--id',               required=True,                  help='Camera serial #')
    parser.add_argument('-l', '--lid',              default='',                     help='Local ID no. (cage #, etc.)')
    parser.add_argument('-L', '--lens',             default='',                     help='Lens serial #')

    args = parser.parse_args()
    try:
        s3_prefs([args.s3Bucket])
    except botocore.exceptions.ClientError:
        try:
            s3_prefs([args.s3Bucket], upload=True)
        except botocore.exceptions.ClientError:
            sys.exit('Bucket/path not found!')

    prefs = parse_prefs('preferences.txt')

    # grab files
    imageList = []

    if args.files:
        imageList.extend(grab_individuals(args.files))
    elif args.range:
        fRange = args.range.split(' ')
        imageList.extend(grab_range(fRange))
    else:
        imageList.extend(grab_dir(args.dir, args.recursive))

    # check camera model before any processing
    if args.id:
        camera = args.id
    else:
        camera = get_id(imageList[0])

    # copy
    try:
        count = int(prefs['seq'])
    except KeyError:
        count = 0
        add_seq(args.preferences)

    csv_history = os.path.join(args.secondary, 'history.csv')
    csv_keywords = os.path.join(args.secondary, 'keywords.csv')
    csv_metadata = os.path.join(args.secondary, 'xdata.csv')
    try:
        extraValues = parse_extra(args.extraMetadata, csv_metadata)
    except TypeError:
        extraValues = None

    newNameList = []
    for image in imageList:
        newName = copyrename(image, args.secondary, prefs['username'], prefs['organization'], pad_to_5_str(count), args.additionalInfo)
        build_history_file(image, newName, csv_history)
        if args.keywords:
            build_keyword_file(image, args.keywords, csv_keywords)
        if args.extraMetadata:
            build_xmetadata_file(image, extraValues, csv_metadata)
        newNameList += [newName]
        count += 1

    write_seq(args.preferences, pad_to_5_str(count))
    s3_prefs([args.s3Bucket], upload=True)

    # change metadata of copies
    newData = change_all_metadata.parse_file(args.metadata)
    change_all_metadata.process(args.secondary, newData, quiet=True)


    # write final csv
    csv_tally = os.path.join(args.secondary, 'tally.csv')
    tally_images(newNameList, camera, args.lid, args.lens, csv_tally)


if __name__ == '__main__':
    main()