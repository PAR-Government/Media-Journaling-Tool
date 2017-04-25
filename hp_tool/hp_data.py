"""
hp_data

tool for bulk renaming of files to standard
"""

import shutil
import os
import sys
from PIL import Image
import change_all_metadata
import datetime
import csv
import hashlib
import pandas as pd
import subprocess
import json

exts = {'IMAGE':['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.nef', '.crw', '.cr2', '.dng', '.arw', '.srf', '.raf'], 'VIDEO':['.avi', '.mov', '.mp4', '.mpg', '.mts', '.asf'],
        'AUDIO':['.wav', '.mp3', '.flac', '.webm', '.aac', '.amr', '.3ga']}
orgs = {'RIT':'R', 'Drexel':'D', 'U of M':'M', 'PAR':'P', 'CU Denver':'C'}
FIELDSPATH = os.path.join('data', 'fieldnames.json')
HEADERSPATH = os.path.join('data', 'headers.json')
RVERSION = '#@version=01.08'

def copyrename(image, path, usrname, org, seq, other):
    """
    Performs the copy/rename operation
    :param image: original filename (full path)
    :param path: destination path. This must have 3 subdirectories: images, video, and csv
    :param usrname: username for new filename
    :param org: organization code for new filename
    :param seq: sequence # for new filename
    :param other: other info for new filename
    :return: full path of new file
    """
    global exts
    newNameStr = datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                    org + usrname + '-' + seq
    if other:
        newNameStr = newNameStr + '-' + other

    currentExt = os.path.splitext(image)[1]
    if currentExt.lower() in exts['VIDEO']:
        sub = 'video'
    elif currentExt.lower() in exts['AUDIO']:
        sub = 'audio'
    else:
        sub = 'image'
    newPathName = os.path.join(path, sub, '.hptemp', newNameStr + currentExt)
    shutil.copy2(image, newPathName)
    return newPathName


def parse_prefs(self, data):
    """
    Parse preferences file
    :param self: reference to HP GUI
    :param data: string containing path to preferences file
    :return: dictionary containing preference option and setting (e.g. {username:AS...})
    """
    newData = {}
    # open text file
    try:
        with open(data) as f:
            for line in f:
                try:
                    (tag, descr) = line.split('=')
                    newData[tag.lower().strip()] = descr.strip()
                except ValueError:
                    continue
    except IOError:
        print 'Input file: ' + data + ' not found. '
        return

    try:
        (newData['organization'] and newData['username'])
    except KeyError:
        print 'Must specify ''username'' and ''organization'' in preferences file'
        return

    # convert to single-char organization code
    if len(newData['organization']) > 1:
        try:
            newData['organization'] = orgs[newData['organization']]
        except KeyError:
            if newData['organization'][-2] in orgs.values():
                newData['fullorgname'] = newData['organization']
                newData['organization'] = newData['organization'][-2]
            else:
                print 'Error: organization: ' + newData['organization'] + ' not recognized'
                return
    elif len(newData['organization']) == 1:
        if newData['organization'] not in orgs.values():
            print 'Error: organization code: ' + newData['organization'] + ' not recognized'
            return

    # reset sequence if date is new
    try:
        if newData['date'] != datetime.datetime.now().strftime('%Y%m%d')[2:]:
            newData['seq'] = '00000'
    except KeyError:
        newData['date'] = datetime.datetime.now().strftime('%Y%m%d')[2:]
        add_date(data)

    if 'imagetypes' in newData:
        add_types(newData['imagetypes'], 'image')
    if 'videotypes' in newData:
        add_types(newData['videotypes'], 'video')
    if 'audiotypes' in newData:
        add_types(newData['audiotypes'], 'audio')

    return newData

def add_types(data, mformat):
    global exts
    mformat = mformat.upper()
    data = data.replace(',', ' ').split(' ')
    for i in data:
        if i not in exts[mformat] and len(i) > 0:
            exts[mformat].append(i)

# def convert_GPS(coordinate):
#     """
#     Converts lat/long output from exiftool (DMS) to decimal degrees
#     :param coordinate: string of coordinate in the form 'X degrees Y' Z' N/S/W/E'
#     :return: (string) input coordinate in decimal degrees, rounded to 6 decimal places
#     """
#     if coordinate:
#         coord = coordinate.split(' ')
#         whole = float(coord[0])
#         direction = coord[-1]
#         min = float(coord[2][:-1])
#         sec = float(coord[3][:-1])
#         dec = min + (sec/60)
#         coordinate = round(whole + dec/60, 6)
#
#         if direction == 'S' or direction == 'W':
#             coordinate *= -1
#
#     return str(coordinate)

def pad_to_5_str(num):
    """
    Converts an int to a string, and pads to 5 chars (1 -> '00001')
    :param num: int to be padded
    :return: padded string
    """

    return '{:=05d}'.format(num)

def grab_dir(inpath, outdir=None, r=False):
    """
    Grabs all image files in a directory
    :param inpath: path to directory of desired files
    :param outdir: path to output csv directory, to check for existing images
    :param r: Recursively grab images from all subdirectories as well
    :return: list of images in directory
    """
    imageList = []
    names = os.listdir(inpath)
    valid_exts = tuple(exts['IMAGE'] + exts['VIDEO'] + exts['AUDIO'])
    if r:
        for dirname, dirnames, filenames in os.walk(inpath, topdown=True):
            for filename in filenames:
                if filename.lower().endswith(valid_exts) and not filename.startswith('.'):
                    imageList.append(os.path.join(dirname, filename))
    else:
        for f in names:
            if f.lower().endswith(valid_exts) and not f.startswith('.'):
                imageList.append(os.path.join(inpath, f))

    imageList = sorted(imageList, key=str.lower)

    if outdir:
        repeated = []
        ritCSV = None
        for f in os.listdir(outdir):
            if f.endswith('.csv') and 'rit' in f:
                ritCSV = os.path.join(outdir, f)
                rit = pd.read_csv(ritCSV, dtype=str)
                repeated = rit['OriginalImageName'].tolist()
        removeList = []
        for name in imageList:
            for repeatedName in repeated:
                if repeatedName:
                    if repeatedName in name:
                        removeList.append(name)
                        # imageList.remove(name)
                        # repeated.remove(repeatedName)
                        break

        for imageName in removeList:
            imageList.remove(imageName)
    return imageList


def update_prefs(prefs, inputdir, outputdir, newSeq):
    """
    Updates the sequence value in a file
    :param prefs: the file to be updated
    :param newSeq: string containing the new 5-digit sequence value (e.g. '00001'
    :return: None
    """
    originalFileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'preferences.txt')
    tmpFileName = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'tmp.txt')
    with open(tmpFileName, 'wb') as new:
        with open(originalFileName, 'rb') as original:
            for line in original:
                if line.startswith('seq='):
                    new.write('seq=' + newSeq + '\n')
                elif line.startswith('date='):
                    new.write('date=' + datetime.datetime.now().strftime('%Y%m%d')[2:] + '\n')
                else:
                    new.write(line)
                    if not line.endswith('\n'):
                        new.write('\n')
    os.remove(originalFileName)
    shutil.move(tmpFileName, originalFileName)

def add_seq(filename):
    """
    Appends a sequence field and an initial sequence to a file
    (Specifically, adds '\nseq=00000'
    :param filename: file to be edited
    :return: None
    """
    with open(filename, 'ab') as f:
        f.write('\nseq=00000\n')

def add_date(filename):
    with open(filename, 'ab') as f:
        f.write('\ndate=' + datetime.datetime.now().strftime('%Y%m%d')[2:] + '\n')


def build_keyword_file(image, keywords, csvFile):
    """
    Adds keywords to specified file
    :param image: image filename that keywords apply to
    :param keywords: list of keywords
    :param csvFile: csv file to store information
    :return: None
    """
    with open(csvFile, 'a') as csv_keywords:
        keywordWriter = csv.writer(csv_keywords, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
        if keywords:
            for word in keywords:
                keywordWriter.writerow([image, word])
        else:
            keywordWriter.writerow([image])

def build_csv_file(self, oldNameList, newNameList, info, csvFile, type):
    """
    Write out desired csv file, using headers from data/headers.json
    :param self: reference to HP GUI
    :param imageList: original image names
    :param newNameList: new image names, in same order as imageList
    :param info: ordered list of dictionaries of image info. should be in same order as image lists
    :param csvFile: csv file name
    :param type: name of list of headers to take, labeled in headers.json (rit, rankone, history)
    :return:
    """
    newFile = not os.path.isfile(csvFile)
    headers = load_json_dictionary(HEADERSPATH)
    with open(csvFile, 'a') as c:
        wtr = csv.writer(c, lineterminator='\n', quoting=csv.QUOTE_ALL)
        if newFile:
            if type == 'rankone':
                wtr.writerow([RVERSION])
            wtr.writerow(headers[type])
        for imNo in xrange(len(oldNameList)):
            row = []
            for h in headers[type]:
                if h == 'MD5':
                    md5 = hashlib.md5(open(newNameList[imNo], 'rb').read()).hexdigest()
                    row.append(md5)
                elif h == 'ImportDate':
                    row.append(datetime.datetime.today().strftime('%m/%d/%Y %I:%M:%S %p'))
                elif h == 'DeviceSN':
                    row.append(info[imNo]['DeviceSerialNumber'])
                elif h == 'OriginalImageName' or h == 'Original Name':
                    row.append(os.path.basename(oldNameList[imNo]))
                elif h == 'ImageFilename' or h == 'New Name':
                    row.append(os.path.basename(newNameList[imNo]))
                elif h == 'HP-HDLocation' and not info[imNo]['HP-HDLocation']:
                    row.append(os.path.dirname(oldNameList[imNo]))
                else:
                    try:
                        row.append(info[imNo][h])
                    except KeyError:
                        self.master.statusBox.println('Could not find column ' + h)
                        row.append('ERROR')
            wtr.writerow(row)


def check_create_subdirectories(path):
    subs = ['image', 'video', 'audio', 'csv']
    for sub in subs:
        if not os.path.exists(os.path.join(path, sub, '.hptemp')):
            os.makedirs(os.path.join(path, sub, '.hptemp'))
        for f in os.listdir(os.path.join(path, sub,'.hptemp')):
            oldFile = os.path.join(path, sub, '.hptemp', f)
            if os.path.isfile(oldFile):
                os.remove(oldFile)


def remove_temp_subs(path):
    subs = ['image', 'video', 'audio', 'csv']
    for sub in subs:
        for f in os.listdir(os.path.join(path,sub,'.hptemp')):
            shutil.move(os.path.join(path,sub,'.hptemp',f), os.path.join(path,sub))
        os.rmdir(os.path.join(path,sub,'.hptemp'))
        if not os.listdir(os.path.join(path,sub)):
            os.rmdir(os.path.join(path,sub))

def load_json_dictionary(path):
    with open(path) as j:
        data = json.load(j)
    return data

def remove_dash(item):
    """
    Remove the first character in a string.
    :param item: String
    :return: input string, with first character removed
    """
    return item[1:]

def combine_exif(exif_data, lut, d):
    """
    Add extracted exif information to master list of HP data
    :param exif_data: dictionary of data extracted from an image
    :param lut: LUT to translate exiftool output to fields
    :param fields: master dictionary of HP data
    :return: fields - a dictionary with updated exif information
    """
    for k in lut:
        if k in exif_data and exif_data[k] != '-':
            d[lut[k]] = exif_data[k]
    return d

def set_other_data(data, imfile):
    """
    Set implicit metadata to data.
    :param data: Dictionary of field data from one image
    :param imfile: name of corresponding image file
    :return: data with more information completed
    """
    imext = os.path.splitext(imfile)[1]
    data['FileType'] = imext[1:]
    if imext.lower() in exts['AUDIO']:
        data['Type'] = 'audio'
    elif imext.lower() in exts['VIDEO']:
        data['Type'] = 'video'
    else:
        data['Type'] = 'image'
    # data['GPSLatitude'] = convert_GPS(data['GPSLatitude'])
    # data['GPSLongitude'] = convert_GPS(data['GPSLongitude'])

    try:
        if int(data['ImageWidth']) < int(data['ImageHeight']):
            data['HP-Orientation'] = 'portrait'
        else:
            data['HP-Orientation'] = 'landscape'
    except ValueError:
        # no/invalid image width or height in metadata
        pass

    if 'back' in data['LensModel']:
        data['HP-PrimarySecondary'] = 'primary'
    elif 'front' in data['LensModel']:
        data['HP-PrimarySecondary'] = 'secondary'

    return data

def parse_image_info(self, imageList, **kwargs):
    """
    Extract image information from imageList
    :param self: reference to HP GUI
    :param imageList: list of image filepaths
    :param kwargs: additional settings or metadata, including: rec (recursion T/F, path (input directory
    :return:
    """
    fields = load_json_dictionary(FIELDSPATH)
    master = {}

    exiftoolargs = []
    for fkey in fields:
        master[fkey] = ''
        if fields[fkey].startswith('-'):
            exiftoolargs.append(fields[fkey])

    for kkey in kwargs:
        if kkey in fields:
            master[kkey] = kwargs[kkey]

    exiftoolparams = ['exiftool', '-f', '-j', '-r', '-software'] if kwargs['rec'] else ['exiftool', '-f', '-j', '-software']
    exifDataResult = subprocess.Popen(exiftoolparams + exiftoolargs + [kwargs['path']], stdout=subprocess.PIPE).communicate()[0]

    # exifDataResult is in the form of a String json ("[{SourceFile:im1.jpg, imageBitsPerSample:blah}, {SourceFile:im2.jpg,...}]")
    try:
        exifDataResult = json.loads(exifDataResult)
    except:
        self.master.statusBox.println('Exiftool could not return data for all input. Process cancelled.')
        return None

    # further organize exif data into a dictionary based on source filename
    exifDict = {}
    for item in exifDataResult:
        exifDict[os.path.normpath(item['SourceFile'])] = item

    data = {}
    reverseLUT = dict((remove_dash(v),k) for k,v in fields.iteritems() if v)
    for i in xrange(0, len(imageList)):
        data[i] = combine_exif(exifDict[os.path.normpath(imageList[i])], reverseLUT, master.copy())
        data[i] = set_other_data(data[i], imageList[i])

    return data

def check_for_errors(data, cameraData, images, path):
    """
    Check processed data with database information
    :param data: processed HP data
    :param cameraData: ground truth database information
    :param images: list of image names
    :return: list of errors
    """
    errors = {}
    for image in data:
        dbData = cameraData[data[image]['HP-DeviceLocalID']]
        errors[os.path.basename(images[image])] = e = []
        # replace None with empty string
        for item in dbData:
            if dbData[item] is None or dbData[item] == 'nan':
                dbData[item] = ''
        if (data[image]['CameraModel'] != dbData['exif_camera_model']):
            e.append(('CameraModel','Camera model found in exif for image ' + images[image] + ' (' + data[image]['CameraModel'] + ') does not match database.'))
        if (data[image]['CameraMake'] != dbData['exif_camera_make']):
            e.append(('CameraMake','Camera make found in exif for image ' + images[image] + ' (' + data[image]['CameraMake'] + ') does not match database.'))
        if (data[image]['DeviceSerialNumber'] != dbData['exif_device_serial_number']) and (data[image]['DeviceSerialNumber'] != ''):
            e.append(('DeviceSN','Camera serial number found in exif for image ' + images[image] + ' (' + data[image]['DeviceSerialNumber'] + ') does not match database.'))

    fullpath = os.path.join(path, 'errors.json')
    with open(fullpath, 'w') as j:
        json.dump(errors, j)
    return fullpath

def process(self, cameraData, preferences='', metadata='', imgdir='', outputdir='', recursive=False,
            keywords='', additionalInfo='', **kwargs):
    """
    The main process workflow for the hp tool.
    :param self: reference to HP GUI
    :param preferences: preferences filename
    :param metadata: metadata-to-be-set filename
    :param imgdir: directory of raw images/video/audio files to be processed
    :param outputdir: output directory (csv, image, video, and audio files will be made here)
    :param recursive: boolean, whether or not to search subdirectories as well
    :param keywords:
    :param additionalInfo: additional bit to be added onto filenames
    :param kwargs: hp data to be set
    :return: list of paths of original images and new images
    """
    # parse preferences
    userInfo = parse_prefs(self, preferences)
    self.master.statusBox.println('Successfully pulled preferences')

    # collect image list
    self.master.statusBox.println('Collecting images...')
    imageList = []

    # set up the output subdirectories
    check_create_subdirectories(outputdir)

    imageList.extend(grab_dir(imgdir, os.path.join(outputdir, 'csv'), recursive))
    self.master.statusBox.println('done')

    if not imageList:
        self.master.statusBox.println('No new images found')
        remove_temp_subs(outputdir)
        return imageList, [], None

    # build information list. This is the bulk of the processing, and what runs exiftool
    self.master.statusBox.println('Building image info...')
    imageInfo = parse_image_info(self, imageList, path=imgdir, rec=recursive, **kwargs)
    if imageInfo is None:
        return None, None, None
    else:
        errors = check_for_errors(imageInfo, cameraData, imageList, os.path.join(outputdir, 'csv'))
    self.master.statusBox.println(' done')

    # once we're sure we have info to work with, we can check for the image, video, and csv subdirectories
    check_create_subdirectories(outputdir)

    # prepare for the copy operation
    try:
        count = int(userInfo['seq'])
    except KeyError:
        count = 0
        add_seq(preferences)

    csv_keywords = os.path.join(outputdir, 'csv', datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' +
                                userInfo['organization'] + userInfo['username'] + '-' + 'keywords.csv')

    # copy with renaming
    self.master.statusBox.println('Copying files...')
    newNameList = []
    for image in imageList:
        newName = copyrename(image, outputdir, userInfo['username'], userInfo['organization'], pad_to_5_str(count), additionalInfo)
        if keywords:
            build_keyword_file(newName, keywords, csv_keywords)
        newNameList += [newName]
        count += 1
    self.master.statusBox.println(' done')

    update_prefs(preferences, inputdir=imgdir, outputdir=outputdir, newSeq=pad_to_5_str(count))
    self.master.statusBox.println('Prefs updated with new sequence number')

    self.master.statusBox.println('Updating metadata...')
    newData = change_all_metadata.parse_file(metadata)
    if imgdir:
        change_all_metadata.process(os.path.join(outputdir, 'image', '.hptemp'), newData, quiet=True)
        change_all_metadata.process(os.path.join(outputdir, 'video', '.hptemp'), newData, quiet=True)
        change_all_metadata.process(os.path.join(outputdir, 'audio', '.hptemp'), newData, quiet=True)
    else:
        change_all_metadata.process(newNameList, newData, quiet=True)

    self.master.statusBox.println('Building RIT file')
    csv_rit = os.path.join(outputdir, 'csv', os.path.basename(newNameList[0])[0:-9] + 'rit.csv')
    build_csv_file(self, imageList, newNameList, imageInfo, csv_rit, 'rit')

    # history file:
    self.master.statusBox.println('Building history file')
    csv_history = os.path.join(outputdir, 'csv', os.path.basename(newNameList[0])[0:-9] + 'history.csv')
    build_csv_file(self, imageList, newNameList, imageInfo, csv_history, 'history')

    self.master.statusBox.println('Building RankOne file')
    csv_ro = os.path.join(outputdir, 'csv', os.path.basename(newNameList[0])[0:-9] + 'rankone.csv')
    build_csv_file(self, imageList, newNameList, imageInfo, csv_ro, 'rankone')

    # move out of tempfolder
    self.master.statusBox.println('Cleaning up...')
    remove_temp_subs(outputdir)

    self.master.statusBox.println('\nComplete!')

    return imageList, newNameList, errors
