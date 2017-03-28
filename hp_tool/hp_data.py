"""
hp_data

tool for bulk renaming of files to standard
"""

import argparse
import shutil
import os
from PIL import Image
import change_all_metadata
import datetime
import sys
import csv
import hashlib
import pandas as pd
import itertools
import subprocess

exts = {'IMAGE':['.jpg', '.jpeg', '.png', '.tif', '.tiff', '.nef', '.crw', '.cr2', '.dng', '.arw', '.srf', '.raf'], 'VIDEO':['.avi', '.mov', '.mp4', '.mpg', '.mts', '.asf'],
        'AUDIO':['.wav', '.mp3', '.flac', '.webm', '.aac', '.amr', '.3ga']}
orgs = {'RIT':'R', 'Drexel':'D', 'U of M':'M', 'PAR':'P', 'CU Denver':'C'}

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
                try:
                    (tag, descr) = line.split('=')
                    newData[tag.lower().strip()] = descr.strip()
                except ValueError:
                    continue
    except IOError:
        print('Input file: ' + data + ' not found. ')
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

def convert_GPS(coordinate):
    """
    Converts lat/long output from exiftool (DMS) to decimal degrees
    :param coordinate: string of coordinate in the form 'X degrees Y' Z' N/S/W/E'
    :return: (string) input coordinate in decimal degrees, rounded to 6 decimal places
    """
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
        xmetadataWriter = csv.writer(csv_metadata, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
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
    newFile = not os.path.isfile(csvFile)
    with open(csvFile, 'a') as csv_rit:
        ritWriter = csv.writer(csv_rit, lineterminator='\n', quoting=csv.QUOTE_ALL)
        if newFile:
            ritWriter.writerow(['ImageFilename', 'HP-CollectionRequestID', 'HP-HDLocation', 'OriginalImageName', 'MD5',
                                    'CameraModel', 'DeviceSN', 'HP-DeviceLocalID', 'LensModel','LensSN', 'HP-LensLocalID', 'FileType', 'HP-JpgQuality',
                                    'ShutterSpeed', 'Aperture', 'ExpCompensation', 'ISO', 'NoiseReduction', 'WhiteBalance',
                                    'HP-DegreesKelvin', 'ExposureMode', 'FlashFired', 'FocusMode', 'CreationDate', 'HP-Location',
                                    'GPSLatitude', 'GPSLongitude', 'CustomRendered', 'HP-OnboardFilter', 'HP-OBFilterType', 'BitDepth', 'ImageWidth', 'ImageHeight',
                                    'HP-LensFilter', 'Type', 'HP-WeakReflection', 'HP-StrongReflection', 'HP-TransparentReflection', 'HP-ReflectedObject',
                                    'HP-Shadows', 'HP-HDR', 'HP-CameraKinematics', 'HP-App', 'HP-Inside', 'HP-Outside',
                                    'HP-ProximitytoSource', 'HP-MultiInput', 'HP-AudioChannels', 'HP-Echo', 'HP-BackgroundNoise', 'HP-Description', 'HP-Modifier',
                                    'HP-AngleofRecording', 'HP-MicLocation', 'HP-PrimarySecondary', 'HP-ZoomLevel', 'HP-Recapture', 'HP-RecaptureSubject',
                                    'HP-LightSource', 'HP-Orientation', 'HP-DynamicStatic'])
        if newNameList:
            for imNo in xrange(len(imageList)):
                md5 = hashlib.md5(open(newNameList[imNo], 'rb').read()).hexdigest()
                ritWriter.writerow([os.path.basename(newNameList[imNo]), info[imNo][0], os.path.dirname(imageList[imNo]), os.path.basename(imageList[imNo]), md5, info[imNo][30]] +
                                   info[imNo][2:4] + [info[imNo][31]] + info[imNo][4:30] + info[imNo][32:])
        else:
            for imNo in xrange(len(imageList)):
                md5 = hashlib.md5(open(imageList[imNo], 'rb').read()).hexdigest()
                ritWriter.writerow(['', info[imNo][0], info[imNo][1], os.path.basename(imageList[imNo]), md5] + info[imNo][2:])


def build_history_file(imageList, newNameList, data, csvFile):
    """
    Creates an easy-to-follow history for keeping record of image names
    oldImageFile --> newImageFile
    :param image: old image file
    :param newName: new image file
    :param data: image information list
    :param csvFile: csv file to store information
    :return: None
    """
    newFile = not os.path.isfile(csvFile)
    with open(csvFile, 'a') as csv_history:
        historyWriter = csv.writer(csv_history, lineterminator='\n', quoting=csv.QUOTE_ALL)
        if newFile:
            historyWriter.writerow(['Original Name', 'New Name', 'MD5', 'Type'])
        for imNo in range(len(imageList)):
            md5 = hashlib.md5(open(newNameList[imNo], 'rb').read()).hexdigest()
            historyWriter.writerow([os.path.basename(imageList[imNo]), os.path.basename(newNameList[imNo]), md5, data[imNo][29]])


def rankone_camera_update_csv(imageList, newNameList, data, csvFile):
    newFile = not os.path.isfile(csvFile)
    with open(csvFile, 'w') as csv_ro:
        wtr_quotes = csv.writer(csv_ro, lineterminator='\n', quoting=csv.QUOTE_ALL)
        wtr_noquotes = csv.writer(csv_ro, lineterminator='\n', quoting=csv.QUOTE_NONE)
        if newFile:
            wtr_noquotes.writerow(['#@version=01.05'])
            wtr_quotes.writerow(['MD5', 'CameraModel', 'DeviceSerialNumber', 'LensModel', 'LensSN', 'ImageFilename', 'HP-CollectionRequestID', 'HP-DeviceLocalID',
                               'HP-LensLocalID', 'NoiseReduction', 'HP-Location', 'HP-OnboardFilter', 'HP-OBFilterType', 'HP-LensFilter',
                               'HP-WeakReflection', 'HP-StrongReflection', 'HP-TransparentReflection', 'HP-ReflectedObject', 'HP-Shadows', 'HP-HDR', 'HP-CameraKinematics',
                               'HP-App', 'HP-Inside', 'HP-Outside', 'HP-ProximitytoSource', 'HP-MultiInput', 'HP-AudioChannels', 'HP-Echo', 'HP-BackgroundNoise', 'HP-Description', 'HP-Modifier',
                               'HP-AngleofRecording', 'HP-MicLocation', 'HP-PrimarySecondary', 'HP-ZoomLevel', 'HP-Recapture', 'HP-RecaptureSubject',
                               'HP-LightSource', 'HP-Orientation', 'HP-DynamicStatic', 'ImportDate'])
        for imNo in range(len(imageList)):
            md5 = hashlib.md5(open(newNameList[imNo], 'rb').read()).hexdigest()
            now = datetime.datetime.today().strftime('%m/%d/%Y %I:%M:%S %p')
            wtr_quotes.writerow([md5, data[imNo][30], data[imNo][2], data[imNo][31], data[imNo][4], os.path.basename(newNameList[imNo]), data[imNo][0],
                               data[imNo][3], data[imNo][5], data[imNo][12], data[imNo][19], data[imNo][23], data[imNo][24], data[imNo][28]] + data[imNo][32:] + [now])
                               # data[imNo][32], data[imNo][33], data[imNo][34], data[imNo][35], data[imNo][36], data[imNo][37], data[imNo][38],
                               # data[imNo][39], data[imNo][40] + data[imNo][41:], now])


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
        tallyWriter = csv.writer(csv_tally, lineterminator='\n', quoting=csv.QUOTE_MINIMAL)
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

def frac2dec(fracStr):
    return fracStr
    # try:
    #     return float(fracStr)
    # except ValueError:
    #     if '\\' in fracStr:
    #         (num, denom) = fracStr.split('\\')
    #     elif '/' in fracStr:
    #         (num, denom) = fracStr.split('/')
    #     else:
    #         print 'Could not convert fraction to decimal: ' + fracStr
    #         return fracStr
    #     return str(float(num)/float(denom))

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

def parse_image_info(imageList, path='', rec=False, collReq='', camera='', localcam='', lens='', locallens='', hd='',
                     sspeed='', fnum='', expcomp='', iso='', noisered='', whitebal='', expmode='', flash='',
                     focusmode='', kvalue='', location='', obfilter='', obfiltertype='', lensfilter='',
                     cameramodel='', lensmodel='', jq='', reflweak='', reflstrg='', refltrans='', reflobj='', shadows='', hdr='', app='', camerakinematics='',
                     inside='', outside='', proximity='', multiinput='', audiochannels='', echo='', bgnoise='',
                     description='', modifier='', recordangle='', miclocation='', primarysecondary='', zoomlvl='',
                     recapture='', recapturesubject='', lightsource='', orientation='', dynamicstatic=''):
    """
    Prepare list of values about the specified image.
    If an argument is entered as an empty string, will check image's exif data for it.
    :param imageList: list of images to examine
    :param path: base image directory
    ...
    :return: list containing only values of each argument. The value will be N/A if empty string
    is supplied and no exif data can be found.

    GUIDE of INDICES: (We'll make this a dictionary eventually)
    0: HP-CollectionRequestID
    1: HP-HDLocation
    2. DeviceSN
    3. HP-DeviceLocalID
    4. LensSN
    5. HP-LensLocalID
    6. FileType
    7. HP-JPGQuality
    8. ShutterSpeed
    9. Aperture
    10. ExpCompensation
    11. ISO
    12. NoiseReduction
    13. WhiteBalance
    14. HP-DegreesKelvin
    15. ExposureMode
    16. FlashFired
    17. FocusMode
    18. CreationDate
    19. HP-Location
    20. GPSLatitude
    21. GPSLongitude
    22. CustomRendered
    23. HP-OnboardFilter (T/F)
    24. HP-OBFilterType
    25. BitDepth
    26. ImageWidth
    27. ImageHeight
    28. HP-LensFilter
    29. Type (IMAGE or VIDEO)
    30. CameraModel
    31. LensModel
    32. HP-WeakReflection
    33. HP-StrongReflection
    34. HP-TransparentReflection
    35. HP-ReflectedObject
    36. HP-Shadows
    37. HP-HDR
    38. HP-CameraKinematics
    39. HP-App
    40. HP-Inside
    41. HP-Outside
    42. HP-ProximitytoSource
    43. HP-MultiInput
    44. HP-AudioChannels
    45. HP-Echo
    46. HP-BackgroundNoise
    47. HP-Description
    48. HP-Modifier
    49. HP-AngleofRecording
    50. HP-MicLocation
    51. HP-PrimarySecondary
    52. HP-ZoomLevel
    53. HP-Recapture
    54. HP-RecaptureSubject
    55. HP-LightSource
    56. HP-Orientation
    57. HP-DynamicStatic
    """
    exiftoolargs = []
    data = []
    if not hd:
        hd = path
    master = [collReq, hd, '', localcam, '', locallens, '', jq] + [''] * 6 + [kvalue] + [''] * 4 + [location, '', '', '', obfilter, obfiltertype] + \
             [''] * 3 + [lensfilter, '', '', '', reflweak, reflstrg, refltrans, reflobj, shadows, hdr, camerakinematics, app, inside, outside, proximity, multiinput, audiochannels, echo, bgnoise,
                     description, modifier, recordangle, miclocation, primarysecondary, zoomlvl, recapture, recapturesubject, lightsource, orientation, dynamicstatic]
    missingIdx = []

    if camera:
        master[2] = camera
    else:
        exiftoolargs.append('-SerialNumber')
        missingIdx.append(2)

    if lens:
        master[4] = lens
    else:
        exiftoolargs.append('-LensSerialNumber')
        missingIdx.append(4)

    if sspeed:
        master[8] = sspeed
    else:
        exiftoolargs.append('-ShutterSpeed')
        missingIdx.append(8)

    if fnum:
        master[9] = fnum
    else:
        exiftoolargs.append('-FNumber')
        missingIdx.append(9)

    if expcomp:
        master[10] = expcomp
    else:
        exiftoolargs.append('-ExposureCompensation')
        missingIdx.append(10)

    if iso:
        master[11] = iso
    else:
        exiftoolargs.append('-ISO')
        missingIdx.append(11)

    if noisered:
        master[12] = noisered
    else:
        exiftoolargs.append('-NoiseReduction')
        missingIdx.append(12)

    if whitebal:
        master[13] = whitebal
    else:
        exiftoolargs.append('-WhiteBalance')
        missingIdx.append(13)

    if expmode:
        master[15] = expmode
    else:
        exiftoolargs.append('-ExposureMode')
        missingIdx.append(15)

    if flash:
        master[16] = flash
    else:
        exiftoolargs.append('-Flash')
        missingIdx.append(16)

    if focusmode:
        master[17] = focusmode
    else:
        exiftoolargs.append('-Focusmode')
        missingIdx.append(17)

    if cameramodel:
        master[30] = cameramodel
    else:
        exiftoolargs.append('-Model')
        missingIdx.append(30)

    if lensmodel:
        master[31] = lensmodel
    else:
        exiftoolargs.append('-LensModel')
        missingIdx.append(31)


    exiftoolargs.extend(['-BitsPerSample','-GPSLatitude', '-GPSLongitude', '-CustomRendered', '-CreateDate','-ImageWidth','-ImageHeight'])
    missingIdx.extend([25, 20, 21, 22, 18, 26, 27])

    if len(exiftoolargs) > 0:
        counter = 0
        exifDataStr = ''
        exifData = []
        if path:
            if rec:
                exifDataStr += subprocess.Popen(['exiftool', '-f', '-r'] + exiftoolargs + [path], stdout=subprocess.PIPE).communicate()[0]
            else:
                exifDataStr += subprocess.Popen(['exiftool','-f'] + exiftoolargs + [path], stdout=subprocess.PIPE).communicate()[0]
            exifData = exifDataStr.split(os.linesep)[:-3]
        else:
            while counter < len(imageList):
                if len(imageList) - counter > 500:
                    exifDataStr += subprocess.Popen(['exiftool', '-f'] + exiftoolargs + imageList[counter:counter+500],
                                                stdout=subprocess.PIPE).communicate()[0]
                elif len(imageList) - counter <= 500:
                    exifDataStr += subprocess.Popen(['exiftool','-f'] + exiftoolargs + imageList[counter:],
                                                stdout=subprocess.PIPE).communicate()[0]
                exifDataList = exifDataStr.split(os.linesep)[:-2]
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
        if len(imageIndices) > 1:
            diff = imageIndices[1] - imageIndices[0] - 1
        else:
            diff = len(newExifData) +1
        j = 0
        for i in xrange(len(imageList)):
            data.append(master[:])
            ex = os.path.splitext(imageList[i])[1]
            data[i][6] = os.path.splitext(imageList[i])[1][1:]
            if ex.lower() in exts['AUDIO']:
                data[i][29] = 'audio'
            elif ex.lower() in exts['VIDEO']:
                data[i][29] = 'video'
            else:
                data[i][29] = 'image'
            newExifSubset = newExifData[j:j + diff]
            k = 0
            for dataIdx in missingIdx:
                if newExifSubset:
                    data[i][dataIdx] = newExifSubset[k]
                k += 1
            j += diff
            data[i][8] = frac2dec(data[i][8])
            if data[i][20] and data[i][21]:
                data[i][20] = convert_GPS(data[i][20])
                data[i][21] = convert_GPS(data[i][21])
            if 'hdr' in imageList[i].lower():
                data[i][37] = 'True'
            try:
                with Image.open(imageList[i]) as im:
                    width, height = im.size
                    if width < height:
                        data[i][56] = 'portrait'
                    else:
                        data[i][56] = 'landscape'
            except (IOError, AttributeError):
                pass

    return data

def process(preferences='', metadata='', files='', range='', imgdir='', outputdir='', recursive=False, xdata='',
            keywords='', additionalInfo='', tally=False, **kwargs):

    # parse preferences
    userInfo = parse_prefs(preferences)
    print 'Successfully pulled preferences'

    # collect image list
    print 'Collecting images...',
    imageList = []

    # set up the output subdirectories
    check_create_subdirectories(outputdir)

    if files:
        imageList.extend(grab_individuals(files))
    elif range:
        fRange = range.split(' ')
        imageList.extend(grab_range(fRange))
    else:
        imageList.extend(grab_dir(imgdir, os.path.join(outputdir, 'csv'), recursive))
    print ' done'

    if not imageList:
        print 'No new images found'
        remove_temp_subs(outputdir)
        return imageList, []

    # build information list. This is the bulk of the processing, and what runs exiftool
    print 'Building image info...',
    imageInfo = parse_image_info(imageList, path=imgdir, rec=recursive, **kwargs)
    print ' done'

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


    csv_metadata = os.path.join(outputdir, 'csv', datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' +
                                userInfo['organization'] + userInfo['username'] + '-' + 'xdata.csv')

    try:
        extraValues = parse_extra(xdata, csv_metadata)
    except TypeError:
        extraValues = None


    # copy with renaming
    print 'Copying files...',
    newNameList = []
    for image in imageList:
        newName = copyrename(image, outputdir, userInfo['username'], userInfo['organization'], pad_to_5_str(count), additionalInfo)
        if keywords:
            build_keyword_file(newName, keywords, csv_keywords)
        if extraValues:
            build_xmetadata_file(newName, extraValues, csv_metadata)
        newNameList += [newName]
        count += 1
    print ' done'

    update_prefs(preferences, inputdir=imgdir, outputdir=outputdir, newSeq=pad_to_5_str(count))
    print 'Prefs updated with new sequence number'

    print 'Updating metadata...'
    newData = change_all_metadata.parse_file(metadata)
    if imgdir:
        change_all_metadata.process(os.path.join(outputdir, 'image', '.hptemp'), newData, quiet=True)
        change_all_metadata.process(os.path.join(outputdir, 'video', '.hptemp'), newData, quiet=True)
        change_all_metadata.process(os.path.join(outputdir, 'audio', '.hptemp'), newData, quiet=True)
    else:
        change_all_metadata.process(newNameList, newData, quiet=True)

    print 'Building RIT file'
    csv_rit = os.path.join(outputdir, 'csv', os.path.basename(newNameList[0])[0:11] + 'rit.csv')
    build_rit_file(imageList, imageInfo, csv_rit, newNameList=newNameList)
    'Success'

    # history file:
    print 'Building history file'
    csv_history = os.path.join(outputdir, 'csv', os.path.basename(newNameList[0])[0:11] + 'history.csv')
    build_history_file(imageList, newNameList, imageInfo, csv_history)

    print 'Building RankOne file'
    csv_ro = os.path.join(outputdir, 'csv', os.path.basename(newNameList[0])[0:11] + 'rankone.csv')
    rankone_camera_update_csv(imageList, newNameList, imageInfo, csv_ro)

    if tally:
        # write final csv
        print 'Building tally file'
        csv_tally = os.path.join(outputdir, os.path.basename(newNameList[0])[0:11] + 'tally.csv')
        tally_images(imageInfo, csv_tally)
        print 'Successfully tallied image data'

    # move out of tempfolder
    print 'Cleaning up...'
    remove_temp_subs(outputdir)

    print '\nComplete!'

    return imageList, newNameList

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

    parser.add_argument('-T', '--tally',            action='store_true',            help='Produce tally output')
    parser.add_argument('-z', '--cameramodel',      default='',                     help='Camera model')
    parser.add_argument('-i', '--id',               default='',                     help='Camera serial #')
    parser.add_argument('-o', '--localid',          default='',                     help='Local ID no. (cage #, etc.)')
    parser.add_argument('-Z', '--lensmodel',        default='',                     help='Lens model')
    parser.add_argument('-L', '--lens',             default='',                     help='Lens serial #')
    parser.add_argument('-O', '--locallens',        default='',                     help='Lens local ID')
    parser.add_argument('-j', '--jpegquality',      default='',                     help='Approx. JPEG quality')
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
    parser.add_argument('-b', '--filter',           required=True,                  help='On-board filter (T/F)')
    parser.add_argument('-B', '--filtertype',       default='',                     help='What type of ob filter')
    parser.add_argument('-c', '--lensfilter',       default='',                     help='Lens filter type')
    parser.add_argument('-C', '--collection',       default='',                     help='Collection Request ID')
    parser.add_argument('--reflections',            action='store_true',            help='Include to specify reflections in these images')
    parser.add_argument('--shadows',                action='store_true',            help='Include to specify shadows in these images')

    args = parser.parse_args()

    # parse filter arg
    if args.filter.lower().startswith('t'):
        boolfilter = True
    elif args.filter.lower().startswith('f'):
        boolfilter = False
    else:
        'Error: Please specify whether or not an on-board filter was used with "true" or "false"'
        sys.exit(0)


    kwargs = {'collReq':args.collection, 'camera':args.id, 'localcam':args.localid, 'lens':args.lens, 'locallens':args.locallens,
              'hd':args.hd, 'sspeed':args.sspeed, 'fnum':args.fnum, 'expcomp':args.expcomp, 'iso':args.iso, 'noisered':args.noisered,
              'whitebal':args.whitebal, 'expmode':args.expmode, 'flash':args.flash, 'focusmode':args.focusmode, 'kvalue':args.kvalue,
              'location':args.location, 'obfilter':boolfilter, 'obfiltertype':args.filtertype, 'lensfilter':args.lensfilter, 'reflections':args.reflections,
              'shadows':args.shadows}
    process(preferences=args.preferences, metadata=args.metadata, files=args.files, range=args.range,
            imgdir=args.dir, outputdir=args.secondary, recursive=args.recursive, keywords=args.keywords, xdata=args.extraMetadata, **kwargs)

if __name__ == '__main__':
    main()
