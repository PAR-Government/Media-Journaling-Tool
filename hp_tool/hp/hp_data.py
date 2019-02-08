"""
hp_data

Various helper functions that perform the backend processing for the HP Tool
"""

import shutil
import os
import datetime
import csv
import hashlib
import tkFileDialog
import tkMessageBox
import maskgen.tool_set
import pandas as pd
import numpy as np
import subprocess
import json
import data_files
from PIL import Image
from hp.GAN_tools import SeedProcessor
from zipfile import ZipFile

exts = {'IMAGE': [x[1][1:] for x in maskgen.tool_set.imagefiletypes],
        'VIDEO': [x[1][1:] for x in maskgen.tool_set.videofiletypes] + [".zip"],
        'AUDIO': [x[1][1:] for x in maskgen.tool_set.audiofiletypes],
        'MODEL': ['.3d.zip'],
        'nonstandard': ['.lfr']}

model_types = [x[1][1:] for x in maskgen.tool_set.modelfiletypes]

orgs = {'RIT': 'R', 'Drexel': 'D', 'U of M': 'M', 'PAR': 'P', 'CU Denver': 'C'}

RVERSION = '#@version=01.14'
thumbnail_conversion = {}


def copyrename(image, path, usrname, org, seq, other, containsmodels):
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
    global thumbnails
    newNameStr = datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                 org + usrname + '-' + seq
    if other:
        newNameStr = newNameStr + '-' + other

    currentExt = os.path.splitext(image)[1]
    files_in_dir = os.listdir(os.path.dirname(image)) if containsmodels else []

    if any(filename.lower().endswith('.3d.zip') for filename in files_in_dir):
        sub = 'model'
    elif any(os.path.splitext(filename)[1].lower() in exts["nonstandard"] for filename in files_in_dir):
        sub = 'nonstandard'
    elif currentExt.lower() in exts['VIDEO']:
        sub = 'video'
    elif currentExt.lower() in exts['AUDIO']:
        sub = 'audio'
    elif currentExt.lower() in exts['IMAGE']:
        sub = 'image'
    else:
        return image
    if sub not in ['model', 'nonstandard']:
        if currentExt == ".zip":
            full_ext = os.path.splitext(os.path.splitext(image)[0])[1] + ".zip"
            newPathName = os.path.join(path, sub, '.hptemp', newNameStr + full_ext)
        else:
            newPathName = os.path.join(path, sub, '.hptemp', newNameStr + currentExt)
    else:
        sub = 'image' if sub == 'nonstandard' else 'model'
        thumbnail_folder = os.path.join(path, sub, '.hptemp', newNameStr) if sub == 'model' else os.path.join(path,
                                                                                                              'thumbnails',
                                                                                                              '.hptemp')
        if not os.path.isdir(thumbnail_folder):
            os.mkdir(thumbnail_folder)

        file_dir = os.path.normpath(os.path.dirname(image))
        thumbnail_conversion[file_dir] = {}
        thumbnail_counter = 0
        for i in os.listdir(file_dir):
            currentExt = os.path.splitext(i)[1].lower()
            if i.lower().endswith(".3d.zip"):
                newPathName = os.path.join(path, sub, '.hptemp', newNameStr, newNameStr + ".3d.zip")
            elif currentExt in exts["nonstandard"]:
                newPathName = os.path.join(path, sub, '.hptemp', newNameStr + currentExt)
            elif currentExt in exts['IMAGE']:
                newThumbnailName = "{0}_{1}{2}".format(newNameStr, str(thumbnail_counter), currentExt)
                dest = os.path.join(thumbnail_folder, newThumbnailName)
                with Image.open(os.path.join(file_dir, i)) as im:
                    if im.width > 264:
                        im.thumbnail((264, 192), Image.ANTIALIAS)
                        im.save(dest)
                    else:
                        shutil.copy2(os.path.join(file_dir, i), dest)
                thumbnail_conversion[file_dir][i] = newThumbnailName
                thumbnail_counter += 1
            else:
                tkMessageBox.showwarning("File Copy Error", i + " will not be copied to the output directory as it is"
                                                                " an unrecognized file format")

    shutil.copy2(image, newPathName)
    return newPathName


def check_settings(self):
    """
    Check settings for new seq and additional filetypes
    :param self: reference to HP GUI
    """
    # reset sequence if date is new
    if self.settings.get_key('date') != datetime.datetime.now().strftime('%Y%m%d')[2:]:
        self.settings.save('seq', '00000')
    else:
        self.settings.save('date', datetime.datetime.now().strftime('%Y%m%d')[2:])

    add_types(self.settings.get_key('imagetypes'), 'image')
    add_types(self.settings.get_key('videotypes'), 'video')
    add_types(self.settings.get_key('audiotypes'), 'audio')


def add_types(data, mformat):
    global exts
    mformat = mformat.upper()
    # type == str when settings have been opened, None otherwise
    if type(data) == str:
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
    valid_exts = tuple(exts['IMAGE'] + exts['VIDEO'] + exts['AUDIO'] + ['.dng.zip'])
    if r:
        for dirname, dirnames, filenames in os.walk(inpath, topdown=True):
            for filename in filenames:
                if filename.lower().endswith(valid_exts) and not filename.startswith('.'):
                    imageList.append(os.path.join(dirname, filename))
    else:
        for f in names:
            if f.lower().endswith(valid_exts) and not f.startswith('.'):
                imageList.append(os.path.join(inpath, f))
            elif os.path.isdir(os.path.join(inpath, f)):
                for obj in os.listdir(os.path.join(inpath, f)):
                    if obj.lower().endswith('.3d.zip') or os.path.splitext(obj)[1].lower() in exts["nonstandard"]:
                        imageList.append(os.path.normpath(os.path.join(inpath, f, obj)))

    imageList = sorted(imageList, key=str.lower)

    if outdir:
        repeated = []
        ritCSV = None
        if os.path.exists(outdir):
            for f in os.listdir(outdir):
                if f.endswith('.csv') and 'rit' in f:
                    ritCSV = os.path.join(outdir, f)
                    rit = pd.read_csv(ritCSV, dtype=str)
                    repeated = rit['OriginalImageName'].tolist()
                    break
        removeList = []
        for name in imageList:
            for repeatedName in repeated:
                if repeatedName:
                    if os.path.basename(repeatedName) == os.path.basename(name):
                        removeList.append(name)
                        break

        for imageName in removeList:
            imageList.remove(imageName)
    return imageList


def find_rit_file(outdir):
    """
    Find a file ending in a dir, ending with 'rit.csv'
    :param outdir: string directory name
    :return: string w/ rit filename, None if not found
    """
    rit_file = None
    if not os.path.exists(outdir):
        return None
    for f in os.listdir(outdir):
        if f.endswith('rit.csv'):
            rit_file = os.path.join(outdir, f)
    return rit_file


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
    headers = load_json_dictionary(data_files._HEADERS)
    with open(csvFile, 'a') as c:
        wtr = csv.writer(c, lineterminator='\n', quoting=csv.QUOTE_ALL)
        if newFile:
            if type == 'rankone':
                wtr.writerow([RVERSION])
            wtr.writerow(headers[type])
        for imNo in xrange(len(oldNameList)):
            row = []
            if type == 'keywords':
                row.extend([os.path.basename(newNameList[imNo]), '', '', ''])
                wtr.writerow(row)
                continue
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
                        print('Could not find column ' + h)
                        row.append('ERROR')
            wtr.writerow(row)


def check_create_subdirectories(path):
    """
    Check if temporary image, video, audio, and csv subdirectories exist in a path, and creates them if not.
    :param path: directory path
    :return: None
    """
    subs = ['image', 'video', 'audio', 'model', 'thumbnails', 'csv']
    for sub in subs:
        if not os.path.exists(os.path.join(path, sub, '.hptemp')):
            os.makedirs(os.path.join(path, sub, '.hptemp'))
        for f in os.listdir(os.path.join(path, sub, '.hptemp')):
            oldFile = os.path.join(path, sub, '.hptemp', f)
            if os.path.isfile(oldFile):
                os.remove(oldFile)


def remove_temp_subs(path):
    """
    Move files out of temporary subdirectories and into output folder.
    :param path: Path containing temp subdirectories
    :return:
    """
    subs = ['image', 'video', 'audio', 'model', 'thumbnails', 'csv']
    for sub in subs:
        for f in os.listdir(os.path.join(path, sub, '.hptemp')):
            shutil.move(os.path.join(path, sub, '.hptemp', f), os.path.join(path, sub))
        os.rmdir(os.path.join(path, sub, '.hptemp'))
        if not os.listdir(os.path.join(path, sub)):
            os.rmdir(os.path.join(path, sub))


def load_json_dictionary(path):
    """
    Load a json file into a dictionary
    :param path: path to json file
    :return: Dictionary containing json-format data
    """
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


def set_other_data(self, data, imfile, set_primary):
    """
    Set implicit metadata to data.
    :param data: Dictionary of field data from one image
    :param imfile: name of corresponding image file
    :return: data with more information completed
    """
    def get_model_ext(model):
        zf = ZipFile(model)
        exts_in_zip = [os.path.splitext(x)[1] for x in zf.namelist()]
        matching_types = [x for x in exts_in_zip if x in model_types]
        if matching_types:
            return matching_types[0]
        return "3d.zip"

    imext = os.path.splitext(imfile)[1]
    if imext.lower() in exts['AUDIO']:
        data['Type'] = 'audio'
    elif imfile.lower().endswith('.3d.zip'):
        data['Type'] = 'model'
    elif imext.lower() in exts['VIDEO']:
        data['Type'] = 'video'
    else:
        data['Type'] = 'image'

    data['FileType'] = imext[1:] if imext[1:] != "zip" else os.path.splitext(os.path.splitext(imfile)[0])[1][1:] +\
                                                            imext if data['Type'] != "model" else get_model_ext(imfile)
    # data['GPSLatitude'] = convert_GPS(data['GPSLatitude'])
    # data['GPSLongitude'] = convert_GPS(data['GPSLongitude'])

    data['HP-Username'] = self.settings.get_key('username')

    try:
        if int(data['ImageWidth']) < int(data['ImageHeight']):
            data['HP-Orientation'] = 'portrait'
        else:
            data['HP-Orientation'] = 'landscape'
    except ValueError:
        # no/invalid image width or height in metadata
        pass

    if set_primary and set_primary != "model":
        data['HP-PrimarySecondary'] = 'primary'

    if 'back' in data['LensModel']:
        data['HP-PrimarySecondary'] = 'primary'
    elif 'front' in data['LensModel']:
        data['HP-PrimarySecondary'] = 'secondary'

    return data


def check_outdated(ritCSV, path):
    """
    If an old CSV directory is loaded, check for any updates.
    Future update functions should be called from here for backwards compatibility. (For new column headings, etc)
    :param ritCSV: path to RIT csv
    :param path: path to data
    :return:
    """
    current_headers = load_json_dictionary(data_files._FIELDNAMES)
    rit_data = pd.read_csv(ritCSV, dtype=str)
    rit_headers = list(rit_data)
    diff = [x for x in current_headers.keys() if x not in rit_headers]  # list all new items

    for new_item in diff:
        if new_item == 'HP-Collection':
            rit_data.rename(columns={'HP-CollectionRequestID': 'HP-Collection'}, inplace=True)
            print('Updating: Changed HP-CollectionRequestID to HP-Collection.')
        elif new_item == 'CameraMake':
            add_exif_column(rit_data, 'CameraMake', '-Make', path)

    if diff:
        rit_data.to_csv(ritCSV, index=False, quoting=csv.QUOTE_ALL)


def add_exif_column(df, title, exif_tag, path):
    """
    Add a new column of exif data to a pandas dataframe containing image names
    :param df: pandas dataframe, contains image data
    :param title: string, column title
    :param exif_tag: exif tag to run exiftool with (e.g. -Make)
    :param path: path to root process directory
    :return: None
    """
    print('Updating: Adding new column: ' + title + '. This may take a moment for large sets of data... '),
    exifDataResult = subprocess.Popen(['exiftool', '-f', '-j', '-r', exif_tag, path], stdout=subprocess.PIPE).communicate()[0]
    exifDataResult = json.loads(exifDataResult)
    exifDict = {}
    for item in exifDataResult:
        exifDict[os.path.normpath(item['SourceFile'])] = item

    # create an empty column, and add the new exif data to it
    a = np.empty(df.shape[0])
    a[:] = np.NaN
    new = pd.Series(a, index=df.index)
    try:
        for index, row in df.iterrows():
            image = row['ImageFilename']
            sub = row['Type']
            key = os.path.join(path, sub, image)
            val = exifDict[os.path.normpath(key)][exif_tag[1:]]
            new[index] = val if val != '-' else ''
    except KeyError:
        print('Could not add column. You may encounter validation errors. It is recommended to re-process your data.')
        return

    df[title] = new
    print('done')


def parse_image_info(self, imageList, cameraData, **kwargs):
    """
    One of the critical backend functions for the HP tool. Parses out exifdata all of the images, and sorts into
    dictionary
    :param self: reference to HP GUI
    :param imageList: list of image filepaths
    :param kwargs: additional settings or metadata, including: rec (recursion T/F, path (input directory
    :return: data: dictionary containing image names and their gathered data
    """
    fields = load_json_dictionary(data_files._FIELDNAMES)
    master = {}

    exiftoolargs = []
    for fkey in fields:
        master[fkey] = ''
        if fields[fkey].startswith('-'):
            exiftoolargs.append(fields[fkey])

    for kkey in kwargs:
        if kkey in fields:
            master[kkey] = kwargs[kkey]

    exiftoolparams = ['exiftool', '-f', '-j', '-r', '-software', '-make', '-model', '-serialnumber'] if kwargs['rec'] else ['exiftool', '-f', '-j', '-software', '-make', '-model', '-serialnumber']
    exifDataResult = subprocess.Popen(exiftoolparams + exiftoolargs + [kwargs['path']], stdout=subprocess.PIPE).communicate()[0]

    # exifDataResult is in the form of a String json ("[{SourceFile:im1.jpg, imageBitsPerSample:blah}, {SourceFile:im2.jpg,...}]")
    try:
        exifDataResult = json.loads(exifDataResult)
    except:
        print('Exiftool could not return data for all input.')

    # further organize exif data into a dictionary based on source filename
    exifDict = {}
    for item in exifDataResult:
        exifDict[os.path.normpath(item['SourceFile'])] = item

    try:
        set_primary = cameraData[cameraData.keys()[0]]["camera_type"] != "CellPhone"
    except IndexError:
        set_primary = "model"

    data = {}
    reverseLUT = dict((remove_dash(v), k) for k, v in fields.iteritems() if v)
    for i in xrange(0, len(imageList)):
        if not (imageList[i].lower().endswith('.3d.zip') or os.path.splitext(imageList[i])[1].lower() in exts["nonstandard"]):
            try:
                data[i] = combine_exif(exifDict[os.path.normpath(imageList[i])], reverseLUT, master.copy())
            except KeyError:
                data[i] = combine_exif({}, reverseLUT, master.copy())
        else:
            image_file_list = os.listdir(os.path.normpath(os.path.dirname(imageList[i])))
            del image_file_list[image_file_list.index(os.path.basename(imageList[i]))]
            data[i] = combine_exif({"Thumbnail": "; ".join(image_file_list)},
                                   reverseLUT, master.copy())
        data[i] = set_other_data(self, data[i], imageList[i], set_primary)

    return data


def process_metadata(dir, metadata, recursive=False, quiet=False):
    """
    Attempts to add tags containing metadata gathered from preferences to all output images. Some media files will not
    be writable by exiftool
    Adds the following:
        copyright
        artist
        by-line
        credit
        usage terms
        copyright notice
    :param dir: string, root directory
    :param metadata: dictionary, metadata tags to write
    :param recursive: boolean, whether or not to recursively edit metadata of subdirectories too
    :param quiet: boolean, set to True for no progress messages
    :return:
    """
    exifToolInput = ['exiftool', '-progress']
    for key, value in metadata.iteritems():
        exifToolInput.append('-' + key + '=' + value)
    if recursive:
        exifToolInput.extend(('-XMPToolkit=', '-overwrite_original', '-r', '-L', '-m', '-P'))
    else:
        exifToolInput.extend(('-XMPToolkit=', '-overwrite_original', '-L', '-m', '-P'))

    exifToolInput.append(dir)

    if quiet:
        del exifToolInput[1]

    # run exiftool
    subprocess.call(exifToolInput)


def process(self, cameraData, imgdir='', outputdir='', recursive=False,
            keywords='', additionalInfo='', **kwargs):
    """
    The main process workflow for the hp tool.
    :param self: reference to HP GUI
    :param preferences: preferences filename
    :param imgdir: directory of raw images/video/audio files to be processed
    :param outputdir: output directory (csv, image, video, and audio files will be made here)
    :param recursive: boolean, whether or not to search subdirectories as well
    :param keywords:
    :param additionalInfo: additional bit to be added onto filenames
    :param kwargs: hp data to be set
    :return: list of paths of original images and new images
    """
    check_settings(self)
    print('Settings OK')

    # collect image list
    print('Collecting images...')
    imageList = []

    # set up the output subdirectories
    check_create_subdirectories(outputdir)

    imageList.extend(grab_dir(imgdir, os.path.join(outputdir, 'csv'), recursive))

    if not imageList:
        print('No new images found')
        remove_temp_subs(outputdir)
        if os.path.exists(os.path.join(outputdir, 'csv')):
            check_outdated(find_rit_file(os.path.join(outputdir, 'csv')), outputdir)
        else:
            tkMessageBox.showerror("Directory Error", "There has been an error processing the input directory.  Please verify there is media within the directory.  If there is only 3D Models or Lytro images to be processed, verify that you are following the correct directory structure.")
            return None, None
        return imageList, []

    # build information list. This is the bulk of the processing, and what runs exiftool
    print('Building image info...')
    imageInfo = parse_image_info(self, imageList, cameraData, path=imgdir, rec=recursive, **kwargs)
    if imageInfo is None:
        return None, None
    print('...done')

    # once we're sure we have info to work with, we can check for the image, video, and csv subdirectories
    check_create_subdirectories(outputdir)

    # prepare for the copy operation
    try:
        count = int(self.settings.get_key('seq'))
    except TypeError:
        count = 0
        self.settings.save('seq', '00000')

    # copy with renaming
    print('Copying files...')
    newNameList = []
    searchmodels = not (recursive or cameraData) or (not recursive and "lytro" in cameraData[cameraData.keys()[0]]["hp_camera_model"].lower())
    for image in imageList:
        newName = copyrename(image, outputdir, self.settings.get_key('username', ''), self.settings.get_key('hp-organization', ''), pad_to_5_str(count), additionalInfo, searchmodels)
        if os.path.split(newName)[1] == os.path.split(image)[1]:
            name = os.path.split(image)[1]

            if name.lower().endswith('.3d.zip'):
                tkMessageBox.showerror("Improper 3D Model Processing", "In order to process 3D models, you must have "
                                                                       "no device local ID and the 'Include "
                                                                       "Subdirectories' box must NOT be checked")
            else:
                tkMessageBox.showerror("Unrecognized data type", "An unrecognized data type {0} was found in the input "
                                                                 "directory.  Please add this extension to the list of "
                                                                 "addition extensions.".format(os.path.splitext(image)[1]))

            return
        # image_dir = os.path.dirname(image)
        # newFolder = copyrename(image_dir, outputdir, self.settings.get('username'), self.settings.get('organization'), pad_to_5_str(count), additionalInfo, searchmodels)
        # newImage = copyrename(image, outputdir, self.settings.get('username'), self.settings.get('organization'), pad_to_5_str(count), additionalInfo, searchmodels)
        newNameList += [newName]
        count += 1

    # Updates HP-Thumbnails tab to show renamed image names rather than the original image names.
    for model in xrange(0, len(imageInfo)):
        thumbnails = imageInfo[model]['HP-Thumbnails'].split("; ")
        try:
            del thumbnails[thumbnails.index('')]
        except ValueError:
            pass
        new_thumbnails = []
        if thumbnails:
            for thumbnail in thumbnails:
                model_path = os.path.dirname(os.path.normpath(imageList[model]))
                try:
                    new_thumbnails.append(thumbnail_conversion[model_path][thumbnail])
                except KeyError:
                    pass
        imageInfo[model]['HP-Thumbnails'] = "; ".join(new_thumbnails)

    # parse seeds
    def get_seed_file():
        seed = None
        while not seed:
            tkMessageBox.showinfo("Select Seed File", "Select the GAN seed file (ex. log.txt for the"
                                                      " Progressive GAN).")
            seed = tkFileDialog.askopenfilename()

        print("Loading seeds... "),
        seed_loader = SeedProcessor(self, seed)
        print("done.")
        seeds = seed_loader.get_seeds()
        return seeds

    try:
        local_id = cameraData.keys()[0]
    except IndexError:  # 3D Models
        local_id = ""
    if local_id.lower().startswith("gan"):
        if tkMessageBox.askyesno("Add Seed?", "Would you like to connect a seed file to these GAN images? "):
            seed_list = get_seed_file()
            while len(seed_list) != len(imageInfo):
                if len(seed_list) > len(imageInfo):
                    diff_type = "There are more seeds found than GANs.  If you continue with this seed file, the last" \
                                " {0} seeds will be unused.".format(len(seed_list) - len(imageInfo))
                if len(seed_list) < len(imageInfo):
                    diff_type = "There are more GANs found than seeds provided.  If you continue with this seed file," \
                                " the last {0} GANs will not have seeds.".format(len(imageInfo) - len(seed_list))
                retry_seed = tkMessageBox.askyesno("Mismatched Seed File", diff_type + "  Would you like to select a "
                                                                                       "different seed file?")
                if retry_seed:
                    seed_list = get_seed_file()
            for im in xrange(0, len(imageInfo)):
                try:
                    imageInfo[im]['HP-seed'] = seed_list[im]
                except IndexError:
                    break

    print(' done')

    self.settings.save('seq', pad_to_5_str(count))
    self.settings.save('date', datetime.datetime.now().strftime('%Y%m%d')[2:])
    print('Settings updated with new sequence number')

    print('Updating metadata...')

    metadata = {"usageterms": self.settings.get_key("usageterms"),
                "copyrightnotice": self.settings.get_key("copyrightnotice"),
                "credit": self.settings.get_key("credit"),
                "artist": self.settings.get_key("artist"),
                "copyright": self.settings.get_key("copyright"),
                "by-line": self.settings.get_key("by-line")}

    for folder in ['image', 'video', 'audio', 'model']:
        process_metadata(os.path.join(outputdir, folder, '.hptemp'), metadata, quiet=True)

    dt = datetime.datetime.now().strftime('%Y%m%d%H%M%S')[2:]

    for csv_type in ['rit', 'rankone', 'keywords']:
        print('Writing ' + csv_type + ' file')
        csv_path = os.path.join(outputdir, 'csv', '-'.join(
            (dt, self.settings.get_key('hp-organization') + self.settings.get_key('username'), csv_type + '.csv')))
        build_csv_file(self, imageList, newNameList, imageInfo, csv_path, csv_type)

    # move out of tempfolder
    print('Cleaning up...')
    remove_temp_subs(outputdir)

    print('\nComplete!')

    return imageList, newNameList
