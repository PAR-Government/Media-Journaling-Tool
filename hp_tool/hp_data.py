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
    seq = str(num)
    diff = '0' * (5 - len(seq))
    return diff + seq


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

    with open(csvFile, 'a') as csv_history:
        historyWriter = csv.writer(csv_history, lineterminator='\n')
        historyWriter.writerow([image, ' --> ', newName])

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
    with open(csvFile, 'w') as csv_metadata:
        xmetadataWriter = csv.writer(csv_metadata, lineterminator='\n')
        xmetadataWriter.writerow(keys)
    return values

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
    args = parser.parse_args()

    newData = change_all_metadata.parse_file(args.metadata)
    if args.s3Bucket:
        values = args.s3Bucket
        s3 = boto3.client('s3', 'us-east-1')
        BUCKET = values[0][0:values[0].find('/')]
        DIR = values[0][values[0].find('/') + 1:]
        s3.download_file(BUCKET, DIR + '/preferences.txt', 'preferences.txt')
        prefs = parse_prefs('preferences.txt')
    else:
        prefs = parse_prefs(args.preferences)

    # grab files
    imageList = []

    if args.files:
        imageList.extend(grab_individuals(args.files))
    elif args.range:
        fRange = args.range.split(' ')
        imageList.extend(grab_range(fRange))
    else:
        imageList.extend(grab_dir(args.dir, args.recursive))

    # copy
    try:
        count = int(prefs['seq'])
    except KeyError:
        count = 0
        add_seq(args.preferences)

    csv_history = os.path.join(args.secondary, 'history.csv')
    csv_keywords = os.path.join(args.secondary, 'keywords.csv')
    csv_metadata = os.path.join(args.secondary, 'xdata.csv')
    extraValues = parse_extra(args.extraMetadata, csv_metadata)
    for image in imageList:
        newName = copyrename(image, args.secondary, prefs['username'], prefs['organization'], pad_to_5_str(count), args.additionalInfo)
        build_history_file(image, newName, csv_history)
        if args.keywords:
            build_keyword_file(image, args.keywords, csv_keywords)
        if args.extraMetadata:
            build_xmetadata_file(image, extraValues, csv_metadata)
        count += 1

    write_seq(args.preferences, pad_to_5_str(count))

    # change metadata of copies
    change_all_metadata.process(args.secondary, newData, quiet=True)


if __name__ == '__main__':
    main()