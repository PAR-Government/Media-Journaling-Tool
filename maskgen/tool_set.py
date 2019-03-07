# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import imghdr
import math
import platform
import re
import sys
import threading
import warnings
from datetime import datetime
from subprocess import Popen, PIPE

from scipy import ndimage
from skimage.measure import compare_ssim

import cv2api
import loghandling
import maskgen.exif
from ffmpeg_api import get_ffprobe_tool, ffmpeg_overlay
from image_wrap import *
from maskgen.support import removeValue, getValue
from maskgen.userinfo import get_username
from maskgen_loader import MaskGenLoader

imagefiletypes = [("jpeg files", "*.jpg"), ("png files", "*.png"), ("tiff files", "*.tiff"), ("tiff files", "*.tif"),
                  ("Raw NEF", "*.nef"), ("ARW Sony", "*.arw"), ("CRW Canon", "*.crw"), ("raw panasonic", "*.raw"),
                  ("Raw 2 Panasonic", "*.rw2"), ("ORF Olympus", "*.orf"), ("MDC Minolta", "*.mdc"),
                  ("PTX Pentax", "*.ptx"),
                  ("PEF Pentax", "*.pef"), ("MRW Minolta", "*.nrw"), ("Adobe", "*.dng"),
                  ("bmp files", "*.bmp"), ("pdf files", "*.pdf"), ('cr2', '*.cr2'), ('raf Fuji', '*.raf'),
                  ("NITF files","*.ntf"),("NITF files","*.nitf"),('JP2','*.jp2'), ('Lytro Raw','*.lfr'),
                  ("High Efficiency Image File Format", "*.heic"), ("High Efficiency Image File Format", "*.heif")]

videofiletypes = [("mpeg files", "*.mp4"), ("mov files", "*.mov"), ('wmv', '*.wmv'), ('m4p', '*.m4p'), ('m4v', '*.m4v'),
                  ('f4v', '*.flv'), ("avi files", "*.avi"), ('asf', '*.asf'), ('mts', '*.mts'), ('3gp', '*.3gp'),
                  ('mxf', '*.mxf')]
audiofiletypes = [("mpeg audio files", "*.m4a"), ("mpeg audio files", "*.m4p"), ("mpeg audio files", "*.mp3"),
                  ("raw audio files", "*.raw"), ("Audio Interchange File", "*.aif"),
                  ("Audio Interchange File", "*.aiff"),
                  ("Standard PC audio files", "*.wav"), ("Windows Media  audio files", "*.wma")]
zipfiletypes = [('zip of images','*.zip'),('zip of images','*.gz'),('zip of images','*.tgz')]

textfiletypes = [("CSV file", "*.csv"), ("json file", "*.json"), ("text file", "*.txt"), ("log file","*.log")]
suffixes = [".nef", ".jpg", ".png", ".tiff", ".bmp", ".avi", ".mp4", ".mov", ".wmv", ".ppm", ".pbm", ".mdc",".gif",
            ".raf", ".ptx", ".pef", ".mrw",".dng", ".zip",".gz", ".cr2",".jp2",
            ".wav", ".wma", ".m4p", ".mp3", ".m4a", ".raw", ".asf", ".mts",".tif",".arw",".orf",".raw",".rw2",".crw"]
maskfiletypes = [("png files", "*.png"), ("zipped masks", "*.tgz")]

modelfiletypes = [('3D Studio', '*.3ds'), ('Blender', '*.blen'), ('Collada', '*.dae'), ('AutoCAD', '*.dxf'),
                  ('Autodesk Exchange', '*.fbx'), ('geoTIFF', '*.tif'), ('gITF', '*.gITF'), ('Lightwave', '*.lwo'),
                  ('OBJ Files', '*.obj'), ('OFF File', '*.off'), ('PLY Files', '*.ply'), ('PTS Files', '*.pts'),
                  ('PTX Files', '*.ptx'), ('Sculptris', '*.sc1'), ('Pro/ENGINEER', '*.scl'),
                  ('Google Sketchup', '*.skp'), ('STL File', '*.stl'), ('TRI Files', '*.tri'), ('V3D Files', '*.v3d'),
                  ('VRML (WRL Files)', '*.wrl'), ('X3D Files', '*.x3d'), ('X3DV Files', '*.x3dv'),
                  ('SoftImage', '*.xsi'), ('ZBrush', '*.ztl'), ('XYZ Files', '*.xyz')]


class S3ProgessComposite(object):

    def __init__(self,progress_monitors = []):
        self.progress_monitors = progress_monitors

    def __call__(self, bytes_amount):
        for pm in self.progress_monitors:
            pm(bytes_amount)


class S3ProgressPercentage(object):

    def __init__(self, filename, log = None):
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self._percentage_so_far = 0
        self._lock = threading.Lock()
        self.log = log if log is not None else logging.getLogger('maskgen').info

    def __call__(self, bytes_amount):
        # To simplify we'll assume this is hooked up
        # to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            percentage = (self._seen_so_far / self._size) * 100
            if (percentage - self._percentage_so_far) > 5:
                self.log(
                    "%s  %s / %s  (%.2f%%)" % (
                        self._filename, self._seen_so_far, self._size,
                        percentage))
                self._percentage_so_far = percentage


def exportlogsto3(location, last_uploaded):
    import boto3
    loghandling.flush_logging()
    logging_file = get_logging_file()
    if logging_file is not None and last_uploaded != logging_file:
        logging_file_name = os.path.split(logging_file)[1]
        s3 = boto3.client('s3', 'us-east-1')
        bucket = location.split('/')[0].strip()
        directory = location[location.find('/') + 1:].strip()
        directory = directory[:-1] if directory.endswith('/') else directory
        directory = directory[:directory.rfind('/') + 1:].strip() + "logs/"
        try:
            s3.upload_file(logging_file, bucket, directory + get_username() + '_' + logging_file_name)
        except:
            logging.getLogger('maskgen').error("Could not upload prior log file to " + directory)
    return logging_file


def fetchbyS3URL(url):
    import boto3
    location = url[5:] if url.startswith('s3://') else url
    parts = location.split('/')
    BUCKET = parts[0].strip()
    location = location[location.find('/') + 1:].strip()
    file = parts[-1]
    s3 = boto3.resource('s3')
    destination = os.path.join('.', file)
    my_bucket = s3.Bucket(BUCKET)
    my_bucket.download_file(location, destination)
    return destination


def get_icon(name):
    places = []  # ['./icons']
    places.extend([os.path.join(x, 'icons/' + name) for x in sys.path if 'maskgen' in x])
    for place in places:
        if os.path.exists(place):
            return place
    return None


def get_logging_file():
    """
    :return: The last roll over log file
    """
    newest = None
    newest_time = None
    filename = 'maskgen.log.'
    for item in os.listdir('.'):
        if item.startswith(filename):
            t = os.stat(item).st_ctime
            if newest_time is None or newest_time < t:
                newest = item
                newest_time = t
    return newest


def getImageFileTypes():
    prefLoader = MaskGenLoader()
    filetypes = prefLoader.get_key('filetypes')
    filetypes = [] if filetypes is None else filetypes
    types = [tuple(x) for x in filetypes]
    tset = set([x[1] for x in types])
    for suffix in getFileTypes():
        if suffix[1] not in tset:
            types.append(suffix)
    return types


def getMaskFileTypes():
    return maskfiletypes


def getFileTypes():
    return imagefiletypes + videofiletypes + audiofiletypes + zipfiletypes


def fileTypeChanged(file_one, file_two):
    """
     Return: True if the file types of the two provided files do not match
    """
    try:
        one_type = fileType(file_one)
        two_type = fileType(file_two)
        return one_type != two_type
    except:
        return os.path.splitext(file_one)[1].lower() != os.path.splitext(file_two)[1].lower()


def runCommand(command,outputCollector=None):
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    errors = []
    if p.returncode == 0:
        if outputCollector is not None:
            for line in stdout.splitlines():
                outputCollector.append(line)
    if p.returncode != 0:
        try:
            if stderr is not None:
                for line in stderr.splitlines():
                    if len(line) > 2:
                        errors.append(line)
        except OSError as e:
            errors.append(str(e))
    return errors

def isVideo(filename):
    ffmpegcommand = [get_ffprobe_tool(), filename]
    try:
        p = Popen(ffmpegcommand, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
        return stderr.find('Invalid data') < 0
    except:
        return False

def getMimeType(filename):
    import subprocess
    import shlex
    cmd = shlex.split('file --mime-type "{0}"'.format(filename))
    try:
        result = subprocess.check_output(cmd)
        return (result.split(':')[1]).split('/')[0].strip()
    except Exception as e:
        logging.getLogger('maskgen').error('Cannot determine file type for "{}": {}'.format(
            filename,
            str(e)
        ))
        raise ValueError('Cannot determine file type for "{}"'.format(
            filename
        ))

def fileType(fileName):
    if os.path.isdir(fileName):
        return 'dir'
    lowerName = fileName.lower()
    suffixes = lowerName.split('.')
    suffix = '*.' + suffixes[-1] if len(suffixes) > 0 else ''
    file_type = None
    if suffix in ['*.zip', '*.tgz', '*.gz']:
        file_type = 'zip'
        if len(suffixes) > 2:
            content_type = '*.' + suffixes[-2]
            if  content_type not in [x[1] for x in imagefiletypes]:
                file_type = 'collection'
    elif suffix in [x[1] for x in imagefiletypes] or (os.path.exists(fileName) and imghdr.what(fileName) is not None):
        file_type = 'image'
    elif suffix in [x[1] for x in audiofiletypes]:
        file_type = 'audio'
    elif suffix in [x[1] for x in textfiletypes]:
        file_type = 'text'
    elif suffix in [x[1] for x in videofiletypes] or isVideo(fileName):
        file_type = 'video'
    return getMimeType(fileName) if file_type is None else file_type


def getOS():
    return platform.system() + ' ' + platform.release() + ' ' + platform.version()


def openFile(fileName):
    """
     Open a file using a native OS associated program
    """
    import sys
    if fileName.endswith('.hdf5'):
        fileName = convertToVideo(fileName, preferences=MaskGenLoader())
    if sys.platform.startswith('linux'):
        os.system('xdg-open "' + fileName + '"')
    elif sys.platform.startswith('win'):
        os.startfile(fileName)
    else:
        os.system('open "' + fileName + '"')


class IntObject:
    value = 0

    def __init__(self):
        pass

    def set(self, value):
        self.value = value

    def increment(self):
        self.value += 1
        return self.value




def imageResize(img, dim):
    """
    :param img:
    :param dim:
    :return:
    @rtype: ImageWrapper
    """
    return img.resize(dim, Image.ANTIALIAS).convert('RGBA')


def imageResizeRelative(img, dim, otherImDim):
    """
    Preserves the dimension ratios_
    :param dim:
    :param otherImDim: dimensions of other image
    :return: Resized relative to width given the maximum constraints
     @rtype: ImageWrapper
    """
    if otherImDim is None and img is not None:
        otherImDim = img.size
    if img is None:
        img = ImageWrapper(np.zeros((otherImDim[1], otherImDim[0]), dtype=np.uint8))
    wmax = max(img.size[0], otherImDim[0])
    hmax = max(img.size[1], otherImDim[1])
    wpercent = float(dim[0]) / float(wmax)
    hpercent = float(dim[1]) / float(hmax)
    perc = min(wpercent, hpercent)
    wsize = int((float(img.size[0]) * float(perc)))
    hsize = int((float(img.size[1]) * float(perc)))
    return img.resize((wsize, hsize), Image.ANTIALIAS)


def validateCoordinates(v):
    """
    Coordinates are [x,y] or (x,y) or x,y where x and y are integers.
    Return False if the coordinates are invalid.
    """
    try:
        return len([int(re.sub('[()]', '', x)) for x in v.split(',')]) == 2
    except ValueError:
        return False


def sumMask(mask):
    return int(np.sum(mask))


class VidTimeManager:


    """
    frameCountWhenStarted: record the frame at start
    frameCountWhenStopped: record the frame at finish
    """

    def __init__(self, startTimeandFrame=None, stopTimeandFrame=None):
        self.startTimeandFrame = startTimeandFrame
        self.stopTimeandFrame = stopTimeandFrame
        #if startTimeandFrame is not None and startTimeandFrame[1] > 0  and startTimeandFrame[0] > 0:
        #    self.startTimeandFrame = (startTimeandFrame[0],startTimeandFrame[1]+1)
        #if stopTimeandFrame is not None and stopTimeandFrame[1] > 0  and stopTimeandFrame[0] > 0:
        #    self.stopTimeandFrame = (stopTimeandFrame[0],stopTimeandFrame[1]+1)
        self.pastEndTime = False
        self.beforeStartTime = True if startTimeandFrame else False
        self.reachedEnd = False
        self.milliNow = 0
        self.frameCountWhenStopped = 0
        self.frameCountWhenStarted = 0
        self.frameSinceBeginning = 0
        self.frameCountSinceStart = 0
        self.frameCountSinceStop = 0

    def isAtBeginning(self):
        return self.startTimeandFrame is None or (self.startTimeandFrame[0] < 0 and self.startTimeandFrame[1] < 2)

    def spansToEnd(self):
        return self.stopTimeandFrame is None or (self.stopTimeandFrame[0] is None and self.stopTimeandFrame[1] is None)

    def getExpectedStartFrameGiveRate(self, rate, defaultValue=None):
        if not self.startTimeandFrame:
            return defaultValue
        return self.startTimeandFrame[1] + (self.startTimeandFrame[0] / 1000.0) * float(rate)

    def getExpectedEndFrameGiveRate(self, rate, defaultValue=None):
        if not self.stopTimeandFrame:
            return defaultValue
        val = int(self.stopTimeandFrame[1] + (self.stopTimeandFrame[0] / 1000.0) * float(rate))
        if val == 0:
            return defaultValue
        return self.stopTimeandFrame[1] + (self.stopTimeandFrame[0] / 1000.0) * float(rate)

    def getStartFrame(self):
        return self.frameCountWhenStarted if self.startTimeandFrame else 1

    def getEndFrame(self):
        return self.frameCountWhenStopped if self.stopTimeandFrame else self.frameSinceBeginning

    def updateToNow(self, milliNow, frames=1):
        """

        :param milliNow: time after the frame is to be displayed or sound emitted
        :param frames:
        :return:
        """
        self.milliNow = milliNow
        self.frameSinceBeginning += frames
        if self.stopTimeandFrame:
            if self.milliNow > self.stopTimeandFrame[0]:
                self.frameCountSinceStop += frames
                if self.frameCountSinceStop >= self.stopTimeandFrame[1]:
                    self.frameCountWhenStopped = self.frameSinceBeginning
                    self.reachedEnd = True
                    if not self.pastEndTime and self.frameCountSinceStop > self.stopTimeandFrame[1]:
                        self.pastEndTime = True
                        self.frameCountWhenStopped = self.frameSinceBeginning - 1

        if self.startTimeandFrame:
            if self.milliNow > self.startTimeandFrame[0]:
                self.frameCountSinceStart += frames
                if self.frameCountSinceStart >= self.startTimeandFrame[1]:
                    if self.beforeStartTime:
                        self.frameCountWhenStarted = self.frameSinceBeginning
                        self.beforeStartTime = False

    def setStopFrame(self, frame):
        ""
        if self.stopTimeandFrame[0] > 0:
            self.frameCountSinceStop = self.frameSinceBeginning
        self.stopTimeandFrame = (0,frame)

    def isOpenEnded(self):
        return self.stopTimeandFrame is None

    def isEnd(self):
        return self.reachedEnd

    def isPastTime(self):
        return self.pastEndTime

    def isPastStartTime(self):
        return self.startTimeandFrame and self.milliNow > self.startTimeandFrame[0] and \
               self.frameCountSinceStart > self.startTimeandFrame[1]

    def isBeforeTime(self):
        return self.beforeStartTime


def getFrameDurationString(st, et):
    """
     calculation duration
    """
    try:
        stdt = datetime.strptime(st, '%H:%M:%S.%f')
    except ValueError:
        stdt = datetime.strptime(st, '%H:%M:%S')

    try:
        etdt = datetime.strptime(et, '%H:%M:%S.%f')
    except ValueError:
        etdt = datetime.strptime(et, '%H:%M:%S')

    delta = etdt - stdt
    if delta.days < 0:
        return None

    sec = delta.seconds
    sec += (1 if delta.microseconds > 0 else 0)
    hr = sec / 3600
    mi = sec / 60 - (hr * 60)
    ss = sec - (hr * 3600) - mi * 60
    return '{:=02d}:{:=02d}:{:=02d}'.format(hr, mi, ss)


def getSecondDurationStringFromMilliseconds(millis):
    sec = int(millis / 1000)
    ms = int(millis - (sec * 1000))
    return '{:=02d}.{:=03d}'.format(sec, ms)


def getDurationStringFromMilliseconds(millis):
    sec = int(millis / 1000)
    ms = int((millis - (sec * 1000)) * 1000.0)
    hr = sec / 3600
    mi = sec / 60 - (hr * 60)
    ss = sec - (hr * 3600) - mi * 60
    return '{:=02d}:{:=02d}:{:=02d}.{:=06d}'.format(hr, mi, ss, ms)

def addTwo(num_string):
    return int(num_string) + 2


def sutractOne(num_string):
    return int(num_string) - 1


def addOneFrame(time_string):
    time_val = getMilliSecondsAndFrameCount(time_string, defaultValue=(0,0))
    return str(time_val[1] + 1)


def subtractOneFrame(time_string):
    time_val = getMilliSecondsAndFrameCount(time_string, defaultValue=(0,1))
    return str(time_val[1] - 1) if time_val[1] > 1 else '0'


def addFrame(millisAndFrame, frames):
    return millisAndFrame[0], millisAndFrame[1] + frames


def differenceBetweenFrame(mandf1, mandf2, rate):
    timediff = mandf1[0] - mandf2[0]
    frames = int(timediff*rate/1000.0)
    return  frames + (mandf1[1] - mandf2[1])

def differenceBetweeMillisecondsAndFrame(mandf1, mandf2, rate):
    return mandf1[0] - mandf2[0] + (rate * (mandf1[1] - mandf2[1]))


def differenceInFramesBetweenMillisecondsAndFrame(mandf1, mandf2, rate):
    return (mandf1[0] - mandf2[0]) / 1000.0 / rate + mandf1[1] - mandf2[1]


def getMilliSeconds(v):
    if v is None:
        return None, 0
    if type(v) == int:
        return v
    dt = None
    coloncount = v.count(':')
    if coloncount == 0:
        return int(float(v) * 1000.0)
    try:
        if '.' in v and len(v) > 15:
            v = v[:15]
        dt = datetime.strptime(v, '%H:%M:%S.%f')
    except ValueError:
        try:
            dt = datetime.strptime(v, '%H:%M:%S')
        except ValueError:
            return None
    millis = dt.hour * 360000 + dt.minute * 60000 + dt.second * 1000 + dt.microsecond / 1000
    return millis


def getMilliSecondsAndFrameCount(v, rate=None, defaultValue=None):
    if v is None:
        return defaultValue
    if type(v) == int:
        return (float(v) / rate * 1000, 0) if rate is not None else (0, 1 if v == 0 else v)
    frame_count = 0
    coloncount = v.count(':')
    if coloncount > 2:
        try:
            frame_count = int(v[v.rfind(':') + 1:])
            v = v[0:v.rfind(':')]
        except:
            return defaultValue
    elif coloncount == 0:
        return (float(v) / rate * 1000.0, 0) if rate is not None else (0, 1 if v == 0 else int(v))
    try:
        if '.' in v and len(v) > 15:
            v = v[:15]
        dt = datetime.strptime(v, '%H:%M:%S.%f')
    except ValueError:
        try:
            dt = datetime.strptime(v, '%H:%M:%S')
        except ValueError:
            return defaultValue
    millis = dt.hour * 360000 + dt.minute * 60000 + dt.second * 1000 + dt.microsecond / 1000
    if rate is not None:
        millis += float(frame_count) / rate * 1000.0
        frame_count = 0
    return (millis, frame_count) if (millis, frame_count) != (0, 0) else (0, 1)


def validateTimeString(v):
    if type(v) == int:
        return True

    if v.count(':') > 2:
        return False

    if v.count(':') == 0:
        try:
            int(v)
        except:
            return False
        return True
    try:
        datetime.strptime(v, '%H:%M:%S.%f')
    except ValueError:
        try:
            datetime.strptime(v, '%H:%M:%S')
        except ValueError:
            return False
    return True


def validateAndConvertTypedValue(argName, argValue, operationDef, skipFileValidation=True):
    """
      Validate a typed operation argument
      return the type converted argument if necessary
      raise a ValueError if invalid
    """
    if not argValue or len(str(argValue)) == 0:
        raise ValueError(argName + ' cannot be an empty string')
    argDef = operationDef.optionalparameters[argName] if argName in operationDef.optionalparameters else None
    argDef = operationDef.mandatoryparameters[
        argName] if not argDef and argName in operationDef.mandatoryparameters else argDef
    if argDef:
        if argDef['type'] == 'imagefile':
            if not os.path.exists(argValue) and not skipFileValidation:
                raise ValueError(argName + ' is an invalid file')
        elif argDef['type'].startswith('float'):
            typeDef = argDef['type']
            vals = [float(x) for x in typeDef[typeDef.rfind('[') + 1:-1].split(':')]
            if float(argValue) < vals[0] or float(argValue) > vals[1]:
                raise ValueError(argName + ' is not within the defined range')
            return float(argValue)
        elif argDef['type'].startswith('int'):
            typeDef = argDef['type']
            vals = [int(x) for x in typeDef[typeDef.rfind('[') + 1:-1].split(':')]
            if int(argValue) < vals[0] or int(argValue) > vals[1]:
                raise ValueError(argName + ' is not within the defined range')
            return int(argValue)
        elif argDef['type'] == 'list':
            if argValue not in argDef['values']:
                raise ValueError(argValue + ' is not one of the allowed values')
        elif argDef['type'] in ('frame_or_time', 'time'):
            if not validateTimeString(argValue):
                raise ValueError(argValue + ' is not a valid time (e.g. HH:MM:SS.micro)')
        elif argDef['type'] == 'yesno':
            if argValue.lower() not in ['yes', 'no']:
                raise ValueError(argName + ' is not yes or no')
        elif argDef['type'] == 'coorindates':
            if not validateCoordinates(argValue):
                raise ValueError(argName + ' is not a valid coordinate (e.g. (6,4)')
    return argValue


def _processFileMeta(stream):
    streams = []
    if stream is None:
        return streams
    for line in stream.splitlines():
        if line is None or len(line) == 0:
            break
        if 'Stream' in line:
            if 'Audio' in line:
                streams.append('audio')
            if 'Video' in line:
                streams.append('video')
    return streams


def getFileMeta(filename):
    ffmpegcommand = os.getenv('MASKGEN_FFPROBETOOL', 'ffprobe')
    try:
        stdout, stderr = Popen([ffmpegcommand, filename], stdout=PIPE, stderr=PIPE).communicate()
        if stderr is not None:
            meta = _processFileMeta(stderr)
        if stdout is not None:
            meta.extend(_processFileMeta(stdout))
        return meta
    except Exception as e:
        logging.getLogger('maskgen').error('FFMPEG error (is it installed?): ' + str(e))
    return {}


def millisec2time(milliseconds):
    ''' Convert milliseconds to 'HH:MM:SS.FFF' '''
    s, ms = divmod(milliseconds, 1000)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    if ms > 0:
        pattern = r'%02d:%02d:%02d.%03d'
        return pattern % (h, m, s, ms)
    else:
        pattern = r'%02d:%02d:%02d'
        return pattern % (h, m, s)


def outputVideoFrame(filename, outputName=None, videoFrameTime=None, isMask=False):
    import os
    ffcommand = os.getenv('MASKGEN_FFMPEG', 'ffmpeg')
    if outputName is not None:
        outfilename = outputName
    else:
        outfilename = os.path.splitext(filename)[0] + '.png'
    command = [ffcommand, '-i', filename]
    if videoFrameTime is not None:
        st = videoFrameTime[0] + 30 * videoFrameTime[1]
        command.extend(['-ss', millisec2time(st)])
    command.extend(['-vframes', '1', outfilename])
    try:
        p = Popen(command, stdout=PIPE, stderr=PIPE)
        p.communicate()
        p.wait()
    except OSError as e:
        logging.getLogger('maskgen').error("FFmpeg not installed")
        logging.getLogger('maskgen').error(str(e))
        raise e
    return openImage(outfilename, isMask=isMask)

class ZipWriter:

    def __init__(self, filename,fps=30):
        from zipfile import ZipFile
        self.filename = filename
        self.myzip = ZipFile(filename, 'w')
        self.count = 0
        self.fps = fps
        self.prefix = os.path.basename(os.path.splitext(filename)[0])
        #self.names = []

    def isOpened(self):
        #TODO: check names, what else
        return True

    def get(self,prop):
        if prop == cv2api.cv2api_delegate.prop_fps:
            return self.fps
        if prop == cv2api.cv2api_delegate.prop_frame_count:
            return self.count
        if prop == cv2api.cv2api_delegate.prop_pos_msec:
            return self.count * self.fps

    def write(self, frame):
        fname = "{}_{}.png".format(self.prefix, self.count)
        ImageWrapper(frame,filename=fname).save(fname)
        self.myzip.write(fname,fname)
        self.count+=1
        os.remove(fname)

    def release(self):
        self.myzip.close()

class ZipCapture:

    def __init__(self, filename, fps=30, filetypes=imagefiletypes):
        from zipfile import ZipFile
        import uuid
        self.filename = filename
        self.myzip = ZipFile(filename, 'r')
        file_type_matcher = re.compile('.*\.(' + '|'.join([ft[1][ft[1].rfind('.') + 1:] for ft in filetypes]) + ')')
        self.fps = fps
        self.count = 0
        self.dir = os.path.join(os.path.dirname(os.path.abspath(self.filename)) ,  uuid.uuid4().__str__())
        os.mkdir(self.dir)
        self.names = [name for name in self.myzip.namelist() if len(file_type_matcher.findall(name.lower())) > 0 and  \
                      os.path.basename(name) == name]

    def isOpened(self):
        #TODO: check names, what else
        return True

    def get(self,prop):
        if prop == cv2api.cv2api_delegate.prop_fps:
            return self.fps
        if prop == cv2api.cv2api_delegate.prop_frame_count:
            return self.count
        if prop == cv2api.cv2api_delegate.prop_pos_msec:
            return self.count* 1000.0/self.fps

    def grab(self):
        self.count+=1
        return self.count <= len(self.names)

    def get_exif(self):
        name = self.names[min(len(self.names)-1,self.count - 1)]
        extracted_file = os.path.join(self.dir,name)
        if not os.path.exists(extracted_file):
            extracted_file = self.myzip.extract(name, self.dir)
        return exif.getexif(extracted_file)

    def retrieve(self):
        if self.count > len(self.names):
            return False, None
        name = self.names[self.count-1]
        extracted_file = self.myzip.extract(name, self.dir)
        return True, openImage(extracted_file, isMask=False).to_array()

    def read(self):
        self.grab()
        return self.retrieve()

    def release(self):
        import shutil
        shutil.rmtree(self.dir)
        self.myzip.close()


def readFromZip(filename, filetypes=imagefiletypes, videoFrameTime=None, isMask=False, snapshotFileName=None, fps=30):
    from zipfile import ZipFile
    import re
    file_type_matcher = re.compile('.*\.(' + '|'.join([ft[1][ft[1].rfind('.') + 1:] for ft in filetypes]) + ')')
    with ZipFile(filename, 'r') as myzip:
        names = myzip.namelist()
        names.sort()
        time_manager = VidTimeManager(stopTimeandFrame=videoFrameTime)
        i = 0
        for name in names:
            i += 1
            elapsed_time = i * fps
            if len(file_type_matcher.findall(name.lower())) == 0:
                continue
            time_manager.updateToNow(elapsed_time)
            if time_manager.isPastTime() or videoFrameTime is None:
                break
        extracted_file = myzip.extract(name, os.path.dirname(os.path.abspath(filename)))
        img = openImage(extracted_file, isMask=isMask)
        if extracted_file != snapshotFileName and snapshotFileName is not None:
            img.save(snapshotFileName)
        return img

def readFromArchive(filename, filetypes=imagefiletypes, videoFrameTime=None, isMask=False, snapshotFileName=None, fps=30):
    import tarfile
    import re
    file_type_matcher = re.compile('.*\.(' + '|'.join([ft[1][ft[1].rfind('.') + 1:] for ft in filetypes]) + ')')
    archive = tarfile.open(filename, "w:gz")
    try:
        names = archive.getnames()
        names.sort()
        time_manager = VidTimeManager(stopTimeandFrame=videoFrameTime)
        i = 0
        for name in names:
            i += 1
            elapsed_time = i * fps
            if len(file_type_matcher.findall(name.lower())) == 0:
                continue
            time_manager.updateToNow(elapsed_time)
            if time_manager.isPastTime() or videoFrameTime is None:
                break
        extracted_file = archive.extract(name, os.path.dirname(os.path.abspath(filename)))
        img = openImage(extracted_file, isMask=isMask)
        if extracted_file != snapshotFileName and snapshotFileName is not None:
            img.save(snapshotFileName)
        return img
    finally:
        archive.close()

def readImageFromVideo(filename, videoFrameTime=None, isMask=False, snapshotFileName=None):
    cap = cv2api.cv2api_delegate.videoCapture(filename, useFFMPEGForTime=False)

    bestSoFar = None
    bestVariance = -1
    maxTry = 20
    time_manager = VidTimeManager(stopTimeandFrame=videoFrameTime)
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            frame = frame[..., ::-1]
            elapsed_time = cap.get(cv2api.cv2api_delegate.prop_pos_msec)
            time_manager.updateToNow(elapsed_time)
            if time_manager.isPastTime():
                bestSoFar = frame
                break
            varianceOfImage = math.sqrt(ndimage.measurements.variance(frame))
            if frame is not None and bestVariance < varianceOfImage:
                bestSoFar = frame
                bestVariance = varianceOfImage
            maxTry -= 1
            if not videoFrameTime and maxTry <= 0:
                break
    finally:
        cap.release()
    if bestSoFar is None:
        logging.getLogger('maskgen').error(
            "{} cannot be read by OpenCV/ffmpeg.  Mask generation will not function properly.".format(filename))
        return outputVideoFrame(filename, outputName=snapshotFileName, videoFrameTime=videoFrameTime, isMask=isMask)
    else:
        img = ImageWrapper(bestSoFar, to_mask=isMask)
        if snapshotFileName is not None and snapshotFileName != filename:
            img.save(snapshotFileName)
        return img


def md5_of_file(filename, raiseError=True):
    import hashlib
    try:
        with open(filename, 'rb') as rp:
            return hashlib.md5(rp.read()).hexdigest()
    except Exception as e:
        if raiseError:
            raise e
        return ''


def uniqueId():
    import time
    return str(time.time()).replace('.', '')


def shortenName(name, postfix, identifier=None):
    import hashlib
    middle = ''.join([(x[0] + x[-1] if len(x) > 1 else x) for x in name.split('_')])
    if identifier is not None:
        middle = middle + '_' + str(identifier)
    return hashlib.md5(name + postfix).hexdigest() + '_' + middle + '_' + postfix


class ImageOpener:
    def __init__(self):
        pass

    def openImage(self, filename, isMask=False, args=None):
        try:
            img = openImageFile(filename, isMask=isMask, args=args)
            return img if img is not None else openImage(get_icon('RedX.png'))
        except Exception as e:
            logging.getLogger('maskgen').warning('Failed to load ' + filename + ': ' + str(e))
            return openImage(get_icon('RedX.png'))


class AudioOpener(ImageOpener):
    def __init__(self):
        ImageOpener.__init__(self)

    def openImage(self, filename, isMask=False, args=None):
        return ImageOpener.openImage(self, get_icon('audio.png'))

class VideoOpener(ImageOpener):

    def __init__(self, videoFrameTime=None, preserveSnapshot=True):
        self.videoFrameTime = videoFrameTime
        self.preserveSnapshot = preserveSnapshot
        ImageOpener.__init__(self)

    def openSnapshot(self, filename, snapshotFileName):
        return os.path.exists(snapshotFileName) and \
               os.stat(snapshotFileName).st_mtime >= os.stat(filename).st_mtime

    def openImage(self, filename, isMask=False, args=None):
        if not ('video' in getFileMeta(filename)):
            return ImageOpener.openImage(self, get_icon('audio.png'))
        snapshotFileName = os.path.splitext(filename)[0] + '.png'
        if self.openSnapshot(filename, snapshotFileName):
            return ImageOpener.openImage(self, snapshotFileName)
        videoFrameImg = readImageFromVideo(filename, videoFrameTime=self.videoFrameTime, isMask=isMask,
                                           snapshotFileName=snapshotFileName if self.preserveSnapshot else None)
        if videoFrameImg is None:
            logging.getLogger('maskgen').warning('invalid or corrupted file ' + filename)
            return ImageOpener.openImage(self, get_icon('RedX.png'))
        return videoFrameImg

class ZipOpener(VideoOpener):
    def __init__(self, videoFrameTime=None, preserveSnapshot=True):
        VideoOpener.__init__(self, videoFrameTime=videoFrameTime, preserveSnapshot=preserveSnapshot)

    def openImage(self, filename, isMask=False, args=None):
        snapshotFileName = os.path.splitext(filename)[0] + '.png'
        if self.openSnapshot(filename, snapshotFileName):
            return ImageOpener.openImage(self, snapshotFileName)
        videoFrameImg = readFromZip(filename, videoFrameTime=self.videoFrameTime, isMask=isMask,
                                    snapshotFileName=snapshotFileName if self.preserveSnapshot else None)
        if videoFrameImg is None:
            logging.getLogger('maskgen').warning('invalid or corrupted file ' + filename)
            return ImageOpener.openImage(self, get_icon('RedX.png'))
        return videoFrameImg

class CollectionOpener(ImageOpener):
    def __init__(self):
        ImageOpener.__init__(self)

    def openImage(self, filename, isMask=False, args=None):
        return ImageOpener.openImage(self, get_icon('zip.jpg'))

class TgzOpener(VideoOpener):
    def __init__(self, videoFrameTime=None, preserveSnapshot=True):
        VideoOpener.__init__(self, videoFrameTime=videoFrameTime, preserveSnapshot=preserveSnapshot)

    def openImage(self, filename, isMask=False, args=None):
        snapshotFileName = os.path.splitext(filename)[0] + '.png'
        if self.openSnapshot(filename, snapshotFileName):
            return ImageOpener.openImage(self, snapshotFileName)
        videoFrameImg = readFromArchive(filename, videoFrameTime=self.videoFrameTime, isMask=isMask,
                                    snapshotFileName=snapshotFileName if self.preserveSnapshot else None)
        if videoFrameImg is None:
            logging.getLogger('maskgen').warning('invalid or corrupted file ' + filename)
            return ImageOpener.openImage(self, get_icon('RedX.png'))
        return videoFrameImg

def getContentsOfZip(filename):
    from zipfile import ZipFile
    with ZipFile(filename, 'r') as inzip:
        names = inzip.namelist()
        names.sort()
        return names


def condenseZip(filename, outputfile=None, filetypes=None, keep=2):
    from zipfile import ZipFile
    import re
    filetypematcher = re.compile('.*\.(' + '|'.join([ft[1][ft[1].rfind('.') + 1:] for ft in filetypes]) + ')') \
        if filetypes is not None else re.compile('.*')
    fn = os.path.splitext(filename)[0] + '_c' + os.path.splitext(filename)[1] if outputfile is None else outputfile
    cleanup = []
    try:
        with ZipFile(fn, 'w') as outzip:
            with ZipFile(filename, 'r') as inzip:
                names = inzip.namelist()
                names.sort()
                extensions = {}
                for i in range(len(names)):
                    name = names[i]
                    extension = os.path.splitext(name)[1]
                    if len(filetypematcher.findall(name)) == 0:
                        continue
                    if extension not in extensions:
                        extensions[extension] = 1
                    else:
                        extensions[extension] += 1
                    dir = os.path.dirname(os.path.abspath(filename))
                    extracted_file = os.path.join(dir, name)
                    cleanup.append(extracted_file)
                    if extensions[extension] <= keep:
                        extracted_file = inzip.extract(name, dir)
                        outzip.write(extracted_file, name)
                    else:
                        with open(extracted_file, 'wb') as fp:
                            fp.flush()
                        outzip.write(extracted_file, name)
    finally:
        for filename in cleanup:
            if os.path.exists(filename):
                os.remove(filename)


def openImage(filename, videoFrameTime=None, isMask=False, preserveSnapshot=False, args=None):
    """
    Open and return an image from the file. If the file is a video, find the first non-uniform frame.
    videoFrameTime, integer time in milliseconds, is provided, then find the frame after that point in time
    preserveSnapshot, False by default, informs the function to save the frame image after extraction for videos
    """
    import os

    if not os.path.exists(filename):
        logging.getLogger('maskgen').warning(filename + ' is missing.')
        if not filename.endswith('icons/RedX.png'):
            return openImage(get_icon('RedX.png'))
        return None

    prefix = os.path.splitext(filename)[1][1:].lower()
    opener = ImageOpener()
    if prefix in ['avi', 'mp4', 'mov', 'flv', 'qt', 'wmv', 'm4p', 'mpeg', 'mpv',
                  'm4v', 'mts', 'mpg'] or fileType(filename) == 'video':
        opener = VideoOpener(videoFrameTime=videoFrameTime, preserveSnapshot=preserveSnapshot)
    elif prefix in ['zip', 'gz']:
        if fileType(filename) == 'collection':
            opener = CollectionOpener()
        else:
            opener = ZipOpener(videoFrameTime=videoFrameTime, preserveSnapshot=preserveSnapshot)
    elif prefix in [ 'tgz']:
        if fileType(filename) == 'collection':
            opener = CollectionOpener()
        else:
            opener = TgzOpener(videoFrameTime=videoFrameTime, preserveSnapshot=preserveSnapshot)
    elif fileType(filename) == 'audio':
        opener = AudioOpener()

    return opener.openImage(filename, isMask=isMask, args=args)


def interpolateMask(mask, startIm, destIm, invert=False, arguments=dict()):
    """

    :param mask:
    :param img1:
    :param img2:
    :param invert:
    :param arguments:
    :return:
    @type mask: ImageWrapper
    @type img2: ImageWrapper
    @type img1: ImageWrapper
    """
    maskInverted = mask if invert else mask.invert()
    mask = np.asarray(mask)
    mask = mask.astype('uint8')
    logger = logging.getLogger('maskgen')
    try:
        mask1 = convertToMask(startIm).to_array() if startIm.has_alpha() else None
        logger.debug('SIFT')
        TM, matchCount = __sift(startIm, destIm, mask1=mask1, mask2=maskInverted, arguments=arguments)
    except:
        TM = None
    if TM is not None:
        logger.debug('WARP')
        newMask = cv2.warpPerspective(mask, TM, (startIm.size[0], startIm.size[1]), flags=cv2.WARP_INVERSE_MAP,
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=255)
        analysis = {}
        analysis['transform matrix'] = serializeMatrix(TM)
        return newMask, analysis
    elif getValue(arguments,'homography','None') != 'None':
        logger.debug('SIFT Failed. Find Countours')
        try:
            contours, hier = cv2api.findContours(255 - mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            minpoint = None
            maxpoint = None
            for contour in contours:
                for point in contour:
                    if type(point[0]) is np.ndarray:
                        point = point[0]
                    if minpoint is None:
                        minpoint = point
                    else:
                        minpoint = (min(minpoint[0], point[0]), min(minpoint[1], point[1]))
                    if maxpoint is None:
                        maxpoint = point
                    else:
                        maxpoint = (max(maxpoint[0], point[0]), max(maxpoint[1], point[1]))
            w = maxpoint[0] - minpoint[0] + 1
            h = maxpoint[1] - minpoint[1] + 1
            x = minpoint[0]
            y = minpoint[1]
            if (startIm.size[0] - w) == 0 and (startIm.size[1] - h) == 0:
                return mask[y:y + h, x:x + w], {}
        except:
            return None, None
    return None, None


def serializeMatrix(m):
    if m is None:
        return None
    data = {'r': m.shape[0],'c':m.shape[1]}
    for r in range(m.shape[0]):
        data['r' + str(r)] = list(m[r, :])
    return data

def deserializeMatrix(data):
    if data is None:
        return None
    m = np.zeros((int(data['r']), int(data['c'])))
    for r in range(m.shape[0]):
        m[r, :] = data['r' + str(r)]
    return m


def redistribute_intensity(edge_map):
    """
    Produce a intensity_map that redistributes the intensity values found in the edge_map evenly over 1 to 255
    :param edge_map contains a map between an edge identifier (s,e) and an intensity value from 1 to 255 and possibly a color
    :return map of intensity value from edge map to a replacement intensity value
    @type edge_map {(str,str): (int,[])}
    """
    levels = [x[0] for x in edge_map.values()]
    colors = [str(x[1]) for x in edge_map.values() if x[1] is not None]
    unique_colors = sorted(np.unique(colors))

    intensities = sorted(np.unique(levels))
    intensity_map = [0]
    if len(unique_colors) == len(intensities):
        for x in edge_map.values():
            intensity_map[x[0]] = x[1]
        return intensity_map
    increment = int(16777216 / (len(intensities) + 1))
    for pos in range(len(intensities)):
        v = (pos + 1) * increment
        intensity_map.append([(v % 65536) / 256, v / 65536, (v % 65536) % 256])
    for k, v in edge_map.iteritems():
        edge_map[k] = (v[0], intensity_map[v[0]])
    #im = np.zeros((500,500,3)).astype('uint8')
    #pos = 0
    #for i in intensity_map:
    #    im[pos,:] = i
    #    pos+=1
    #ImageWrapper(im).save('foo.png')
    return intensity_map


def maskToColorArray(img, color=[0, 0, 0]):
    """
    Create a new image setting all white to the color and all black to white.
    :param img:
    :param color:
    :return:
    @type img: ImageWrapper
    @rtype ImageWrapper
    """
    imarray = np.asarray(img)
    rgb = np.ones((imarray.shape[0], imarray.shape[1], 3)).astype('uint8') * 255
    rgb[imarray == 0, :] = color
    return rgb


def toColor(img, intensity_map={}):
    """
    Produce an image that changes gray scale to color.
    First, set the intensity values of each pixel using the intensity value from the intensity map
    Then use a color map to build a color image
    Then repopulate the edge_map with the assigned color for each edge
    :param img gray scale image
    :param intensity_map intensity value mapped to its replacement
    :return the new color image
    """
    result = cv2.applyColorMap(img.astype('uint8'), cv2.COLORMAP_HSV)
    for old, new in intensity_map.iteritems():
        result[img == old] = new
    result[img == 0] = [255, 255, 255]
    return result


def toComposite(img):
    """
    Convert to a mask with white indicating change
    :param img gray scale image
    :return image
    """
    result = np.zeros(img.shape).astype('uint8')
    result[img > 0] = 255
    return result


def toIntTuple(tupleString):
    import re
    if tupleString is not None and tupleString.find(',') > 0:
        return tuple([int(re.sub('[()L]', '', x)) for x in tupleString.split(',')])
    return 0, 0


def sizeOfChange(mask):
    if len(mask.shape) == 2:
        return mask.size - sumMask(mask == 255)
    else:
        mask_size = mask.shape[0] * mask.shape[1]
        return mask_size - sumMask(np.all(mask == [255, 255, 255], axis=2))


def maskChangeAnalysis(mask, globalAnalysis=False):
    mask = np.asarray(mask)
    totalPossible = reduce(lambda a, x: a * x, mask.shape)
    totalChange = sumMask(mask.astype('float32')) / 255.0
    ratio = float(totalChange) / float(totalPossible)
    globalchange = True
    if globalAnalysis:
        globalchange = ratio > 0.75
        kernel = np.ones((5, 5), np.uint8)
        erosion = cv2.erode(mask, kernel, iterations=2)
        closing = cv2.morphologyEx(erosion, cv2.MORPH_CLOSE, kernel)
        try:
            contours, hierarchy = cv2api.findContours(closing.astype('uint8'), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            p = np.asarray([item[0] for sublist in contours for item in sublist])
            if len(p) > 0:
                area = cv2.contourArea(cv2.convexHull(p))
                totalArea = cv2.contourArea(
                    np.asarray([[0, 0], [0, mask.shape[0]], [mask.shape[1], mask.shape[0]], [mask.shape[1], 0], [0, 0]]))
                globalchange = globalchange or area / totalArea > 0.50
        except:
            True,'empty'
    return globalchange, 'small' if totalChange < 2500 else ('medium' if totalChange < 10000 else 'large'), ratio


def SSIMAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments={}, directory='.'):
    globalchange = img1.size != img2.size
    img1, img2 = __alignChannels(img1, img2)
    analysis['ssim'] = compare_ssim(np.asarray(img1), np.asarray(img2), multichannel=False),
    if mask is not None:
        mask = np.copy(np.asarray(mask))
        mask[mask > 0] = 1
        analysis['local ssim'] = ssim(img1 * mask, img2 * mask, mask, R=65536)
    return globalchange


def globalTransformAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments={}, directory='.'):
    globalchange = img1.size != img2.size
    changeCategory = 'large'
    ratio = 1.0
    if mask is not None:
        globalchange, totalChange, ratio = maskChangeAnalysis(mask, not globalchange)
    analysis['global'] = arguments['global operation'] if 'global operation' in arguments else \
        ('yes' if globalchange else 'no')
    analysis['change size ratio'] = ratio
    analysis['change size category'] = changeCategory
    return globalchange


def localTransformAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments={}, directory='.'):
    globalchange = globalTransformAnalysis(analysis, img1, img2, mask=mask, linktype=linktype, arguments=arguments,
                                           directory=directory)
    analysis['global'] = 'no'
    return globalchange


def forcedSiftWithInputAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments=dict(), directory='.'):
    """
       Perform SIFT regardless of the global change status, using an input mask from the arguments
       to select the source region.
       :param analysis:
       :param img1:
       :param img2:
       :param mask:
       :param linktype:
       :param arguments:
       :return:
       """
    globalTransformAnalysis(analysis, img1, img2, mask=mask, arguments=arguments)
    if linktype != 'image.image':
        return
    if 'inputmaskname' in arguments:
        inputmask = openImageFile(os.path.join(directory, arguments['inputmaskname'])).to_mask().to_array()
        # a bit arbitrary.  If there is a less than  50% overlap, then isolate the regions highlighted by the inputmask
        # otherwise just use the change mask for the transform.  The change mask should be the full set of the pixels
        # changed and the input mask a subset of those pixels
        if sumMask(abs((mask.image_array - inputmask) / 255)) / float(sumMask(mask.image_array / 255)) >= 0.75:
            # want mask2 to be the region moved to
            mask2 = mask - inputmask
            # mask1 to be the region moved from
            mask = inputmask
        else:
            mask2 = mask.resize(img2.size, Image.ANTIALIAS) if mask is not None and img1.size != img2.size else mask
    else:
        mask2 = mask.resize(img2.size, Image.ANTIALIAS) if mask is not None and img1.size != img2.size else mask
    matrix, matchCount = __sift(img1, img2, mask1=mask, mask2=mask2, arguments=arguments)
    analysis['transform matrix'] = serializeMatrix(matrix)


def forcedSiftAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments=dict(), directory='.'):
    """
    Perform SIFT regardless of the global change status
    :param analysis:
    :param img1:
    :param img2:
    :param mask:
    :param linktype:
    :param arguments:
    :return:
    """
    globalTransformAnalysis(analysis, img1, img2, mask=mask, arguments=arguments)
    if linktype != 'image.image':
        return
    mask2 = mask.resize(img2.size, Image.ANTIALIAS) if mask is not None and img1.size != img2.size else mask
    matrix, matchCount = __sift(img1, img2, mask1=mask, mask2=mask2, arguments=arguments)
    analysis['transform matrix'] = serializeMatrix(matrix)


def seamAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments=dict(), directory='.'):
    forcedSiftAnalysis(analysis, img1, img2, mask=mask, linktype=linktype, arguments=arguments, directory=directory)
    if 'neighbor mask' in arguments:
        analysis['global'] = 'no'


def rotateSiftAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments=dict(), directory='.'):
    import copy
    rot = float(getValue(arguments,'rotation',-1))
    is_local = getValue(arguments,'local',True)
    globalTransformAnalysis(analysis, img1, img2, mask=mask, arguments=arguments)
    if abs(rot % 90)<0.001 and not is_local:
        return
    if is_local:
        return siftAnalysis(analysis, img1, img2, mask=mask, linktype=linktype, arguments=arguments, directory=directory)
    # global case and not a factor of 90
    # skip video
    if linktype != 'image.image':
        return
    mask2 = mask.resize(img2.size, Image.ANTIALIAS) if mask is not None and img1.size != img2.size else mask
    serializedMatrix = getValue(arguments,'transform matrix')
    if serializedMatrix is None:
        args = copy.copy(arguments)
        (x,y),(w,h) = boundingRegion(mask.invert().image_array)
        if (w-x + h-y) > 0.5*(mask.size[0] + mask.size[1]):
            args['Matcher.TREES'] = 6
            args['Matcher.CHECKS'] = 20
        matrix,matchCount = __sift(img1, img2, mask1=mask, mask2=mask2, arguments=args)
        if matrix is not None and isHomographyOk(matrix,img1.size[1],img1.size[0]):
            analysis['transform matrix'] = serializeMatrix(matrix)
    else:
        analysis['transform matrix']  = serializedMatrix

def siftAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments=dict(), directory='.'):
    if globalTransformAnalysis(analysis, img1, img2, mask=mask, arguments=arguments):
        return
    if linktype != 'image.image':
        return
    mask2 = mask.resize(img2.size, Image.ANTIALIAS) if mask is not None and img1.size != img2.size else mask
    matrix, matchCount = __sift(img1, img2, mask1=mask, mask2=mask2, arguments=arguments)
    analysis['transform matrix'] = serializeMatrix(matrix)

def boundingRegion(mask):
    x, y, w, h = widthandheight(mask)
    return (x, y), (x + w, y + h)

def boundingRectange(mask):
    allpoints = []
    contours, hierarchy = cv2api.findContours(np.copy(mask), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for i in range(0, len(contours)):
        cnt = contours[i]
        allpoints.extend(cnt)

    hull = cv2.convexHull(np.asarray(allpoints))
    return cv2.minAreaRect(hull)


def _affineTransformDonorImage(initialImage, donorImage, mask, donorMask):
    dims = initialImage.shape[2]
    IM = (255 - mask)
    IDM = (255 - donorMask)
    mcenter, mdims, mrotation = boundingRectange(IM)
    dcenter, ddims, drotation = boundingRectange(IDM)
    ratiox = float(donorImage.shape[0]) / float(initialImage.shape[0])
    ratioy = float(donorImage.shape[1]) / float(initialImage.shape[1])
    scale = min(float(mdims[0]) * ratiox / ddims[0], float(mdims[1]) * ratioy / ddims[1])
    M = cv2.getRotationMatrix2D(mcenter, drotation - mrotation, scale)
    IDM3 = np.zeros((donorImage.shape[0], donorImage.shape[1], dims))
    IM3 = np.zeros((initialImage.shape[0], initialImage.shape[1], dims))
    for i in range(dims):
        IDM3[:, :, i] = IDM
        IM3[:, :, i] = IM
    donorImageSelection = donorImage[:, :, 0:dims] * IDM3
    return cv2.warpAffine(donorImageSelection, M, (initialImage.shape[1], initialImage.shape[0]))


def generateOpacityImage(initialImage, donorImage, outputImg, mask, donorMask, tm):
    """
    Assume opacity is o such that

    outputImg = initialImage*(mask/255) + initialImage*((255-mask)/255)*(1-o) + donorImage*o*((255-donormask)/255)
    IM = inverted mask
    IDM = inverted donor mask
    outputImg - initialImage*(mask/255) = initialImage*IM - initialImage*IM*o + donorImage*o*((255-donormask)/255)
    outputImg - initialImage*(mask/255) - initialImage*IM  = donorImage*IDM*o - initialImage*IM*o
    outputImg - initialImage = donorImage*IDM*o - initialImage*IM*o
    outputImg - initialImage = o * (donorImage*IDM - initialImage*IM)
    o = (outputImg - initialImage)/(donorImage*IDM - initialImage*IM)
    Challenging since the donor mask is not lined up the image exactly.
    :param img1:
    :param img2:
    :param outputImg:
    :param mask:
    :return:
    """
    dims = initialImage.shape[2]
    IDM = (255 - donorMask) / 255
    IM = (255 - mask) / 255
    IDM3 = np.zeros((donorImage.shape[0], donorImage.shape[1], dims))
    IM3 = np.zeros((initialImage.shape[0], initialImage.shape[1], dims))
    for i in range(dims):
        IDM3[:, :, i] = IDM
        IM3[:, :, i] = IM
    donorImageSelection = (donorImage[:, :, 0:dims] * IDM3)
    if tm is not None:
        transformedImageAligned = cv2.warpPerspective(donorImageSelection, tm,
                                                      (initialImage.shape[1], initialImage.shape[0]),
                                                      flags=cv2.INTER_LINEAR,
                                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    else:
        transformedImageAligned = _affineTransformDonorImage(initialImage, donorImage, mask, donorMask).astype('uint8')
    # r = i(1-o) + t*o
    # r = i - o*i + t*o
    # r-i = o*t - o*i
    # r-i= o(t-i)
    # o = (r-i)/(t-i)
    diffDonorImage = abs(transformedImageAligned * IM3 - initialImage * IM3).astype('float32')
    diffOutputImage = abs(outputImg[:, :, 0:dims] * IM3 - initialImage * IM3).astype('float32')

    result = np.zeros(diffOutputImage.shape)
    result[diffDonorImage > 0.0] = diffOutputImage[diffDonorImage > 0] / diffDonorImage[diffDonorImage > 0.0]
    result[np.isinf(result)] = 0.0
    result[result > 1] = 1.0
    if dims > 3:
        result[:, :, 3] = 1
    return result


def generateOpacityColorMask(initialImage, donorImage, outputImg, mask, donorMask):
    result = generateOpacityImage(initialImage, donorImage, outputImg, mask, donorMask)
    min = np.min(result)
    max = np.max(result)
    return (result - min) / (max - min) * 255.0


def optionalSiftAnalysis(analysis, img1, img2, mask=None, linktype=None, arguments=dict(), directory='.'):
    if 'location change' not in arguments or arguments['location change'] == 'no':
        return
    globalTransformAnalysis(analysis, img1, img2, mask=mask, arguments=arguments)
    if linktype != 'image.image':
        return
    mask2 = mask.resize(img2.size, Image.ANTIALIAS) if mask is not None and img1.size != img2.size else mask
    matrix, matchCount = __sift(img1, img2, mask1=mask, mask2=mask2, arguments=arguments)
    if matrix is not None:
        analysis['transform matrix'] = serializeMatrix(matrix)


def createMask(img1, img2, invert=False, arguments={}, alternativeFunction=None, convertFunction=None):
    mask, analysis, error = __composeMask(img1,
                                          img2,
                                          invert,
                                          arguments=arguments,
                                          alternativeFunction=alternativeFunction,
                                          convertFunction=convertFunction)
    analysis['shape change'] = sizeDiff(img1, img2)
    if 'location' not in analysis:
        analysis['location'] = '(0,0)'
    analysis['empty mask'] = 'yes' if np.all(mask == 255) else 'no'
    return ImageWrapper(mask), analysis, error

def __indexOf(source, dest):
    positions = []
    for spos in range(len(source)):
        for dpos in range(len(dest)):
            if (source[spos] == dest[dpos]).all():
                positions.append(spos)
                break
    return positions

def __flannMatcher(d1, d2, args=None):
    FLANN_INDEX_KDTREE = 0
    TREES = 16
    CHECKS = 50
    if 'Matcher.CHECKS' in args:
        CHECKS = int(args['Matcher.CHECKS'])
    if 'Matcher.TREES' in args:
        TREES = int(args['Matcher.TREES'])
    index_params = dict(algorithm=FLANN_INDEX_KDTREE, trees=TREES)
    search_params = dict(checks=CHECKS)
    flann = cv2.FlannBasedMatcher(index_params, search_params)
    return flann.knnMatch(d1, d2, k=2) if d1 is not None and d2 is not None else []


def getMatchedSIFeatures(img1, img2, mask1=None, mask2=None, arguments=dict(), matcher=__flannMatcher):
    img1 = img1.to_rgb().apply_mask(mask1).to_array()
    img2 = img2.to_rgb().apply_mask(mask2).to_array()
    threshold = arguments['sift_match_threshold'] if 'sift_match_threshold' in arguments else 10
    maxmatches = int(arguments['homography max matches']) if 'homography max matches' in arguments else 10000

    (kp1, d1) = cv2api.cv2api_delegate.computeSIFT(img1)
    (kp2, d2) = cv2api.cv2api_delegate.computeSIFT(img2)

    if kp2 is None or len(kp2) == 0:
        return None

    if kp1 is None or len(kp1) == 0:
        return None

    d1 /= (d1.sum(axis=1, keepdims=True) + 1e-7)
    d1 = np.sqrt(d1)

    d2 /= (d2.sum(axis=1, keepdims=True) + 1e-7)
    d2 = np.sqrt(d2)

    matches = matcher(d1,d2, args=arguments)

    # store all the good matches as per Lowe's ratio test.
    good = [m for m, n in matches if m.distance < 0.75 * n.distance]
    good = sorted(good, lambda g1, g2: -int(max(g1.distance, g2.distance) * 1000))
    good = good[0:min(maxmatches, len(good))]

    if len(good) >= threshold:
        src_pts = np.float32([kp1[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
        return (src_pts, dst_pts) if src_pts is not None else None
    return None


def _remap(img, mask, src_pts, dst_pts):
    from scipy.interpolate import griddata
    long = mask.reshape(mask.shape[0] * mask.shape[1])
    grid_x, grid_y = np.mgrid[0:mask.shape[0], 0:mask.shape[1]]
    grid_z = griddata(np.array(dst_pts),
                      np.array(src_pts), (grid_x, grid_y), method='cubic', rescale=True)
    map_x = np.append([], [ar[:, 0] for ar in grid_z])
    map_y = np.append([], [ar[:, 1] for ar in grid_z])
    default_x = np.append([], [ar for ar in grid_x])
    default_y = np.append([], [ar for ar in grid_y])
    # remove remaps outside the mask
    map_x[long == 0] = default_x[long == 0]
    map_y[long == 0] = default_y[long == 0]
    # fix nan's with no mapping
    jj = np.where(np.isnan(map_x))
    map_x[jj] = default_x[jj]
    jj = np.where(np.isnan(map_y))
    map_y[jj] = default_y[jj]
    map_x_32 = map_x.astype('float32').reshape(mask.shape)
    map_y_32 = map_y.astype('float32').reshape(mask.shape)
    return cv2.remap(img, map_y_32, map_x_32, cv2.INTER_NEAREST)


def __grid(img1, img2, compositeMask, edgeMask=None, arguments=None):
    """
    Compute sparse maps from points between img1 to img2
    :param img1:
    :param img2:
    :param mask1:
    :param mask2:
    @type img1: ImageWrapper
    @type img2: ImageWrapper
    :return: None if a matrix cannot be constructed, otherwise a 3x3 transform matrix
    """
    src_dts_pts = getMatchedSIFeatures(img1, img2, mask1=edgeMask, mask2=None, arguments=arguments)
    if src_dts_pts is None:
        return compositeMask
    newMask = _remap(compositeMask, edgeMask,
                     [[x[0][1], x[0][0]] for x in src_dts_pts[0].astype('int')],
                     [[x[0][1], x[0][0]] for x in src_dts_pts[1].astype('int')])
    # r = np.zeros(r.shape).astype('uint8')
    # for x in range(len(src_dts_pts[1])):
    #  cv2.line(r,tuple(src_dts_pts[0][x][0]),tuple(src_dts_pts[1][x][0]),255)
    # r[int(x[0][1]),int(x[0][0])] = 255
    return newMask


def __sift(img1, img2, mask1=None, mask2=None, arguments=None):
    """
    Compute homography to transfrom img1 to img2
    Apply the mask to each in order to only compare relevent regions of images
    :param img1:
    :param img2:
    :param mask1:
    :param mask2:
    @type img1: ImageWrapper
    @type img2: ImageWrapper
    :return: None if a matrix cannot be constructed, otherwise a 3x3 transform matrix
    """
    arguments = dict(arguments)
    homography = arguments['homography'] if arguments is not None and 'homography' in arguments else 'RANSAC-4'
    if homography in ['None', 'Map']:
        return None, None
    elif homography in ['All'] and 'homography max matches' in arguments:
        # need as many as possible
        arguments.pop('homography max matches')
    src_dts_pts = getMatchedSIFeatures(img1, img2, mask1=mask1, mask2=mask2, arguments=arguments)
    if src_dts_pts is not None:
        new_src_pts = src_dts_pts[0]
        new_dst_pts = src_dts_pts[1]
        matches = None
        if homography == 'LMEDS':
            M1, matches = cv2.findHomography(new_src_pts, new_dst_pts, cv2.LMEDS)
        elif homography == 'All':
            M1, matches = cv2.findHomography(new_src_pts, new_dst_pts)
        elif homography.find('-') > 0:
            try:
                RANSAC_THRESHOLD = float(homography[homography.find('-') + 1])
            except:
                RANSAC_THRESHOLD = 10.0
            if matches is None:
                M1, matches = cv2.findHomography(new_src_pts, new_dst_pts, cv2.RANSAC, RANSAC_THRESHOLD)
        matchCount = np.sum(matches)
        if float(matchCount) / len(src_dts_pts) < 0.15 and matchCount < 30:
            return None, None
        return M1, matchCount
    return None, None


def applyResizeComposite(compositeMask, shape, interpolation=2):
    """
    Resize the composite mask
    :param compositeMask:
    :param transform_matrix:
    :return:
    """
    newMask = np.zeros(shape).astype('uint8')
    for level in list(np.unique(compositeMask)):
        if level == 0:
            continue
        levelMask = np.zeros(compositeMask.shape).astype('uint16')
        levelMask[compositeMask == level] = 1024
        newLevelMask = cv2.resize(levelMask, (shape[1], shape[0]),interpolation=interpolation)
        newMask[newLevelMask > 300] = level
    return newMask


class Flipper:
    def __init__(self, mask, flip):
        self.mask = mask
        self.flipdirection = flip
        self.region = boundingRegion(mask)

    def _lcs(self, alist, blist):
        """
        :param alist
        :param blist:
        :return:
        """
        m = len(alist)
        n = len(blist)
        counter = [[0] * (n + 1) for x in range(m + 1)]
        longest = 0
        lcs_set = (0, 0)
        for i in range(m):
            for j in range(n):
                if alist[i] == blist[j]:
                    c = counter[i][j] + 1
                    counter[i + 1][j + 1] = c
                    if c > longest:
                        lcs_set = (i, j)
                        longest = c
        return lcs_set, longest

    def flip(self, compositeMask):
        flipped = compositeMask[self.region[0][1]:self.region[1][1], self.region[0][0]:self.region[1][0]]
        flipped = cv2.flip(flipped,
                           1 if self.flipdirection == 'horizontal' else (-1 if self.flipdirection == 'both' else 0))
        flipCompositeMask = np.zeros(self.mask.shape).astype('uint8')
        flipCompositeMask[self.region[0][1]:self.region[1][1], self.region[0][0]:self.region[1][0]] = flipped
        return flipCompositeMask


def applyFlipComposite(compositeMask, mask, flip):
    """
    Since SIFT Cannot flip
    Flip the selected area
    :param compositeMask:
    :param mask:
    :param flip:
    :return:
    """
    maskInverted = ImageWrapper(np.asarray(mask)).invert().to_array()
    flipper = Flipper(maskInverted, flip)
    maskAltered = np.copy(mask)
    maskAltered[maskAltered > 0] = 1
    def work(levelMask):
        flipCompositeMask = flipper.flip(levelMask)
        return (flipCompositeMask + levelMask * maskAltered).astype('uint8')
    return applyToComposite(compositeMask,work)


def applyToComposite(compositeMask, func, shape=None):
    """
    Loop through each level add apply the function.
    Need to convert levels to 0 and unmapped levels to 255
    :param compositeMask:
    :param mask:
    :param transform_matrix:
    :return:
    """
    newMask = np.zeros(shape if shape is not None else compositeMask.shape).astype('uint8')
    for level in list(np.unique(compositeMask)):
        if level == 0:
            continue
        levelMask = np.zeros(compositeMask.shape).astype('uint8')
        levelMask[compositeMask == level] = 255
        newLevelMask = func(levelMask)
        if newLevelMask is not None:
            newMask[newLevelMask > 100] = level
    return newMask


def applyGridTransformCompositeImage(compositeMask, startIm, destIm, edgeMask=None, arguments={}):
    newMask = np.zeros((destIm.image_array.shape[0], destIm.image_array.shape[1]), dtype=np.uint8)
    arguments = dict(arguments)
    if 'homography max matches' in arguments:
        arguments.pop('homography max matches')
    levels = list(np.unique(compositeMask))
    for level in levels:
        if level == 0:
            continue
        levelMask = np.zeros(compositeMask.shape).astype('uint16')
        levelMask[compositeMask == level] = 255
        newlevelmask = __grid(startIm, destIm, levelMask, edgeMask=255 - edgeMask, arguments=arguments)
        if newlevelmask is not None:
            newMask[newlevelmask > 100] = level
    return newMask


def applyInterpolateToCompositeImage(compositeMask, startIm, destIm, edgeMask, inverse=False, arguments={},
                                     defaultTransform=None,
                                     withMask = False):
    """
       Loop through each level add apply SIFT to transform the mask
       :param compositeMask:
       :param mask:
       :param transform_matrix:
       :return:
       @type destIm: ImageWrapper
       @type startIm: ImageWrapper
       """
    newMask = np.zeros((destIm.image_array.shape[0], destIm.image_array.shape[1]), dtype=np.uint8)
    if 'homography' in arguments and arguments['homography'] == 'Map':
        return applyGridTransformCompositeImage(compositeMask,
                                                startIm,
                                                destIm,
                                                edgeMask=edgeMask,
                                                arguments=arguments)
    if 'homography' in arguments and arguments['homography'] == 'None':
        return compositeMask
    levels = list(np.unique(compositeMask))
    flags = cv2.WARP_INVERSE_MAP if inverse else cv2.INTER_LINEAR
    borderValue = 0
    for level in levels:
        if level == 0:
            continue
        if defaultTransform is None or (
                        'composite homography' in arguments and arguments['composite homography'] == 'Multiple'):
            levelMask = np.zeros(compositeMask.shape).astype('uint8')
            levelMask[compositeMask == level] = 200
            TM, matchCountResult = __sift(startIm, destIm, mask1=levelMask, mask2=invertMask(ImageWrapper(edgeMask)), arguments=arguments)
        else:
            TM = defaultTransform
        levelMask = np.zeros(compositeMask.shape).astype('uint16')
        levelMask[compositeMask == level] = 8000
        if TM is None:
            newLevelMask = cv2.resize(levelMask, (destIm.size[0], destIm.size[1]))
        elif withMask:
            newLevelMask = applyTransform(levelMask,
                                          mask=edgeMask,
                                          transform_matrix=TM,
                                          invert=inverse,
                                          shape=(destIm.size[1], destIm.size[0]))
        else:
            newLevelMask = cv2.warpPerspective(levelMask, TM, (destIm.size[0], destIm.size[1]),
                                               flags=flags,
                                               borderMode=cv2.BORDER_CONSTANT, borderValue=borderValue)
        if newLevelMask is not None:
            newMask[newLevelMask > 100] = level

    return newMask


def applyRotateToCompositeImage(img, angle, pivot):
    """
       Loop through each level add apply the rotation.
       Need to convert levels to 0 and unmapped levels to 255
       :param img:
       :param angle:
       :param pivot:
       :return:
       """
    from functools import partial
    func = partial(rotateImage, angle, pivot)
    return applyToComposite(img, func, shape=img.shape)


def applyTransformToComposite(compositeMask, mask, transform_matrix, shape=None, returnRaw=False):
    """
    Loop through each level add apply the transform.
    Need to convert levels to 0 and unmapped levels to 255
    :param compositeMask:
    :param mask:
    :param transform_matrix:
    :return:
    """
    from functools import partial
    func = partial(applyTransform, mask=mask, transform_matrix=transform_matrix, shape=shape, returnRaw=returnRaw)
    return applyToComposite(compositeMask, func, shape=shape)


def applyPerspectiveToComposite(compositeMask, transform_matrix, shape):
    def perspectiveChange(composite_mask, M=None, shape=None):
        return cv2.warpPerspective(composite_mask, M, (shape[1], shape[0]))

    from functools import partial
    func = partial(perspectiveChange, M=transform_matrix, shape=shape)
    return applyToComposite(compositeMask, func, shape=shape)


def applyAffineToComposite(compositeMask, transform_matrix, shape):
    def perspectiveChange(composite_mask, M=None, shape=None):
        return cv2.warpAffine(composite_mask, M, (shape[1], shape[0]))

    from functools import partial
    func = partial(perspectiveChange, M=transform_matrix, shape=shape)
    return applyToComposite(compositeMask, func, shape=shape)


def applyRotateToComposite(rotation, compositeMask, edgeMask, expectedDims, local=False):
    """
       Loop through each level add apply the rotation.
       Need to convert levels to 0 and unmapped levels to 255
       :param rotation:
       :param compositeMask:
       :param edgeMask:
       :param expectedDims:
       :param local
       :return:
       """
    from functools import partial
    if local:
        func = partial(__localrotateImage, rotation, edgeMask, expectedDims=expectedDims, cval=255)
    else:
        func = partial(__rotateImage, rotation, expectedDims=expectedDims, cval=255)
    return applyToComposite(compositeMask, func, shape=expectedDims)


def isHomographyOk(transform_matrix, h, w):
    # convert cornore to homogenous coordinates
    ll = np.array([0, 0, 1])
    ul = np.array([0, w, 1])
    lr = np.array([h, 0, 1])
    ur = np.array([h, w, 1])
    if transform_matrix.shape == (2,3):
        transform_matrix = np.vstack([transform_matrix,[0,0,1.0]])

    a_ll = np.matmul(transform_matrix, ll)
    a_ul = np.matmul(transform_matrix, ul)
    a_ur = np.matmul(transform_matrix, ur)
    a_lr = np.matmul(transform_matrix, lr)
    # convert points to lines
    a = np.cross(a_ll, a_ul)
    b = np.cross(a_lr, a_ur)
    # find point of intersection
    intersection_point_projective = np.cross(a, b)
    if intersection_point_projective[2] == 0:
        return False
    y_vertical = intersection_point_projective[0] / intersection_point_projective[2]
    x_vertical = intersection_point_projective[1] / intersection_point_projective[2]

    a = np.cross(a_ul, a_ur)
    b = np.cross(a_ll, a_lr)
    # find point of intersection
    intersection_point_projective = np.cross(a, b)
    if intersection_point_projective[2] == 0:
        return False
    y_horizontal = intersection_point_projective[0] / intersection_point_projective[2]
    x_horizontal = intersection_point_projective[1] / intersection_point_projective[2]
    # if the resulting lines intersect inside the box, fail
    return not (0 <= x_vertical <= w and 0 <= y_vertical <= h) and not (
        0 <= x_horizontal <= w and 0 <= y_horizontal <= h)
    # Or is more appropriate to look at the hull of the shape.
    # point = Point(x,y)
    # points = [(d[0] / d[2], d[1] / d[2]) for d in [a_ll,a_ul,a_ur,a_lr]]
    ##polygon = Polygon(points).convex_hull
    # return not polygon.contains(point)


def applyTransform(compositeMask, mask=None, transform_matrix=None, invert=False, returnRaw=False, shape=None):
    """
    Ceate a new mask applying the transform to only those parts of the
    compositeMask that overlay with the provided mask.
    :param compositeMask:
    :param mask:  255 for unmanipulated pixels
    :param transform_matrix:
    :param invert:
    :param returnRaw: do merge back in the composite
    :return:
    """
    flags = cv2.WARP_INVERSE_MAP if invert else cv2.INTER_LINEAR  # +cv2.CV_WARP_FILL_OUTLIERS
    maskInverted = ImageWrapper(np.asarray(mask)).invert().to_array()
    maskInverted[maskInverted > 0] = 1
    compositeMaskFlipped = compositeMask

    # resize only occurs by user error.
    if compositeMaskFlipped.shape != maskInverted.shape:
        compositeMaskFlipped = cv2.resize(compositeMaskFlipped, (maskInverted.shape[1], maskInverted.shape[0]))
        compositeMask = cv2.resize(compositeMask, (maskInverted.shape[1], maskInverted.shape[0]))

    if shape is None:
        shape = mask.shape
    # zeros out areas outside the mask
    compositeMaskAltered = compositeMaskFlipped * maskInverted

    maxvalue = compositeMaskAltered.max()

    compositeMaskAltered[compositeMaskAltered > 0] = maxvalue-20
    if transform_matrix.shape[0] == 2:
        newMask = cv2.warpAffine(compositeMaskAltered, transform_matrix, (shape[1], shape[0]), flags=flags,
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    else:
        newMask = cv2.warpPerspective(compositeMaskAltered, transform_matrix, (shape[1], shape[0]), flags=flags,
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    newMask[newMask > 99] = maxvalue
    newMask[newMask < 100] = 0
    # put the areas outside the mask back into the composite
    maskAltered = np.copy(mask)
    maskAltered[maskAltered > 0] = 1
    if returnRaw:
        return newMask
    newMask = newMask | compositeMask * maskAltered
    return newMask

def cropResize(img,location, wh):
    img_crop = img[location[0]:wh[0],location[1]:wh[1],:]
    return cv2.resize(img_crop, (img.shape[1],img.shape[0]))

def cropResizeCompare(img1, img2, arguments=dict()):
    width_and_height = (int(arguments['crop width']), int(arguments['crop height']))
    pre_resize_img = cv2.resize(img2, width_and_height)
    return composeCropImageMask(img1, pre_resize_img, location=None)

def cropCompare(img1, img2, arguments=dict()):
    from maskgen.image_wrap import ImageWrapper
    if (sum(img1.shape) > sum(img2.shape)):
        img1_m, img2_m = __alignChannels(ImageWrapper(img1), ImageWrapper(img2))
        analysis = {'shape change': sizeDiff(ImageWrapper(img1_m), ImageWrapper(img2_m))}
        location = getValue(arguments,'location',None)
        if type(location) == str:
            location = toIntTuple(location)
        mask, analysis_d = composeCropImageMask(img1_m, img2_m,location=location)
        analysis.update(analysis)
        return mask, analysis_d
    return None, {}

def _composeLCS(img1, img2):
    from scipy import sparse
    m = img1.shape[0] * img1.shape[1]
    n = img2.shape[0] * img2.shape[1]
    LCS = sparse.lil_matrix((m + 1, n + 1), dtype=np.int8)
    # that L[i][j] contains length of LCS of X[0..i-1] and Y[0..j-1]
    for i in xrange(1, m + 1, 1):
        for j in xrange(1, n + 1, 1):
            x1 = (i - 1) % img1.shape[0]
            y1 = (i - 1) / img1.shape[0]
            x2 = (j - 1) % img2.shape[0]
            y2 = (j - 1) / img2.shape[0]
            if img1[x1, y1] == img2[x2, y2]:
                LCS[i, j] = LCS[i - 1, j - 1] + 1
            else:
                m = max(LCS[i - 1, j], LCS[i, j - 1])
                if m > 0:
                    LCS[i, j] = m
                    # Start from the right-most-bottom-most corner and
                    # one by one store characters in lcs[]
    i = m - 1
    j = n - 1
    mask = np.zeros(img1.shape, dtype=np.uint8)
    while i >= 0 and j >= 0:
        x1 = i % img1.shape[0]
        y1 = i / img1.shape[0]
        x2 = j % img2.shape[0]
        y2 = j / img2.shape[0]
        if img1[x1, y1] == img2[x2, y2]:
            mask[x1, y1] = 255
            i -= 1
            j -= 1
        # If not same, then find the larger of two and
        # go in the direction of larger value
        elif LCS[i - 1, j] > LCS[i, j - 1]:
            i -= 1
        else:
            j -= 1


def __search1(pixel, img2, tally, endx, endy, x, y):
    from collections import deque
    def __addToQueue(x, y, endx, endy, queue):
        if x > endx:
            queue.append((x - 1, y))
        if y > endy:
            queue.append((x, y - 1))
            if x > endx:
                queue.append((x - 1, y - 1))

    pixel2 = img2[x, y]
    if pixel == pixel2:
        return (x, y)
    queue = deque()
    __addToQueue(x, y, endx, endy, queue)
    while len(queue) > 0:
        x, y = queue.popleft()
        pixel2 = img2[x, y]
        if pixel == pixel2:
            return x, y
        if tally[x, y] == 0:
            __addToQueue(x, y, endx, endy, queue)
    return None


def __search(pixel, img2, tally, position, depth):
    startx = min(max(0, position[0] - depth[0]), img2.shape[0])
    starty = min(max(0, position[1] - depth[1]), img2.shape[1])
    endx = min(position[0] + depth[0], img2.shape[0]) + 1
    endy = min(position[1] + depth[1], img2.shape[1]) + 1
    imgbox = img2[startx:endx, starty:endy]
    image_positions = zip(*np.where(imgbox == pixel))
    if len(image_positions) > 0:
        tallybox = tally[startx:endx, starty:endy]
        tallypostions = zip(*np.where(tallybox > 0))
        if len(tallypostions) > 0:
            maxtally = max(tallypostions)
            image_positions = [p for p in image_positions if p > maxtally]
    else:
        return None
    if len(image_positions) > 0:
        best = min(image_positions)
        return startx + best[0], starty + best[1]
    return None


def _tallySeam(img1, img2, minDepth=50):
    tally1 = np.zeros(img1.shape)
    tally2 = np.zeros(img2.shape)
    depth_x = max(img2.shape[0] - img1.shape[0], minDepth)
    depth_y = max(img2.shape[1] - img1.shape[1], minDepth)
    for x1 in range(img1.shape[0]):
        for y1 in range(img1.shape[1]):
            pos = __search(img1[x1, y1], img2, tally2, (x1, y1), (depth_x, depth_y))
            if pos is not None:
                tally1[x1, y1] = 1
                tally2[pos[0], pos[1]] = 1
    return tally1.astype('uint8') * 255


def rotateCompare(img1, img2, arguments=dict()):
    rotation = float(arguments['rotation']) if 'rotation' in arguments else 0.0
    local = (arguments['local'] == 'yes') if 'local' in arguments else False
    if img1.shape == img2.shape:
        mask1, analysis1 = __diffMask(img1, img2, False, args=arguments)
        if abs(rotation) < 0.0001:
            return mask1, analysis1
        mask2, analysis2 = __compareRotatedImage(rotation, img1, img2, arguments)
        diff = sumMask(mask1) - sumMask(mask2)
        return (mask1, analysis1) if diff < 0 or local else (mask2, analysis2)
    else:
        return __compareRotatedImage(rotation, img1, img2, arguments)


def resizeImage(img1, shape, interpolation):
    name_map = {
        'bicubic': cv2api.cv2api_delegate.inter_cubic,
        'nearest': cv2api.cv2api_delegate.inter_nn,
        'bilinear': cv2api.cv2api_delegate.inter_linear,
        'cubic': cv2api.cv2api_delegate.inter_cubic,
        'mesh': cv2api.cv2api_delegate.inter_area,
        'lanczos': cv2api.cv2api_delegate.inter_lanczos
    }
    inter_val = name_map[interpolation] if interpolation in name_map else cv2api.cv2api_delegate.inter_nn
    return cv2.resize(img1, (shape[1], shape[0]), interpolation=inter_val)


def resizeCompare(img1, img2, arguments=dict()):
    new_img2 = resizeImage(img2,
                           img1.shape,
                           arguments['interpolation'] if 'interpolation' in arguments else 'nearest')
    return __diffMask(img1, new_img2, False, args=arguments)


def moving_average(a, n=3):
    ret = np.cumsum(a, dtype=float)
    ret[n:] = ret[n:] - ret[:-n]
    return ret[n - 1:] / n

def morphologyCompare(img_one, img_two, arguments= {}):
    kernel_size = int(getValue(arguments, 'kernel', 3))
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    diff = (np.abs(img_one - img_two)).astype('uint16')
    mask = np.sum(diff, 2)
    difference = float(arguments['tolerance']) if arguments is not None and 'tolerance' in arguments else 0.00390625
    difference = difference * 256
    mask[np.where(mask < difference)] = 0
    if getValue(arguments, 'distribute_difference', False):
        mask = 255*mask.astype(np.double)/(np.max(mask)-difference)
        mask = mask.astype('uint8')
    else:
        # set to black if less than threshold
        mask[np.where(mask > 0)] = 255
        mask = mask.astype('uint8')
        mask = cv2.morphologyEx(mask,cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)# filter out noise in the mask
    return mask, {}

def mediatedCompare(img_one, img_two, arguments={}):
    gain = int(getValue(arguments, 'gain', 0))
    kernel_size=int(getValue(arguments, 'kernel',3))
    weight = int(getValue(arguments, 'weight', 1.0))
    smoothing = int(getValue(arguments, 'smoothing', 3))
    algorithm = getValue(arguments, 'filling', 'morphology')
    aggregate = getValue(arguments, 'aggregate', 'max')
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    from scipy import signal
    # compute diff in 3 colors
    if aggregate == 'luminance':
        min_threshold = int(getValue(arguments, 'minimum threshold', 3))
        img_one = cv2.cvtColor(img_one.astype('uint8'), cv2.COLOR_BGR2YCR_CB)
        img_two = cv2.cvtColor(img_two.astype('uint8'), cv2.COLOR_BGR2YCR_CB)
        diff = (np.abs(img_one.astype('int16') - img_two.astype('int16')))
        mask = diff[:, :, 0] + (diff[:, :, 2] + diff[:, :, 1])/weight
        bins = 256 + 512/weight
    else:
        min_threshold = int(getValue(arguments, 'minimum threshold', 9))
        diff = (np.abs(img_one.astype('int16') - img_two.astype('int16'))).astype('uint16')
        if aggregate == 'max':
            mask = np.max(diff, 2)  # use the biggest difference of the 3 colors
            bins=256
        elif aggregate == 'sum':
            mask = np.sum(diff, 2)
            bins=768
        else:
            mask = np.mean(diff, 2)
            bins = 256
    hist, bin_edges = np.histogram(mask, bins=bins, density=False)
    hist = moving_average(hist,n=smoothing)  # smooth out the histogram
    minima = signal.argrelmin(hist, order=2)  # find local minima
    if minima[0].size == 0 or minima[0][0] > bins/2:  # if there was no minima, hardcode
        threshold = min_threshold
    else:
        threshold = max(min_threshold,minima[0][0])  # Use first minima

    threshold += gain
    mask[np.where(mask <= threshold)] = 0  # set to black if less than threshold
    mask[np.where(mask > 0)] = 255
    mask = mask.astype('uint8')
    if algorithm == 'morphology':
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    elif algorithm == 'median':
        mask = cv2.medianBlur(mask, kernel_size)  # filter out noise in the mask
    return mask, {'minima': threshold}

def getExifDimensions(filename, crop=False):
    from maskgen import exif
    meta = exif.getexif(filename)
    heights= ['Cropped Image Height', 'AF Image Height', 'Image Height','Exif Image Height', ] if crop else ['Image Height','Exif Image Height']
    widths = ['Cropped Image Width', 'AF Image Width','Image Width','Exif Image Width', ] if crop else ['Image Width','Exif Image Width']
    height_selections = [(meta[h] if h in meta else None) for h in heights]
    width_selections =  [(meta[w] if w in meta else None) for w in widths ]
    if 'png:IHDR.width,height' in meta:
        try:
            w,h = [int(x.strip()) for x in meta['png:IHDR.width,height'].split(',')]
            height_selections.append(h)
            width_selections.append(w)
        except:
            pass
    return [(int(height_selections[p]), int(width_selections[p]))
            for p in range(len(width_selections)) if height_selections[p] is not None and width_selections[p] is not None]

def convertCompare(img1, img2, arguments=dict()):
    analysis = {}
    if 'Image Rotated' in arguments and arguments['Image Rotated'] == 'yes':
        if 'source filename' in arguments:
            orienation = exif.getOrientationFromExif((arguments['source filename']))
            analysis.update(exif.rotateAnalysis(orienation))
            img1 = exif.rotateAccordingToExif(img1, orienation,counter=True)
        else:
            # assumes crop, but this approach should be improved to use HOG comparisons
            # since some of these conversions occur with Raw images
            rotation, mask = __findRotation(img1, img2, [0, 90, 180, 270])
            analysis.update({'rotation': rotation})
            return 255 - mask, analysis
    if 'source filename' in arguments and img1.shape != img2.shape:
        # see if there is crop information in exif
        dims_crop = getExifDimensions(arguments['source filename'], crop=True)
        dims = getExifDimensions(arguments['source filename'], crop=False)
        if len(dims_crop) > 0 and len(dims) > 0 and dims_crop[0] != dims[0]:
            analysis['Crop'] = 'yes'
    if img1.shape != img2.shape:
        diff_shape = (int(img1.shape[0] - img2.shape[0]) / 2, int(img1.shape[1] - img2.shape[1]) / 2)
        #keep in mind that alterMask, used for composite generation, assumes 'crop' occurs first, followed
        # by final adjustments for size
        if 'location' not in arguments:
            diff_shape= (max(1,diff_shape[0]),max(1,diff_shape[1]))
        else:
            diff_shape = toIntTuple(arguments['location'])
        if getValue(arguments, 'Crop','yes') == 'no':
            new_img1 = img1
        else:
            new_img1 = img1[diff_shape[0]:-diff_shape[0], diff_shape[1]:-diff_shape[1]]
        new_img2 = cv2.resize(img2, (new_img1.shape[1], new_img1.shape[0]))
        if getValue(arguments, 'Crop', 'yes') == 'yes':
            analysis['location'] = str(diff_shape)
        mask, a = __diffMask(new_img1, new_img2, False, args=arguments)
    else:
        mask, a = __diffMask(img1, img2, False, args=arguments)

    analysis.update(a)
    return mask, analysis

def __composeMask(img1_wrapper, img2_wrapper, invert, arguments=dict(), alternativeFunction=None, convertFunction=None):
    """

    :param img1:
    :param img2:
    :param invert:
    :param arguments:
    :param alternativeFunction:
    :param convertFunction:
    :return:
    @type img1_wrapper: ImageWrapper
    @type img2_wrapper: ImageWrapper
    @type arguments: dict
    @rtype numpy.ndarray,dict
    """
    img1, img2 = __alignChannels(img1_wrapper,
                                 img2_wrapper,
                                 convertFunction=convertFunction)

    args = {}
    args.update(arguments)
    args['source filename'] = img1_wrapper.filename
    args['target filename'] = img2_wrapper.filename
    if alternativeFunction is not None:
        try:
            mask, analysis = alternativeFunction(img1, img2, arguments=args)
            removeValue(analysis, 'arguments.source filename')
            removeValue(analysis, 'arguments.target filename')
            if mask is not None:
                return mask if not invert else 255 - mask, analysis, None
        except ValueError as e:
            logging.getLogger('maskgen').error('Mask generation failure ' + str(e))
            logging.getLogger('maskgen').info('Arguments ' + str(arguments))
            mask = np.zeros(img1.shape, dtype=np.uint8)
            analysis = {}
            return abs(255 - mask).astype('uint8') if invert else mask, analysis, str(e)

    # rotate image two if possible to compare back to image one.
    # The mask is not perfect.
    mask = None
    error = None
    rotation = float(arguments['rotation']) if 'rotation' in arguments else 0.0
    analysis = {}
    if abs(rotation) > 0.0001:
        mask, analysis = __compareRotatedImage(rotation, img1, img2, arguments)
    if sum(img1.shape) > sum(img2.shape):
        mask, analysis = composeCropImageMask(img1, img2)
    if sum(img1.shape) < sum(img2.shape):
        mask, analysis = __composeExpandImageMask(img1, img2)
    if mask is None:
        try:
            if img1.shape != img2.shape and \
                            img1.shape[1] == img2.shape[0] and \
                            img1.shape[0] == img2.shape[1]:
                arguments['Image Rotated'] = 'yes'
                mask, analysis = convertCompare(img1, img2, arguments)
            else:
                mask, analysis = __diffMask(img1, img2, False, args=arguments)
        except Exception as e:
            logging.getLogger('maskgen').error('Mask generation failure ' + str(e))
            logging.getLogger('maskgen').info('Arguments ' + str(arguments))
            mask = np.zeros(img1.shape, dtype=np.uint8)
            analysis = {}
    return abs(255 - mask).astype('uint8') if invert else mask, analysis, error


def __alignShape(im, shape):
    x = min(shape[0], im.shape[0])
    y = min(shape[1], im.shape[1])
    z = np.zeros(shape)
    for d in range(min(shape[2], im.shape[2])):
        z[0:x, 0:y, d] = im[0:x, 0:y, d]
    return z


def __resize(img, dimensions):
    if img.shape[0] != dimensions[0]:
        diff = abs(img.shape[0] - dimensions[0])
        img = np.concatenate((np.zeros((diff / 2, img.shape[1])), img), axis=0)
        img = np.concatenate((img, np.zeros((diff - (diff / 2), img.shape[1]))), axis=0)
    if img.shape[1] != dimensions[1]:
        diff = abs(img.shape[1] - dimensions[1])
        img = np.concatenate((np.zeros((img.shape[0], diff / 2)), img), axis=1)
        img = np.concatenate((img, np.zeros((img.shape[0], diff - (diff / 2)))), axis=1)
    return img


def rotateImage(angle, pivot, img):
    padX = [img.shape[1] - pivot[1], pivot[1]]
    padY = [img.shape[0] - pivot[0], pivot[0]]
    imgP = np.pad(img, [padY, padX], 'constant')
    if abs(angle) % 90 == 0:
        imgR = np.rot90(imgP, int(angle / 90)).astype('uint8')
    else:
        try:
            imgR = np.asarray(Image.fromarray(imgP).rotate(angle))
        except:
            imgR = ndimage.rotate(imgP, angle, cval=0, reshape=False, mode='constant').astype('uint8')

    return imgR[padY[0]: -padY[1], padX[0]: -padX[1]]


def __localrotateImage(rotation, mask, img, expectedDims=None, cval=0):
    maskInverted = ImageWrapper(np.asarray(mask)).invert().to_array()
    maskInverted[maskInverted > 0] = 1
    targetDims = img.shape
    if expectedDims is not None:
        targetDims = expectedDims
    x0,y0,w,h = widthandheight(maskInverted)
    if w == 0 or h == 0:
        return img
    h = min(h+1, targetDims[0])
    w = min(w+1, targetDims[1])
    subImg = img[y0:(y0+h),x0:(x0+w)]
    center = (h /2, w / 2)
    M = cv2.getRotationMatrix2D(center, rotation, 1.0)
    rotatedSubMask = cv2.warpAffine(subImg*maskInverted[y0:(y0+h),x0:(x0+w)], M, (w,h),flags=cv2api.cv2api_delegate.inter_linear)
    rotatedMask = np.zeros(mask.shape)
    rotatedMask[y0:y0+h,x0:x0+w] = rotatedSubMask
    maskAltered = np.copy(mask)
    maskAltered[maskAltered > 0] = 1
    return (rotatedMask + img * maskAltered).astype('uint8')


def __rotateImage(rotation, img, expectedDims=None, cval=0):
    expectedDims = expectedDims if expectedDims is not None else (img.shape[0], img.shape[1])
    rotNorm = int(rotation / 90) if (rotation % 90) == 0 else None
    rotNorm = rotNorm if rotNorm is None or rotNorm >= 0 else (4 + rotNorm)
    npRotation = rotNorm is not None and img.shape == (expectedDims[1], expectedDims[0])
    if npRotation:
        res = np.rot90(img, rotNorm)
    else:
        res = ndimage.interpolation.rotate(img, rotation, cval=cval, reshape=(img.shape != expectedDims), order=0)
    if (res.shape[0],res.shape[1]) != expectedDims:
        res = cv2.resize(res,(expectedDims[1],expectedDims[0]))
    return res


def __compareRotatedImage(rotation, img1, img2, arguments):
    if rotation != 0:
        res = __rotateImage(rotation, img1, expectedDims=img2.shape, cval=img2[0, 0])
    else:
        res = img1
    mask, analysis = __composeExpandImageMask(res, img2) if res.shape != img2.shape else __diffMask(res,
                                                                                                    img2,
                                                                                                    False,
                                                                                                    args=arguments)
    if rotation != 0:
        res = __rotateImage(-rotation, mask, expectedDims=img1.shape, cval=255)
    else:
        res = mask
    return res, analysis


def __findRotation(img1, img2, range):
    best = 0
    r = None
    best_mask = None
    for rotation in range:
        res, analysis = __compareRotatedImage(rotation, img1, img2, {})
        c = np.sum(res)
        if c > best or best_mask is None:
            best = c
            best_mask = res
            r = rotation
    return r, best_mask


#      res = __resize(mask,(max(img2.shape[0],img1.shape[0]), max(img2.shape[1],img1.shape[1])))
#      res[res<0.00001] = 0
#      res[res>0] = 255
#      # now crop out the rotation difference, to make sure the original image is not modified
#      if img1.shape != res.shape:
#        diff = (res.shape[0]-img1.shape[0], res.shape[1]-img1.shape[1])
#        diff = (diff[0] if diff[0] > 0 else 0, diff[1] if diff[1] > 0 else 0)
#        res = res[diff[0]/2:res.shape[0]-((diff[0]/2) -diff[0]),diff[1]/2:res.shape[1]-((diff[1]/2) - diff[1])]

def extractAlpha(rawimg1, rawimg2):
    """
    If rawimg2 has an alpha channel, then the pixels then the high alpha value is the pixels that did not change
    :param rawimg1:
    :param rawimg2:
    :return:
    """
    img2_array = rawimg2.to_array()
    img1_array = rawimg1.to_array()
    ii16 = np.iinfo(np.uint16)
    if len(img2_array.shape) == 3 and img2_array.shape[2] == 4:
        img2_array = img2_array[:, :, 3]
    if len(img2_array.shape) == 2:
        all = np.zeros((img2_array.shape[0], img2_array.shape[1])).astype('uint16')
        all[img2_array == 0] = ii16.max
        return np.zeros((img1_array.shape[0], img1_array.shape[1])).astype('uint16'), all
    return rawimg1.to_16BitGray().to_array(), rawimg2.to_16BitGray().to_array()


def convert16bitcolor(rawimg1, rawimg2):
    return rawimg1.to_array().astype('int16'), rawimg2.to_array().astype('int16')

def __alignChannels(rawimg1, rawimg2, convertFunction=None):
    """

    :param rawimg1:
    :param rawimg2:
    :param equalize_colors:
    :return:
    @type rawimg1: ImageWrapper
    @type rawimg2: ImageWrapper
    """
    if convertFunction is not None:
        return convertFunction(rawimg1, rawimg2)
    return rawimg1.to_16BitGray().to_array(), rawimg2.to_16BitGray().to_array()


def __findBestMatch(big, small):
    """ Return a tuple describing the bounding box (xl,xh,yl,yh) with the most
        likely match to the small image.
    """
    if len(small.shape) == 3 and len(big.shape) == 3 and \
                    small.shape[2] == 4 and big.shape[2] == 3:
        newsmall = np.zeros((small.shape[0], small.shape[1], 3))
        newsmall[:, :, :] = small[:, :, 0:3]
        small = newsmall
    if np.any(np.asarray([(x[1] - x[0]) for x in zip(small.shape, big.shape)]) < 0):
        return None
    result = cv2.matchTemplate(big.astype('float32'), small.astype('float32'), cv2api.cv2api_delegate.tm_sqdiff_normed)
    mn, _, mnLoc, _ = cv2.minMaxLoc(result)
    result_tuple = (mnLoc[1], mnLoc[0], mnLoc[1] + small.shape[0], mnLoc[0] + small.shape[1])
    if result_tuple[2] > big.shape[0] or result_tuple[3] > big.shape[1]:
        return None
    return result_tuple


def bm(X, patch):
    from sklearn.metrics import mean_absolute_error
    bv = 999999.0
    bp = (0, 0)
    for i in range(X.shape[0] - patch.shape[0]):
        for j in range(X.shape[1] - patch.shape[1]):
            v = mean_absolute_error(X[i:i + patch.shape[0], j:j + patch.shape[1]], patch)
            if v < bv:
                bv = v
                bp = (i, j)
    return bp, bv


def composeCropImageMask(img1, img2, location=None):
    """ Return a masking where img1 is bigger than img2 and
        img2 is likely a crop of img1.
        images are 16 bit unnsigned or floating point.
        @return change mask aligned to in img1 dimensions, dictionary of analysis keys
        @type img1: np.array
        @type img2: np.array
    """
    analysis = {}
    analysis['location'] = '(0,0)'
    if location is not None:
        matched_tuple = (location[0],location[1],img2.shape[0]+location[0],img2.shape[1]+location[1])
    else:
        matched_tuple = __findBestMatch(img1, img2)
    if matched_tuple is not None:
        diffIm = np.zeros(img1.shape).astype(img1.dtype)
        diffIm[matched_tuple[0]:matched_tuple[2], matched_tuple[1]:matched_tuple[3]] = img2
        analysis['location'] = str((int(matched_tuple[0]), int(matched_tuple[1])))
        dst = np.abs(img1 - diffIm)
        gray_image = np.zeros(img1.shape).astype('uint8')
        gray_image[dst > 0.0001] = 255
        mask = gray_image
        for k, v in img_analytics(img1, diffIm, mask=mask).iteritems():
            analysis[k] = v
    else:
        mask = np.ones(img1.shape) * 255
    return abs(255 - mask).astype('uint8'), analysis


def composeCloneMask(changemask, startimage, finalimage):
    """

    :param changemask:
    :param startimage:
    :param finalimage:
    :return:
    @type changemask: ImageWrapper
    @type startimage: ImageWrapper
    @type finalimage: ImageWrapper
    """
    mask = np.asarray(changemask.invert())
    start_image_array = np.array(startimage)
    final_image_array = np.array(finalimage)
    newmask = np.zeros(start_image_array.shape).astype('uint8')
    try:
        contours, hierarchy = cv2api.findContours(np.copy(mask), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for i in range(0, len(contours)):
            try:
                cnt = contours[i]
                x, y, w, h = cv2.boundingRect(cnt)
                if w <= 2 or h <= 2:
                    continue
                final_image_subarray = final_image_array[y:y + h, x:x + w]
                for i in range(final_image_subarray.shape[2]):
                    final_image_subarray[:, :, i] = final_image_subarray[:, :, i] * (mask[y:y + h, x:x + w] / 255)
                matched_tuple = __findBestMatch(start_image_array, final_image_subarray)
                if matched_tuple is not None:
                    newmask[matched_tuple[0]:matched_tuple[2], matched_tuple[1]:matched_tuple[3]] = 255
            except Exception as e:
                logging.getLogger('maskgen').warning('Failed to compose clone mask: ' + str(e))
                continue
    except Exception as e:
        return changemask.to_array()
    return newmask


def __composeExpandImageMask(img1, img2):
    """ Return a masking where img1 is smaller than img2 and
        img2 contains img1.
    """
    matched_tuple = __findBestMatch(img2, img1)
    analysis = {}
    if matched_tuple is not None:
        diffIm = img2[matched_tuple[0]:matched_tuple[2], matched_tuple[1]:matched_tuple[3]]
        dst = np.abs(img1 - diffIm)
        analysis['location'] = str((int(matched_tuple[0]), int(matched_tuple[1])))
        gray_image = np.zeros(img1.shape).astype('uint8')
        gray_image[dst > 0.0001] = 255
        mask = gray_image
        for k, v in img_analytics(img1, diffIm, mask=mask).iteritems():
            analysis[k] = v
    else:
        mask = np.ones(img1.shape) * 255
    return abs(255 - mask).astype('uint8'), analysis


def __colorPSNR(z1, z2, size=None):
    if size == 0:
        return 0.0
    d = (z1 - z2) ** 2
    sse = np.sum(d)
    size = float(reduce(lambda x, y: x * y, d.shape)) if size is None else float(size)
    mse = float(sse) / size
    return 0.0 if mse == 0.0 else 20.0 * math.log10(255.0 / math.sqrt(mse))


def sizeDiff(z1, z2):
    """
       z1 and z2 are expected to be PIL images
    """
    # size is inverted due to Image's opposite of numpy arrays
    return str((int(z2.size[1] - z1.size[1]), int(z2.size[0] - z1.size[0])))


def invertMask(mask):
    return mask.invert()


def convertToMask(im):
    """
      Takes an image and produce a mask where all black areas are white
    """
    return im.to_mask()


def __checkInterpolation(val):
    validVals = ['nearest', 'lanczos', 'bilinear', 'bicubic' or 'cubic']
    return val if val in validVals else 'nearest'


def applyMask(image, mask, value=0):
    if mask.shape != image.shape:
        mask = cv2.resize(mask, (image.shape[1], image.shape[0]))
    image = np.copy(image)
    image[mask == 0] = value
    return image


def carveMask(image, mask, expectedSize):
    """
    Trim a mask after seam carving
    :param image:
    :param mask:
    :param expectedSize:
    :return:
    """
    newimage = np.zeros(expectedSize).astype('uint8')
    if expectedSize[0] == mask.shape[0]:
        for x in range(expectedSize[0]):
            topaste = image[x, mask[x, :] == 255]
            if (len(topaste)) <= newimage.shape[1]:
                newimage[x, 0:len(topaste)] = topaste
            else:
                newimage[x, :] = topaste[0:len(topaste)]
    elif expectedSize[1] == mask.shape[1]:
        for y in range(expectedSize[1]):
            topaste = image[mask[:, y] == 255, y]
            if (len(topaste)) <= newimage.shape[0]:
                newimage[0:len(topaste), y] = topaste
            else:
                newimage[:, y] = topaste[0:len(topaste)]
    else:
        return applyMask(image, mask)
    return newimage


def alterMask(compositeMask,
              edgeMask,
              rotation=0.0,
              targetShape=(0, 0),
              interpolation='nearest',
              location=(0, 0),
              transformMatrix=None,
              flip=None,
              crop=False,
              cut=False):
    res = compositeMask
    # rotation may change the shape
    # transforms typical are created for local operations (not entire image)
    if location != (0, 0) or crop:
        if targetShape != res.shape:
            # inverse crop
            newRes = np.zeros(targetShape).astype('uint8')
            upperBound = (min(res.shape[0] + location[0], newRes.shape[0]),
                          min(res.shape[1] + location[1], newRes.shape[0]))
            newRes[location[0]:upperBound[0], location[1]:upperBound[1]] = res[0:(upperBound[0] - location[0]),
                                                                           0:(upperBound[1] - location[1])]
            res = newRes
        else:
            upperBound = (min(res.shape[0], targetShape[0] + location[0]),
                          min(res.shape[1], targetShape[1] + location[1]))
            res = res[location[0]:upperBound[0], location[1]:upperBound[1]]
    if transformMatrix is not None and not cut and flip is None:
        res = applyTransformToComposite(compositeMask, edgeMask, transformMatrix)
    elif abs(rotation) > 0.001:
        if targetShape != res.shape or abs(rotation) % 90 < 0.001:
            res = __rotateImage(rotation, compositeMask,
                                expectedDims=targetShape,
                                cval=0)
        else:
            res = applyRotateToComposite(rotation, res,
                                         edgeMask,
                                         targetShape)
    # if transform matrix provided and alternate path is taken above
    if flip is not None:
        res = applyFlipComposite(res, edgeMask, flip)
    if cut:
        res = applyMask(res, edgeMask)
    if targetShape != res.shape:
        res = applyResizeComposite(res, targetShape)
    return res


def alterReverseMask(donorMask, edgeMask, rotation=0.0, location=(0, 0),
                     transformMatrix=None, flip=None, crop=False, cut=False, targetShape=None):
    res = donorMask
    # if we are cutting, then do not want to use the edge mask as mask for transformation.
    # see the cut section below, where the transform occurs directly on the mask
    # this  occurs in donor cases
    if ((location != (0, 0) or crop) and not cut):
        if targetShape != donorMask.shape:
            # inverse crop
            upperBound = (min(res.shape[0], targetShape[0] + location[0]),
                          min(res.shape[1], targetShape[1] + location[1]))
            res = res[location[0]:upperBound[0], location[1]:upperBound[1]]
        else:
            newRes = np.zeros(targetShape).astype('uint8')
            upperBound = (res.shape[0] + location[0], res.shape[1] + location[1])
            newRes[location[0]:upperBound[0], location[1]:upperBound[1]] = res[0:(upperBound[0] - location[0]),
                                                                           0:(upperBound[1] - location[1])]
            res = newRes
    if transformMatrix is not None and not cut and flip is None:
        res = applyTransform(res, mask=edgeMask, transform_matrix=transformMatrix, invert=True,
                             returnRaw=False)
    elif abs(rotation) > 0.001:
        res = __rotateImage(-rotation, res, expectedDims=targetShape, cval=0)
    elif flip is not None:
        res = applyFlipComposite(res, edgeMask, flip)
    if cut:
        # res is the donor mask
        # edgeMask may be the overriding mask from a PasteSplice, thus in the same shape
        # The transfrom will convert to the target mask size of the donor path.
        res = applyMask(res, edgeMask)
        if transformMatrix is not None:
            res = cv2.warpPerspective(res, transformMatrix, (targetShape[1], targetShape[0]),
                                      flags=cv2.WARP_INVERSE_MAP,
                                      borderMode=cv2.BORDER_CONSTANT, borderValue=0).astype('uint8')
    # need to use target size since the expected does ot align with the donor paths.
    if targetShape != res.shape:
        res = cv2.resize(res, (targetShape[1], targetShape[0]))
    return res


def __toMask(im):
    """
    Performs same functionality as convertToMask, but takes and returns np array
    """
    if len(im.shape) < 3:
        return im
    imGray = cv2.cvtColor(im, cv2.COLOR_RGB2GRAY)
    gray_image = np.ones(imGray.shape).astype('uint8')
    gray_image[imGray < 255] = 0
    gray_image *= 255
    if im.shape[2] == 4:
        gray_image[im[:, :, 3] == 0] = 255
    return gray_image


def mergeColorMask(compositeMaskArray, newMaskArray):
    matches = np.any(newMaskArray != [255, 255, 255], axis=2)
    compositeMaskArray[matches] = newMaskArray[matches]
    return compositeMaskArray


def mergeMask(compositeMask, newMask, level=0):
    if compositeMask.shape != newMask.shape:
        compositeMask = cv2.resize(compositeMask, (newMask.shape[1], newMask.shape[0]))
        newMask = ImageWrapper(newMask).to_mask().to_array()
    else:
        compositeMask = np.copy(compositeMask)
    compositeMask[newMask == 0] = level
    return compositeMask


def ssim(X, Y, MASK, **kwargs):
    from scipy.ndimage import gaussian_filter

    K1 = kwargs.pop('K1', 0.01)
    R = kwargs.pop('R', 255)
    K2 = kwargs.pop('K2', 0.03)
    sigma = kwargs.pop('sigma', 1.5)

    X = X.astype(np.float64)
    Y = Y.astype(np.float64)
    win_size = 1

    cov_norm = 1.0  # population covariance to match Wang et. al. 2004

    filter_func = gaussian_filter
    filter_args = {'sigma': sigma}

    # compute (weighted) means
    ux = filter_func(X, **filter_args)
    uy = filter_func(Y, **filter_args)

    # compute (weighted) variances and covariances
    uxx = filter_func(X * X, **filter_args)
    uyy = filter_func(Y * Y, **filter_args)
    uxy = filter_func(X * Y, **filter_args)
    vx = cov_norm * (uxx - ux * ux)
    vy = cov_norm * (uyy - uy * uy)
    vxy = cov_norm * (uxy - ux * uy)

    C1 = (K1 * R) ** 2
    C2 = (K2 * R) ** 2

    A1, A2, B1, B2 = ((2 * ux * uy + C1,
                       2 * vxy + C2,
                       ux ** 2 + uy ** 2 + C1,
                       vx + vy + C2))
    D = B1 * B2
    S = ((A1 * A2) / D) * MASK

    # compute (weighted) mean of ssim
    return S.mean()


def img_analytics(z1, z2, mask=None):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        result = {'psnr': __colorPSNR(z1, z2)}
        if mask is not None:
            mask = np.copy(mask)
            mask[mask > 0] = 1
            result.update({'local psnr': __colorPSNR(z1 * mask, z2 * mask, size=sumMask(mask))})
        return result


def __diffMask(img1, img2, invert, args=None):
    itype = np.iinfo(img1.dtype)
    dst = np.abs(np.subtract(img1.astype('int32'), img2.astype('int32')))
    gray_image = np.zeros(img1.shape).astype('uint8')
    difference = float(args['tolerance']) if args is not None and 'tolerance' in args else 0.0001
    difference = difference * (itype.max - itype.min)
    gray_image[dst > difference] = 255
    analysis = img_analytics(img1, img2, mask=gray_image)
    return (gray_image if invert else (255 - gray_image)), analysis

def coordsFromString(value):
    import re
    value = re.sub('[\(\)\,]', ' ', value)
    vals = [int(float(v)) for v in value.split(' ') if v != ' ' and v != '']
    return tuple(vals)


def fixTransparency(img):
    return img.apply_transparency()


def dictDeepUpdate(aDictionary, aPartialDictionary):
    for k, v in aPartialDictionary.iteritems():
        if k in aDictionary and type(v) == dict:
            dictDeepUpdate(aDictionary[k], v)
        else:
            aDictionary[k] = v

def grayToRGB(frame):
    """
    project gray into Green
    """
    result = np.zeros((frame.shape[0], frame.shape[1], 3))
    if len(frame.shape) == 2:
        result[:, :, 1] = frame
    else:
        summary = np.zeros((frame.shape[0], frame.shape[1]))
        for d in range(frame.shape[2]):
            summary[:, :] += frame[:, :, d]
        summary[summary > 0] = 255
        result[:, :, 1] = summary
    return result.astype('uint8')


def composeVideoMaskName(maskprefix, starttime, suffix):
    """
    :param maskprefix:
    :param starttime:
    :param suffix:
    :return: A mask file name using the provided components
    """
    if maskprefix.endswith('_mask_' + str(starttime)):
        return maskprefix + '.' + suffix
    return maskprefix + '_mask_' + str(starttime) + '.' + suffix


def convertToVideo(filename, preferences=None, start_frame=None, start_time=0):
    suffix = '.' + preferredSuffix(preferences=preferences)
    fn = os.path.splitext(filename)[0] + (str(start_frame) if start_frame is not None else '') + suffix
    if os.path.exists(fn):
        if os.stat(filename).st_mtime < os.stat(fn).st_mtime:
            return fn
        else:
            os.remove(fn)
    reader = GrayBlockReader(filename,
                             convert=True,
                             preferences=preferences,
                             start_frame=start_frame,
                             start_time=start_time)
    while True:
        mask = reader.read()
        if mask is None:
            break
    fn = reader.writer.filename
    return fn


executions = {}


def cancel_execute(worker_func):
    if worker_func in executions:
        executions[worker_func].cancel()


def execute_every(interval, worker_func, start=True, **kwargs):
    executions[worker_func] = threading.Timer(
        interval,
        execute_every, [interval, worker_func, False], kwargs)
    executions[worker_func].start()
    if not start:
        worker_func(**kwargs)


class GrayBlockFrameFirstLayout():

    name = 'framefirst'

    @staticmethod
    def is_end(reader):
        return reader.pos >= reader.dset.shape[0]

    @staticmethod
    def count(reader):
        return reader.dset.shape[0]

    @staticmethod
    def get_frame(reader):
        return reader.dset[reader.pos]

    @staticmethod
    def initial_shape(shape, size = None):
        return (size,) + shape

    @staticmethod
    def resize(shape, writer):
        if writer.dset.shape[0] < (writer.pos + 1):
            writer.dset.resize((writer.pos + 1,) + writer.dset.shape[1:])

    @staticmethod
    def set(writer,mask):
            writer.dset[ writer.pos] = mask

class GrayBlockFrameLastLayout():

    name = 'framelast'

    @staticmethod
    def is_end(reader):
        return reader.pos >= reader.dset.shape[-1]

    @staticmethod
    def count(reader):
        return reader.dset.shape[-1]

    @staticmethod
    def get_frame(reader):
        return reader.dset[:, :, reader.pos]

    @staticmethod
    def initial_shape(shape, size=None):
        return (shape)[:-1] + (size,)

    @staticmethod
    def resize(shape, writer):
        if writer.dset.shape[-1] < (writer.pos + 1):
            writer.dset.resize((shape)[:-1] + (writer.pos + 1,))

    @staticmethod
    def set(writer,mask):
        if len(writer.dset.shape) == 2:
            writer.dset[:, :, writer.pos] = mask
        else:
            writer.dset[:, :, :, writer.pos] = mask



class GrayBlockReader:

    def __init__(self, filename,
                 convert=False,
                 preferences=None,
                 start_time=0,
                 start_frame=None,
                 end_frame=None):
        import h5py
        self.writer = None

        self.start_frame = start_frame
        self.start_time = start_time
        self.preferences = preferences
        self.filename = filename
        self.h_file = h5py.File(filename, 'r')
        grp_names = self.h_file.keys()
        if 'masks' in grp_names:
            self.grps = ['masks']
            self.setter = OldFormatGroupSetter()
        else:
            self.setter = NewFormatGroupSetter()
            self.grps = [str(x) for x in sorted([int(x) for x in grp_names])]
        # group selection
        self.grp_pos = 0
        # frame selection in group (relative to start of group)
        self.pos = 0
        # the smart numpy array
        self.dset = None
        # where to stop
        self.end_frame = end_frame
        self.fps = self.h_file.attrs['fps']
        self.mask_format = MASKFORMATS[
        self.h_file.attrs['mask_format'] if 'mask_format' in self.h_file.attrs else GrayBlockFrameFirstLayout.name]
        self.setter.set_group(self, start_time=start_time, start_frame=start_frame, end_frame=end_frame)
        self.convert = convert
        self.writer = GrayFrameWriter(os.path.splitext(filename)[0],
                                      self.fps,
                                      preferences=preferences) if self.convert else DummyWriter()
    def create_writer(self):
        """
        :return:
        @rtype: GrayBlockWriter
        """
        import time
        dir = os.path.dirname(self.filename)
        prefix = os.path.join(dir,os.path.basename(self.h_file.attrs['prefix'])) if 'prefix' in self.h_file.attrs else os.path.splitext(self.filename)[0][:48]
        return GrayBlockWriter(prefix + str(time.clock()), self.fps)

    def set_group(self, start_frame=None, start_time=1, end_frame=None):
        self.setter.set_group(self, start_frame=start_frame,start_time=start_time, end_frame=end_frame)

    def current_frame_time(self):
        return self.start_time + (self.pos * (1000 / self.fps))

    def current_frame(self):
        return self.start_frame + self.pos

    def read(self):
        if self.dset is None:
            return None
        if self.end_frame is not None and self.current_frame() == self.end_frame + 1:
            return None
        if self.mask_format.is_end(self):
            self.grp_pos+=1
            if self.grp_pos < len(self.grps):
                self.setter.select_group(self, self.grp_pos)
            else:
                self.dset = None
                return None
        mask = self.mask_format.get_frame(self)
        mask = mask.astype('uint8')
        self.writer.write(mask, self.start_frame + self.pos, self.current_frame_time())
        self.pos += 1
        return mask

    def release(self):
        pass

    def close(self):
        self.h_file.close()
        if self.writer is not None:
            self.writer.close()

MASKFORMATS = {GrayBlockFrameFirstLayout.name:GrayBlockFrameFirstLayout(),
               GrayBlockFrameLastLayout.name:GrayBlockFrameLastLayout()}


class GrayBlockReaderManager:
    def __init__(self, reader_type= GrayBlockReader):
        self.reader_type = reader_type
        self.reader = None
        self.filename = None

    def create_reader(self, filename,
                      start_frame=None,
                      start_time=0,
                      end_frame=None):
        """
        :param filename:
        :param start_frame:
        :param start_time:
        :param end_frame: optional stopping point
        :return:
        @type filename: str
        @rtype: GrayBlockReader
        """

        if filename == self.filename:
            self.reader.set_group(start_frame=start_frame,
                                  start_time=start_time,
                                  end_frame=end_frame)
        else:
            if self.reader is not None:
                self.reader.close()
            self.filename = filename
            self.reader = self.reader_type(filename,
                               start_frame=start_frame,
                               start_time=start_time,
                               end_frame=end_frame)



        return self.reader

    def close(self):
        if self.reader is not None:
            self.reader.close()
            self.reader = None

class GrayBlockWriterManager:

    def __init__(self):
        self.writer = None

    def create_writer(self, reader):
        """
        :param reader:
        :return:
        @type reader: GrayBlockReader
        @rtype: GrayBlockWriter
        """
        if self.writer is not None:
            return self.writer
        self.writer=  reader.create_writer()
        return self.writer

    def close(self):
        if self.writer is not None:
            self.writer.close()
            self.writer = None

class NewFormatGroupSetter:
    """
    Multiple Mask Segment per HDF5 File, one in each group.
    """

    @staticmethod
    def set_group(reader, start_frame=None, start_time=1,end_frame=None):
        """
        :param start_frame:
        :param start_time:
        :return:
        @type reader: GrayBlockReader
        """
        grp_pos = 0
        if start_frame is not None:
            pos = len([x for x in reader.grps if int(x) <= start_frame]) - 1
            grp_pos = pos if pos > 0 else grp_pos
        NewFormatGroupSetter.select_group(reader,
                                          grp_pos,
                                          start_frame=start_frame,
                                          start_time=start_time,
                                          end_frame=end_frame)

    @staticmethod
    def select_group(reader,
                     grp_pos,
                     start_frame=None,
                     start_time=0,
                     end_frame=None):
        """

        :param reader:
        :param grp_no:
        :param start_frame:
        :param start_time:
        :param end_frame: determine end frame
        :return:
        """
        reader.grp_pos = grp_pos

        reader.current_group = reader.h_file.get(reader.grps[grp_pos])
        reader.dset = reader.current_group.get('masks')
        reader.start_time = reader.current_group.attrs[
            'start_time'] if 'start_time' in reader.current_group.attrs else start_time
        reader.start_frame = reader.current_group.attrs[
            'start_frame'] if 'start_frame' in reader.current_group.attrs else start_frame
        end_frame = reader.current_group.attrs[
            'end_frame'] if 'end_frame' in reader.current_group.attrs and end_frame is None else end_frame
        reader.end_frame = end_frame if end_frame is not None else None
        reader.pos = 0 if start_frame is None else reader.start_frame - start_frame

class OldFormatGroupSetter:
    """
    One Mask Segment per HDF5 File.
    """

    @staticmethod
    def set_group(reader, start_frame=None, start_time=0, end_frame=None):
        """
        :param start_frame:
        :param start_time:
        :return:
        @type reader: GrayBlockReader
        """
        reader.current_group = reader.h_file.get('masks')
        reader.dset = reader.current_group.get('masks')
        reader.start_time = reader.h_file.attrs[
            'start_time'] if 'start_time' in reader.h_file.attrs else start_time
        reader.start_frame = reader.h_file.attrs[
            'start_frame'] if 'start_frame' in reader.h_file.attrs else start_frame
        reader.pos = 0 if start_frame is None else reader.start_frame - start_frame

    @staticmethod
    def select_group(reader, grp_pos, start_frame=None, start_time=0,end_frame=None):
        OldFormatGroupSetter.set_group(reader,start_frame=start_frame,start_time=start_time)

def compose_overlay_name(target_file="", link = tuple()):
    path_tuple = os.path.split(target_file)
    return os.path.join(path_tuple[0], path_tuple[1] + str(hash(link))[:5] + '_overlay.' + preferredSuffix())

class GrayBlockOverlayGenerator:

    def __init__(self, locator, segments = [], target_file = None, output_file = ""):
        from video_tools import getMaskSetForEntireVideo, get_frames_from_segment

        self.target_file = target_file
        self.output_file = output_file

        segments = [segment for segment in segments if segment.media_type == 'video' and segment.filename != None]
        self.segments = sorted(segments, key=lambda segment: segment.startframe)
        self.segment_index = 0
        self.segment = segments[self.segment_index]
        self.readerManager = GrayBlockReaderManager()
        self.reader = self.readerManager.create_reader(
            filename=self.segment.filename,
            start_time=self.segment.starttime,
            start_frame=self.segment.startframe,
            end_frame=self.segment.endframe)
        self.overlay_mask_name = os.path.join(os.path.split(self.segment.filename)[0], '_overlay')
        self.writer = GrayFrameOverlayWriter(
            mask_prefix=self.overlay_mask_name,
            fps=self.reader.fps)

        self.last_frame = get_frames_from_segment(getMaskSetForEntireVideo(locator)[0])

    def updateSegment(self):
        self.segment_index += 1
        self.segment = self.segments[self.segment_index]
        self.reader = self.readerManager.create_reader(
            filename=self.segment.filename,
            start_time=self.segment.starttime,
            start_frame=self.segment.startframe,
            end_frame=self.segment.endframe)

    def generate(self):
        while self.writer.lastPos < self.last_frame:
            frame_time = self.reader.current_frame_time()
            frame_count = self.reader.current_frame()
            mask = self.reader.read()
            if mask is None:
                if self.segment_index + 1 < len(self.segments):
                    self.updateSegment()
                else:
                    frame_count = self.last_frame #write blanks for the rest

            self.writer.write(mask, frame_count, frame_time)
        self.writer.close()
        self.readerManager.close()
        ffmpeg_overlay(self.target_file, self.writer.filename, self.output_file)
        try:
            os.remove(self.writer.filename) #clean up the mask file, leave the finished overlay
        except OSError:
            pass

class DummyWriter:
    def write(self, mask, mask_number, mask_time):
        pass

    def close(self):
        pass


class GrayBlockWriter:
    """
      Write Gray scale (Mask) images to a compressed block file
    """

    def __init__(self, mask_prefix, fps, layout=GrayBlockFrameFirstLayout()):
        self.fps = fps
        self.dset = None
        self.pos = 0
        self.h_file = None
        self.suffix = 'hdf5'
        self.filename = None
        self.mask_prefix = mask_prefix
        self.mask_format = layout
        self.last_frame = 1
        self.last_time = 0
        self.current_group = None

    def write(self, mask, mask_time, frame_number):
        import h5py
        if self.current_group is not None and frame_number - self.last_frame > 1:
            grp = self.current_group
            grp.attrs['end_time'] = self.last_time
            grp.attrs['end_frame'] = self.last_frame
            self.current_group = None

        if self.h_file is None:
            self.filename = composeVideoMaskName(self.mask_prefix, mask_time, self.suffix)
            logging.getLogger('maskgen').info('Writing to ' + self.filename)
            if os.path.exists(self.filename):
                os.remove(self.filename)
            self.h_file = h5py.File(self.filename, 'w')
            self.h_file.attrs['fps'] = self.fps
            self.h_file.attrs['prefix'] = os.path.basename(self.mask_prefix)
            self.h_file.attrs['mask_format'] = self.mask_format.name
            self.current_group = None

        if self.current_group is None:
            self.current_group = self.h_file.create_group(str(frame_number))
            grp = self.current_group
            grp.attrs['start_time'] = mask_time
            grp.attrs['start_frame'] = frame_number
            self.dset = grp.create_dataset("masks",
                                                self.mask_format.initial_shape(mask.shape, size=10),
                                                compression="gzip",
                                                chunks=True,
                                                maxshape=self.mask_format.initial_shape(mask.shape))
            self.pos = 0

        self.mask_format.resize(mask.shape, self)
        self.last_frame = frame_number
        self.last_time = mask_time
        self.mask_format.set(self, mask)
        self.pos += 1

    def get_file_name(self):
        return self.filename

    def close(self):
        self.release()

    def release(self):
        if self.current_group is not None:
            self.current_group.attrs['end_time'] = self.last_time
            self.current_group.attrs['end_frame'] = self.last_frame
        self.current_group = None
        self.dset = None
        if self.h_file is not None:
            self.h_file.close()
        self.h_file = None



def preferredSuffix(preferences=None):
    import sys
    default_suffix = 'm4v'
    if sys.platform.startswith('win'):
        default_suffix = 'avi'
    if sys.platform.startswith('linux'):
        default_suffix = 'avi'
    if preferences is not None:
        t_suffix = getValue(preferences,'vid_suffix')
        default_suffix = t_suffix if t_suffix is not None else default_suffix
    return default_suffix

class GrayBlockFactory:
    """
    Either build the Writer or the Validator
    """
    def __init__(self, jt_mask=None):
        self.jt_mask = jt_mask
        self.product = None

    def __call__(self, name, fps):
        self.product = GrayBlockWriter(mask_prefix=name, fps=fps) if self.jt_mask is None else GrayBlockValidator(jt_mask_file=self.jt_mask)
        return self.product

class GrayBlockValidator:
    """
    Compare frames of two video masks to see if one is valid.
    """
    def __init__(self, jt_mask_file):
        self.filename = jt_mask_file
        self.failed_frames = []
        self.manager = GrayBlockReaderManager()
        self.manager.create_reader(jt_mask_file)

    def compareMask(self, mask, inputmask, cur_frame):
        inputmask = np.invert(inputmask)
        inputmask[inputmask > 0] = 1
        mask = np.invert(mask)
        mask[mask > 0] = 1
        intersection = inputmask * mask
        difference = np.clip(mask - inputmask, 0, 1).astype(dtype='uint8')
        union = np.clip(intersection + difference, 0, 1).astype(dtype='uint8')
        masksize = float(np.sum(mask))
        unionsize = float(np.sum(union))
        mismatch = abs(masksize-unionsize)/masksize
        if mismatch > .05:
            self.failed_frames.append(cur_frame)

    def write(self, mask, mask_time, frame_number):
        while(self.manager.reader.current_frame() < frame_number):
            self.manager.reader.read() #ffwd to where we want to be
        if self.manager.reader.current_frame() == frame_number:
            jt_mask = self.manager.reader.read()
            if jt_mask is not None:
                self.compareMask(inputmask=mask, mask=jt_mask, cur_frame=frame_number)

    def get_file_name(self):
        return self.filename


class GrayFrameWriter:
    """
    Write Gray scale (Mask) video images
    """
    capOut = None
    codec = 'AVC1'
    suffix = 'm4v'
    fourcc = None
    filename = None
    fps = 0
    mask_prefix = None

    def __init__(self, mask_prefix, fps, preferences=None):
        import sys
        self.fps = fps
        self.mask_prefix = mask_prefix
        self.suffix = preferredSuffix(preferences=preferences)
        t_codec = None
        if preferences is not None and 'vid_codec' in preferences:
            t_codec = preferences['vid_codec']
        if t_codec is None and sys.platform.startswith('win'):
            self.codec = 'XVID'
        elif t_codec is None and sys.platform.startswith('linux'):
            self.codec = 'XVID'
        elif t_codec is not None:
            self.codec = str(t_codec)
        self.fourcc = cv2api.cv2api_delegate.get_fourcc(self.codec) if self.codec is not 'raw' else 0

    def write(self, mask, mask_number, mask_time):
        if self.capOut is None:
            self.filename = composeVideoMaskName(self.mask_prefix, mask_time, self.suffix)
            logging.getLogger('maskgen').info('writing using fourcc ' + str(self.fourcc))
            if os.path.exists(unicode(os.path.abspath(self.filename))):
                os.remove(unicode(os.path.abspath(self.filename)))
            self.capOut = cv2.VideoWriter(unicode(os.path.abspath(self.filename)),
                                          self.fourcc,
                                          self.fps,
                                          (mask.shape[1], mask.shape[0]),
                                          len(mask.shape) > 2 and mask.shape[2] > 1)
        if cv2.__version__.startswith('2.4.11'):
            mask = grayToRGB(mask)
        self.capOut.write(mask)

    def close(self):
        if self.capOut is not None:
            self.capOut.release()
        self.capOut = None

    def release(self):
        self.close()

class GrayFrameOverlayWriter(GrayFrameWriter):

    def __init__(self, mask_prefix = '', fps = 30/1, preferences = None):
        GrayFrameWriter.__init__(self, mask_prefix=mask_prefix, fps=fps, preferences = preferences)
        self.lastPos = 0
        self.blankMask = None

    def write(self, mask, mask_number, mask_time):

        if self.blankMask is None:
            self.blankMask = np.ones((mask.shape[0], mask.shape[1]), dtype=np.uint8) * 255

        frames_to_write = mask_number - self.lastPos #write all the frames up to and including the mask frame

        for i in range(1,frames_to_write+1):
            frame_num = self.lastPos + i
            mask_time = frame_num * 1000.0 / self.fps #refigure time for the frame we actually write
            GrayFrameWriter.write(self,
                mask=mask if frame_num == mask_number and mask is not None else self.blankMask,
                mask_number=frame_num,
                mask_time=mask_time)

        self.lastPos = mask_number

def widthandheight(img):
    a = np.where(img != 0)
    if len(a[0]) == 0:
        return 0, 0, 0, 0
    bbox = np.min(a[0]), np.max(a[0]), np.min(a[1]), np.max(a[1])
    h, w = bbox[1] - bbox[0], bbox[3] - bbox[2]
    return bbox[2], bbox[0], w, h


def place_in_image(mask, image_to_place, image_to_cover, placement_center, rect=None):
    x, y, w, h = widthandheight(mask)
    if rect:
        if w > rect[2]:
            x = x + (w - rect[2]) / 2
            w = rect[2]
        if h > rect[3]:
            y = y + (h - rect[3]) / 2
            h = rect[3]
    w += w % 2
    h += h % 2
    x_offset = int(placement_center[0]) - int(math.floor(w / 2))
    y_offset = int(placement_center[1]) - int(math.floor(h / 2))
    if y_offset < 0:
        return None
    if x_offset < 0:
        return None
    image_to_cover = np.copy(image_to_cover)
    flipped_mask = 255 - mask
    for c in range(0, 3):
        image_to_cover[y_offset:y_offset + h, x_offset:x_offset + w, c] = \
            image_to_cover[y_offset:y_offset + h, x_offset:x_offset + w, c] * \
            (flipped_mask[y:y + h, x:x + w] / 255) + \
            image_to_place[y:y + h, x:x + w, c] * \
            (mask[y:y + h, x:x + w] / 255)
    return image_to_cover


def selfVideoTest():
    logging.getLogger('maskgen').info('Checking opencv and ffmpeg, this may take a minute.')
    writer = GrayBlockWriter('test_ts_gw', 29.97002997)
    mask_set = list()
    for i in range(255):
        mask = np.random.randint(255, size=(1090, 1920)).astype('uint8')
        mask_set.append(mask)
        writer.write(mask, i + 1 * 33.3666666667, i + 1)
    writer.close()
    fn = writer.get_file_name()
    vidfn = convertToVideo(fn)
    if not os.path.exists(vidfn):
        return 'Video Writing Failed'
    try:
        size = openImage(vidfn, getMilliSecondsAndFrameCount('00:00:01')).size
        if size != (1920, 1090):
            return 'Video Writing Failed: Frame Size inconsistent'
    except:
        return 'Video Writing Failed'
    return None

def dateTimeStampCompare(v1, v2):
    def get_defaults(source):
        exifdata = maskgen.exif.getexif(source)
        rd = {}
        for e in exifdata:
            if "date" in str(e).lower() or "time" in str(e).lower():
                rd[e] = exifdata[e]
        return rd
        #date_time_stamp = exifdata['Create Date'] if 'Create Date' in exifdata else exifdata['File Creation Date/Time']

    stamp1 = get_defaults(v1)
    rgexdict = {}
    for e in stamp1:
        st = stamp1[e]
        rgexf = "\\A"
        for x in st:
            if x.isdigit():
                rgexf += '[0-9]'
            elif x.isalpha():
                rgexf += '[a-zA-z]*'
            else:
                rgexf += x
        rgexf+= "\\Z"
        rgexdict[e] = rgexf

    stamp2 = get_defaults(v2)
    nonmatches = []
    for e in stamp2:
        if e in rgexdict:
            mo = re.match(rgexdict[e],stamp2[e])
            if mo is None:
                nonmatches.append(e)
        else:
            pass
            #nonmatches.append(e)
    return nonmatches
