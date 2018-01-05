from subprocess import call, Popen, PIPE
import os
import numpy as np
import logging
from cachetools import cached
from cachetools import LRUCache
from threading import RLock


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


def rotateAnalysis( orientation):
    flip, rotate  = rotateAmount(orientation)
    result = {}
    if flip is not None:
        result['flip direction'] = flip
    if rotate  != 0:
        result['rotation'] = rotate
    return result

def rotateAmount( orientation):
    rotation = orientation
    if rotation == 'Mirror horizontal':
        return 'horizontal',0
    elif rotation == 'Rotate 180':
        return None, 180.0
    elif rotation == 'Mirror vertical':
        return 'vertical',0
    elif rotation == 'Mirror horizontal and rotate 270 CW':
        return 'horizontal', 270.0
    elif rotation == 'Rotate 90 CW':
        return None,90.0
    elif rotation == 'Mirror horizontal and rotate 90 CW':
        return 'horizontal', 90.0
    elif rotation == 'Rotate 270 CW':
        return None, 270.0
    try:
        return None, float (orientation)
    except:
        return None,0

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


def toolCheck():
    exifcommand = os.getenv('MASKGEN_EXIFTOOL', 'exiftool')
    try:
        stdout, stderr = Popen([exifcommand, '-ver'], stdout=PIPE, stderr=PIPE).communicate()
        if stdout is not None:
            return None
    except:
        return exifcommand + ' is not installed'

def runexif(args, fix=True, ignoreError=False):
    exifcommand = os.getenv('MASKGEN_EXIFTOOL', 'exiftool')
    command = [exifcommand]
    command.extend(args)
    try:
        pipe = Popen(command,stdout=PIPE,stderr=PIPE)
        stdout,stderr = pipe.communicate()
        if stdout is not None:
            for line in stdout.splitlines():
                logging.getLogger('maskgen').info("exif output for command " + str(command) + " = "+ line)
        if stderr is not None:
            newsetofargs = args
            for line in stderr.splitlines():
            #    newsetofargs = [item for item in newsetofargs if item[1:item.find ('=')] not in line]
                logging.getLogger('maskgen').info("exif output for command " + str(command) + " = " + line)
            ##try stripping off the offenders
            #if len(newsetofargs) < len(args) and fix:
            #    return runexif(newsetofargs, fix=False)
            #else:
            #    return False
            return pipe.returncode == 0
    except OSError as e:
        logging.getLogger('maskgen').error("Exiftool failure. Is it installed? "+ str(e))
        if not ignoreError:
            raise e
    return True

exif_lock = RLock()
exif_cache = LRUCache(maxsize=12)

def stringifyargs(kwargs):
    return [str(item) for item in sorted([(k,str(v)) for k,v in kwargs.iteritems()])]

def sourcefilehashkey(*args, **kwargs):
    import hashlib
    """Return a cache key for the specified hashable arguments."""
    return hashlib.sha384(' '.join(list([str(x) for x in args]) + stringifyargs(kwargs))).hexdigest()


@cached(exif_cache, lock=exif_lock, key=sourcefilehashkey)
def getexif(source, args=None, separator=': '):
    exifcommand = os.getenv('MASKGEN_EXIFTOOL', 'exiftool')
    command = [exifcommand]
    if args is not None:
        command.extend(args)
    command.append(source)
    meta = {}
    try:
        stdout, stderr = Popen(command,stdout=PIPE,stderr=PIPE).communicate()
        if stdout is not None:
            for line in stdout.splitlines():
                try:
                    line = unicode(line, 'utf-8')
                except:
                    try:
                        line = unicode(line, 'latin').encode('ascii', errors='xmlcharrefreplace')
                    except:
                        continue
                pos = line.find(separator)
                if pos > 0:
                    meta[line.split(separator)[0].strip()] = separator.join(line.split(separator)[1:]).strip()
    except OSError:
        logging.getLogger('maskgen').error("Exiftool failure. Is it installed? ")
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
