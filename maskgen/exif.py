from subprocess import call, Popen, PIPE
import os
import numpy as np
import tool_set


def getOrientationFromExif(source):
    orientations = [None, None, 'Mirror horizontal', 'Rotate 180', 'Mirror vertical',
                    'Mirror horizontal and Rotate 270 CW', 'Rotate 90 CW', 'Mirror horizontal and rotate 90 CW',
                    'Rotate 270 CW']

    exifcommand = os.getenv('MASKGEN_EXIFTOOL', 'exiftool')
    rotateStr = Popen([exifcommand, '-n', '-Orientation', source],
                      stdout=PIPE).communicate()[0]

    rotation = rotateStr.split(':')[1].strip() if rotateStr.rfind(':') > 0 else '-'

    if rotation == '-':
        return None
    try:
        rotation_index = int(rotation)
        return orientations[rotation_index]
    except:
        return None


def rotateAccordingToExif(img_array, orientation, counter=False):
    rotation = orientation

    if rotation is None:
        return img_array
    if rotation == 'Mirror horizontal':
        rotatedArr = np.fliplr(img_array)
    elif rotation == 'Rotate 180':
        rotatedArr = np.rot90(img_array, 2)
    elif rotation == 'Mirror vertical':
        rotatedArr = np.flipud(img_array)
    elif rotation == 'Mirror horizontal and rotate 270 CW':
        rotatedArr = np.fliplr(img_array)
        rotatedArr = np.rot90(rotatedArr, 3)
    elif rotation == 'Rotate 90 CW':
        amount = 3 if counter else 1
        rotatedArr = np.rot90(img_array, amount)
    elif rotation == 'Mirror horizontal and rotate 90 CW':
        rotatedArr = np.fliplr(img_array)
        amount = 3 if counter else 1
        rotatedArr = np.rot90(rotatedArr,amount)
    elif rotation == 'Rotate 270 CW':
        amount = 1 if counter else 3
        rotatedArr = np.rot90(img_array, amount)
    else:
        rotatedArr = img_array

    return rotatedArr


def copyexif(source, target):
    exifcommand = os.getenv('MASKGEN_EXIFTOOL', 'exiftool')
    try:
        call([exifcommand, '-overwrite_original', '-q', '-all=', target])
        call([exifcommand, '-P', '-q', '-m', '-TagsFromFile', source, '-all:all', '-unsafe', target])
        call([exifcommand, '-XMPToolkit=', target])
        call([exifcommand, '-Warning=', target])
        return None
    except OSError:
        return 'exiftool not installed'


def runexif(args):
    exifcommand = os.getenv('MASKGEN_EXIFTOOL', 'exiftool')
    command = [exifcommand]
    command.extend(args)
    try:
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        try:
            while True:
                line = p.stdout.readline()
                if line is None or len(line) == 0:
                    break
        finally:
            p.stdout.close()
            p.stderr.close()
    except OSError as e:
        print "Exiftool not installed"
        raise e

def getexif(source):
    exifcommand = os.getenv('MASKGEN_EXIFTOOL', 'exiftool')
    meta = {}
    try:
        p = Popen([exifcommand, source], stdout=PIPE, stderr=PIPE)
        try:
            while True:
                line = p.stdout.readline()
                try:
                    line = unicode(line, 'utf-8')
                except:
                    try:
                        line = unicode(line, 'latin').encode('ascii', errors='xmlcharrefreplace')
                    except:
                        continue
                if line is None or len(line) == 0:
                    break
                pos = line.find(': ')
                if pos > 0:
                    meta[line[0:pos].strip()] = line[pos + 2:].strip()
        finally:
            p.stdout.close()
            p.stderr.close()
    except OSError:
        print "Exiftool not installed"
    return meta


def compareexif(source, target):
    meta_source = getexif(source)
    meta_target = getexif(target)
    diff = {}
    for k, sv in meta_source.iteritems():
        if k in meta_target:
            tv = meta_target[k]
            if tv != sv:
                diff[k] = ('change', sv, tv)
        else:
            diff[k] = ('delete', sv)
    for k, tv in meta_target.iteritems():
        if k not in meta_source:
            diff[k] = ('add', tv)
    return diff
