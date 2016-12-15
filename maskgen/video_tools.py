import numpy as np
import cv2
from subprocess import call, Popen, PIPE
import os
import json
from datetime import datetime
import tool_set
import time
from image_wrap import ImageWrapper
from maskgen_loader import  MaskGenLoader

def otsu(hist):
    total = sum(hist)
    sumB = 0
    wB = 0
    maximum = 0.0
    sum1 = np.dot(np.asarray(range(256)), hist)
    for ii in range(256):
        wB = wB + hist[ii]
        if wB == 0:
            continue
        wF = total - wB
        if wF == 0:
            break
        sumB = sumB + ii * hist[ii]
        mB = sumB / wB
        mF = (sum1 - sumB) / wF
        between = wB * wF * (mB - mF) * (mB - mF)
        if between >= maximum:
            level = ii
            maximum = between
    return level


# def findRange(hist,perc):
#  maxvalue = hist[0]
#  maxpos = 0
#  maxdiff = 0
#  lastv = hist[0]
#  for i in range(1,256):
#    diff = abs(hist[i]-lastv)
#    if (diff > maxdiff):
#      maxdiff = diff
#    if hist[i] > maxvalue:
#      maxvalue = hist[i]
#      maxpos = i
#  i = maxpos-1
#  lastv = maxvalue
#  while i>0:
#    diff = abs(hist[i]-lastv)
#    if diff <= maxdiff:
#      break
#    lastv=hist[i]
#    i-=1
#  bottomRange = i
#  i = maxpos+1
#  lastv = maxvalue
#  while i<256:
#    diff = abs(hist[i]-lastv)
#    if diff <= maxdiff:
#      break
#    lastv=hist[i]
#    i+=1
#  topRange = i
#  return bottomRange,topRange

def _buildHist(filename):
    cap = cv2.VideoCapture(filename)
    hist = np.zeros(256).astype('int64')
    bins = np.asarray(range(257))
    pixelCount = 0.0
    while (cap.isOpened()):
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        pixelCount += (gray.shape[0] * gray.shape[1])
        hist += np.histogram(gray, bins=bins)[0]
    cap.release()
    return hist, pixelCount


def _buildMasks(filename, histandcount):
    maskprefix = filename[0:filename.rfind('.')]
    histnorm = histandcount[0] / histandcount[1]
    values = np.where((histnorm <= 0.95) & (histnorm > (256 / histandcount[1])))[0]
    cap = cv2.VideoCapture(filename)
    while (cap.isOpened()):
        ret, frame = cap.read()
        if not ret:
            break
        gray = tool_set.grayToRGB(frame)
        result = np.ones(gray.shape) * 255
        totalMatch = 0
        for value in values:
            matches = gray == value
            totalMatch += sum(sum(matches))
            result[matches] = 0
        if totalMatch > 0:
            elapsed_time = cap.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
            cv2.imwrite(maskprefix + '_mask_' + str(elapsed_time) + '.png', gray)
            break
    cap.release()


def buildMasksFromCombinedVideoOld(filename):
    h, pc = _buildHist(filename)
    hist = h / pc
    return _buildMasks(filename, hist)


def buildMasksFromCombinedVideo(filename, startSegment=None, endSegment=None, startTime=0):
    capIn = cv2.VideoCapture(filename)
    capOut = tool_set.GrayBlockWriter(filename[0:filename.rfind('.')],
                             capIn.get(cv2.cv.CV_CAP_PROP_FPS))
    try:
        ranges = []
        start = None
        count = 0
        THRESH=16
        HISYORY=10
        fgbg = cv2.BackgroundSubtractorMOG2(varThreshold=THRESH,history=HISYORY,bShadowDetection=False)
        LEARN_RATE = 0.03
        first = True
        sample = None
        kernel = np.ones((5, 5), np.uint8)
        while capIn.isOpened():
            ret, frame = capIn.read()
            if not ret:
                break
            if sample is None:
                sample = np.ones(frame[:, :, 0].shape) * 255
            elapsed_time = capIn.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
            if startSegment and startSegment > elapsed_time:
                continue
            if endSegment and endSegment < elapsed_time:
                break
            thresh = fgbg.apply(frame, learningRate=LEARN_RATE)
            if first:
                first = False
                continue
            #      gray = frame[:,:,1]
            #      laplacian = cv2.Laplacian(frame,cv2.CV_64F)
            #      thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY, 11, 1)
            #      ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            result = thresh.copy()
            result[:, :] = 0
            result[abs(thresh) > 0.000001] = 255
            opening = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
            closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
            totalMatch = sum(sum(closing))
            result = closing
            if totalMatch > 0:
                count += 1
                result = result.astype('uint8')
                result = 255 - result
                if start is None:
                    start = elapsed_time + startTime
                    sample = result
                    capOut.release()
                capOut.write(result,elapsed_time)
            else:
                if start is not None:
                    ranges.append(
                        {'starttime': start, 'endtime': elapsed_time + startTime, 'frames': count, 'mask': sample,
                         'videosegment': os.path.split(capOut.filename)[1]})
                    capOut.release()
                    count = 0
                start = None
        if start is not None:
            ranges.append({'starttime': start, 'endtime': elapsed_time + startTime, 'frames': count, 'mask': sample,
                           'videosegment': os.path.split(capOut.filename)[1]})
            capOut.release()
    finally:
        capIn.release()
        capOut.close()
    return ranges


def _invertSegment(segmentFileName, prefix):
    """
     Invert a single video file (gray scale)
     """
    capIn = tool_set.GrayBlockReader(segmentFileName)
    capOut = tool_set.GrayBlockWriter(prefix,capIn.fps)
    try:
        while True:
            frame_time = capIn.current_frame_time()
            ret, frame = capIn.read()
            if ret:
                result = abs(result - np.ones(result.shape) * 255)
                capOut.write(result,frame_time)
    finally:
        capIn.close()
        capOut.close()
    return capOut.filename


def invertVideoMasks(dir, videomasks, start, end):
    """
    Invert black/white for the video masks.
    Save to a new files for the given start and end node names.
    """
    if videomasks is None:
        return
    prefix = start + '_' + end
    result = []
    for maskdata in videomasks:
        maskdata = maskdata.copy()
        maskdata['videosegment'] = _invertSegment(maskdata['videosegment'], prefix)
        result.append(maskdata)
    return result


def addToMeta(meta, prefix, line, split=True):
    parts = line.split(',') if split else [line]
    for part in parts:
        pair = [x.strip().lower() for x in part.split(': ')]
        if len(pair) > 1 and pair[1] != '':
            if prefix != '':
                meta[prefix + '.' + pair[0]] = pair[1]
            else:
                meta[pair[0]] = pair[1]


def getStreamId(line):
    start = line.find('#')
    if start > 0:
        end = line.find('(', start)
        end = min(end, line.find(': ', start))
        return line[start:end]
    return ''


def processMeta(stream):
    meta = {}
    prefix = ''
    while True:
        line = stream.readline()
        if line is None or len(line) == 0:
            break
        if 'Stream' in line:
            prefix = getStreamId(line)
            splitPos = line.find(': ')
            meta[line[0:splitPos].strip()] = line[splitPos + 2:].strip()
            continue
        if 'Duration' in line:
            addToMeta(meta, prefix, line)
        else:
            addToMeta(meta, prefix, line, split=False)
    return meta


def sortFrames(frames):
    for k, v in frames.iteritems():
        frames[k] = sorted(v, key=lambda meta: meta['pkt_pts_time'])


def _addMetaToFrames(frames, meta):
    if len(meta) > 0 and 'stream_index' in meta:
        index = meta['stream_index']
        if index not in frames:
            frames[index] = []
        frames[index].append(meta)
        meta.pop('stream_index')


def processFrames(stream):
    frames = {}
    meta = {}
    while True:
        line = stream.readline()
        if line is None or len(line) == 0:
            break
        if '[/FRAME]' in line:
            _addMetaToFrames(frames, meta)
            meta = {}
        else:
            parts = line.split('=')
            if len(parts) > 1:
                meta[parts[0].strip()] = parts[1].strip()
    _addMetaToFrames(frames, meta)
    return frames


#   sortFrames(frames)

def getMeta(file, with_frames=False):
    ffmpegcommand = os.getenv('MASKGEN_FFPROBETOOL', 'ffprobe')
    p = Popen([ffmpegcommand, file, '-show_frames'] if with_frames else ['ffprobe', file], stdout=PIPE, stderr=PIPE)
    try:
        frames = processFrames(p.stdout) if with_frames else {}
        meta = processMeta(p.stderr)
    finally:
        p.stdout.close()
        p.stderr.close()
    return meta, frames

def runffmpeg(args):
    ffcommand = os.getenv('MASKGEN_FFMPEG', 'ffmpeg')
    command = [ffcommand]
    command.extend(args)
    try:
        p = Popen(command, stdout=PIPE, stderr=PIPE).communicate()
    except OSError as e:
        print "FFmpeg not installed"
        raise e

# str(ffmpeg.compareMeta({'f':1,'e':2,'g':3},{'f':1,'y':3,'g':4}))=="{'y': ('a', 3), 'e': ('d', 2), 'g': ('c', 4)}"
def compareMeta(oneMeta, twoMeta, skipMeta=None):
    diff = {}
    for k, v in oneMeta.iteritems():
        if skipMeta is not None and k in skipMeta:
            continue
        if k in twoMeta and twoMeta[k] != v:
            diff[k] = ('change', v, twoMeta[k])
        if k not in twoMeta:
            diff[k] = ('delete', v)
    for k, v in twoMeta.iteritems():
        if k not in oneMeta:
            diff[k] = ('add', v)
    return diff

def _getOrder(packet, orderAttr, lasttime, pkt_duration_time='pkt_duration_time'):
    try:
        if packet[orderAttr][0] == 'N':
            if packet['pkt_dts_time'][0] != 'N':
                return float(packet['pkt_dts_time'])
            elif len(packet[pkt_duration_time]) > 0 and  packet[pkt_duration_time][0] != 'N':
                return (lasttime + float(packet[pkt_duration_time])) if lasttime is not None else 0.0
        return float(packet[orderAttr])
    except ValueError as e:
        try:
           return float(packet['pkt_dts_time'])
        except:
            print packet
            raise e

# video_tools.compareStream([{'i':0,'h':1},{'i':1,'h':1},{'i':2,'h':1},{'i':3,'h':1},{'i':5,'h':2},{'i':6,'k':3}],[{'i':0,'h':1},{'i':3,'h':1},{'i':4,'h':9},{'i':4,'h':2}], orderAttr='i')
# [('delete', 1.0, 2.0, 2), ('add', 4.0, 4.0, 2), ('delete', 5.0, 6.0, 2)]
def compareStream(a, b, orderAttr='pkt_pts_time', skipMeta=None):
    """
      Compare to lists of hash maps, generating 'add', 'delete' and 'change' records.
      An order attribute (time stamp) is provided as the orderAttr, to identify each individual record.
      The order attribute is required to identify sequence of added or removed hashes.
      The order attribute serves as unique id of each hash.
      The order attribute is a mandatory key in the hash.
    """
    apos = 0
    bpos = 0
    diff = []
    start = 0
    aptime =None
    bptime = None
    while apos < len(a) and bpos < len(b):
        apacket = a[apos]
        if orderAttr not in apacket:
            apos += 1
            continue
        aptime  =  _getOrder(apacket, orderAttr,aptime)
        bpacket = b[bpos]
        if orderAttr not in bpacket:
            bpos += 1
            continue
        bptime = _getOrder(bpacket, orderAttr, bptime)
        if aptime == bptime:
            metaDiff = compareMeta(apacket, bpacket, skipMeta=skipMeta)
            if len(metaDiff) > 0:
                diff.append(('change', apos, bpos, aptime, metaDiff))
            apos += 1
            bpos += 1
        elif aptime < bptime:
            start = aptime
            c = 0
            while aptime < bptime and apos < len(a):
                end = aptime
                apos += 1
                c += 1
                if apos < len(a):
                    apacket = a[apos]
                    aptime = _getOrder(apacket, orderAttr,aptime)
            diff.append(('delete', start, end, c))
        elif aptime > bptime:
            start = bptime
            c = 0
            while aptime > bptime and bpos < len(b):
                end = bptime
                c += 1
                bpos += 1
                if bpos < len(b):
                    bpacket = b[bpos]
                    bptime = _getOrder(bpacket, orderAttr,bptime)
            diff.append(('add', start, end, c))
    if apos < len(a):
        aptime = start = _getOrder(a[apos], orderAttr,aptime)
        c = len(a) - apos
        apacket = a[len(a) - 1]
        aptime = _getOrder(apacket, orderAttr,aptime)
        diff.append(('delete', start, aptime, c))
    elif bpos < len(b):
        bptime = start = _getOrder(b[bpos], orderAttr,bptime)
        c = len(b) - bpos
        bpacket = b[len(b) - 1]
        bptime = _getOrder(bpacket, orderAttr, bptime)
        diff.append(('add', start, bptime, c))
    return diff


def compareFrames(one_frames, two_frames, skip_meta=None):
    diff = {}
    for streamId, packets in one_frames.iteritems():
        if streamId in two_frames:
            diff[streamId] = ('change', compareStream(packets, two_frames[streamId], skipMeta=skip_meta))
        else:
            diff[streamId] = ('delete', [])
    for streamId, packets in two_frames.iteritems():
        if streamId not in one_frames:
            diff[streamId] = ('add', [])
    return diff


# video_tools.formMetaDataDiff('/Users/ericrobertson/Documents/movie/videoSample.mp4','/Users/ericrobertson/Documents/movie/videoSample1.mp4')
def formMetaDataDiff(file_one, file_two):
    """
    Obtaining frame and video meta-data, compare the two videos, identify changes, frame additions and frame removals
    """
    one_meta, one_frames = getMeta(file_one, with_frames=True)
    two_meta, two_frames = getMeta(file_two, with_frames=True)
    meta_diff = compareMeta(one_meta, two_meta)
    frame_diff = compareFrames(one_frames, two_frames, skip_meta=['pkt_pos', 'pkt_size'])
    return meta_diff, frame_diff


# video_tools.processSet('/Users/ericrobertson/Documents/movie',[('videoSample','videoSample1'),('videoSample1','videoSample2'),('videoSample2','videoSample3'),('videoSample4','videoSample5'),('videoSample5','videoSample6'),('videoSample6','videoSample7'),('videoSample7','videoSample8'),('videoSample8','videoSample9'),('videoSample9','videoSample10'),('videoSample11','videoSample12'),('videoSample12','videoSample13'),('videoSample13','videoSample14'),('videoSample14','videoSample15')] ,'.mp4')
def processSet(directory, set_of_pairs, postfix):
    for pair in set_of_pairs:
        res_meta, res_frame = formMetaDataDiff(os.path.join(dir, pair[0] + postfix), os.path.join(directory, pair[1] + postfix))
        result_file = os.path.join(directory, pair[0] + "_" + pair[1] + ".json")
        with open(result_file, 'w') as f:
            json.dump({"meta": res_meta, "frames": res_frame}, f, indent=2)


def toMilliSeconds(st):
    """
      Convert time to millisecond
    """
    if not st or len(st) == 0:
        return 0

    stdt = None
    try:
        stdt = datetime.strptime(st, '%H:%M:%S.%f')
    except ValueError:
        stdt = datetime.strptime(st, '%H:%M:%S')
    return (stdt.hour * 3600 + stdt.minute * 60 + stdt.second) * 1000 + stdt.microsecond / 1000


def getDuration(st, et):
    """
     calculation duration
    """
    stdt = None
    try:
        stdt = datetime.strptime(st, '%H:%M:%S.%f')
    except ValueError:
        stdt = datetime.strptime(st, '%H:%M:%S')

    etdt = None
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


# video_tools.formMaskDiff('/Users/ericrobertson/Documents/movie/s1/videoSample5.mp4','/Users/ericrobertson/Documents/movie/s1/videoSample6.mp4')
def formMaskDiff2(fileOne, fileTwo, prefix, op, startSegment=None, endSegment=None, applyConstraintsToOutput=True):
    """
    Construct a diff video.  The FFMPEG provides degrees of difference by intensity variation in the green channel.
    The normal intensity is around 98.
    """
    ffmpegcommand = os.getenv('MASKGEN_FFMPEGTOOL', 'ffmpeg')
    postFix = fileOne[fileOne.rfind('.'):]
    outFileName = prefix + postFix
    command = [ffmpegcommand, '-y']
    if startSegment:
        command.extend(['-ss', startSegment])
        if endSegment:
            command.extend(['-t', getDuration(startSegment, endSegment)])
    command.extend(['-i', fileOne])
    if startSegment and applyConstraintsToOutput:
        command.extend(['-ss', startSegment])
        if endSegment:
            command.extend(['-t', getDuration(startSegment, endSegment)])
    command.extend(['-i', fileTwo, '-filter_complex', 'blend=all_mode=difference', outFileName])
    p = Popen(command, stderr=PIPE)
    errors = []
    sendErrors = False
    try:
        while True:
            line = p.stderr.readline()
            if line:
                errors.append(line)
            else:
                break
        sendErrors = p.wait() != 0
    except OSError as e:
        sendErrors = True
        errors.append(str(e))
    finally:
        p.stderr.close()

    if not sendErrors:
        result = buildMasksFromCombinedVideo(outFileName, startTime=toMilliSeconds(startSegment))
    else:
        result = []

    try:
        #os.remove(outFileName)
        print outFileName
    except IOError:
        print 'video diff process failed'

    return result, errors if sendErrors  else []


class VidAnalysisComponents:
    vid_one = None
    vid_two = None
    frame_one = None
    elapsed_time_one = None
    frame_two = None
    elapsed_time_two = None
    mask = None
    writer = None
    fps = None
    time_manager = None

    def __init__(self):
        pass

def cutDetect(vidAnalysisComponents, ranges=list()):
    """
    Find a region of cut frames given the current starting point
    :param vidAnalysisComponents:
    :param ranges: collection of meta-data describing then range of cut frames
    :return:
    """
    diff_in_time = abs(vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.elapsed_time_two)
    if (__changeCount(vidAnalysisComponents.mask) > 0 and
                diff_in_time < vidAnalysisComponents.fps_one) or not vidAnalysisComponents.vid_two.isOpened():
        cut = {}
        cut['starttime'] = vidAnalysisComponents.elapsed_time_one
        end_time = None
        count = 1
        cut['mask'] = vidAnalysisComponents.mask
        if type(cut['mask']) == int:
            cut['mask'] = np.zeros((vidAnalysisComponents.frame_one.shape[0],vidAnalysisComponents.frame_one.shape[1]))
        while (vidAnalysisComponents.vid_one.isOpened()):
            ret_one, frame_one = vidAnalysisComponents.vid_one.read()
            if not ret_one:
                vidAnalysisComponents.vid_one.release()
                break
            end_time = vidAnalysisComponents.vid_one.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
            diff = 0 if vidAnalysisComponents.frame_two is None else np.abs(frame_one - vidAnalysisComponents.frame_two)
            if __changeCount(diff) == 0 and vidAnalysisComponents.vid_two.isOpened():
                break
            count+=1
            if vidAnalysisComponents.time_manager.isPastTime(end_time):
                break
        cut['endtime'] = end_time
        cut['frames'] = count
        ranges.append(cut)

def addDetect(vidAnalysisComponents, ranges=list()):
    """
    Find a region of added frames given the current starting point
    :param vidAnalysisComponents:
    :param ranges: collection of meta-data describing then range of add frames
    :return:
    """
    diff_in_time = abs(vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.elapsed_time_two)
    if (__changeCount(vidAnalysisComponents.mask) > 0 and
                diff_in_time < vidAnalysisComponents.fps_one) or not vidAnalysisComponents.vid_one.isOpened():
        addition = {}
        addition['starttime'] = vidAnalysisComponents.elapsed_time_one
        end_time = None
        count = 1
        addition['mask'] = vidAnalysisComponents.mask
        if type(addition['mask']) == int:
            addition['mask'] = np.zeros((vidAnalysisComponents.frame_two.shape[0],vidAnalysisComponents.frame_two.shape[1]))
        while (vidAnalysisComponents.vid_two.isOpened()):
            ret_two, frame_two = vidAnalysisComponents.vid_two.read()
            if not ret_two:
                vidAnalysisComponents.vid_two.release()
                break
            end_time = vidAnalysisComponents.vid_two.get(cv2.cv.CV_CAP_PROP_POS_MSEC)

            diff = 0 if vidAnalysisComponents.frame_one is None else np.abs(vidAnalysisComponents.frame_one - frame_two)
            if __changeCount(diff) == 0 and vidAnalysisComponents.vid_one.isOpened():
                break
            count+=1
            if vidAnalysisComponents.time_manager.isPastTime(end_time):
                break
        addition['endtime'] = end_time
        addition['frames'] = count
        ranges.append(addition)

def __changeCount(mask):
    if isinstance(mask,np.ndarray):
        return __changeCount(sum(mask))
    return mask

def addChange(vidAnalysisComponents, ranges=list()):
    """
       Find a region of changed frames given the current starting point
       :param vidAnalysisComponents:
       :param ranges: collection of meta-data describing then range of changed frames
       :return:
       """
    diff_in_time = abs(vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.elapsed_time_two)
    if __changeCount(vidAnalysisComponents.mask) > 0 and diff_in_time < vidAnalysisComponents.fps:
        vidAnalysisComponents.writer.write(255-vidAnalysisComponents.mask,vidAnalysisComponents.elapsed_time_one)
        if len(ranges) == 0 or 'End Time' in ranges[-1]:
            change = dict()
            change['mask'] = vidAnalysisComponents.mask
            change['starttime'] = vidAnalysisComponents.elapsed_time_one
            change['frames'] = 1
            ranges.append(change)
        else:
            ranges[-1]['frames']+=1
    elif len(ranges) > 0 and 'End Time' not in ranges[-1]:
        change = ranges[-1]
        change['videosegment'] = os.path.split(vidAnalysisComponents.writer.filename)[1]
        change['endtime'] = vidAnalysisComponents.elapsed_time_one
        vidAnalysisComponents.writer.release()

def formMaskDiff(fileOne, fileTwo, name_prefix, opName, startSegment=None, endSegment=None, applyConstraintsToOutput=False):
    prefernences = MaskGenLoader()
    diffPref = prefernences.get_key('vid_diff')
    time_manager = tool_set.VidTimeManager(startTimeandFrame=startSegment,stopTimeandFrame=endSegment)
    opFunc = cutDetect if opName == 'SelectCutFrames' else (addDetect  if opName == 'PasteFrames' else addChange)
    if opFunc == addChange and (diffPref is None or diffPref == '2'):
        return formMaskDiff2(fileOne, fileTwo, name_prefix, opName)
    analysis_components = VidAnalysisComponents()
    analysis_components.vid_one = cv2.VideoCapture(fileOne)
    analysis_components.vid_two = cv2.VideoCapture(fileTwo)
    analysis_components.fps = analysis_components.vid_one.get(cv2.cv.CV_CAP_PROP_FPS)
    analysis_components.fps_one = analysis_components.vid_one.get(cv2.cv.CV_CAP_PROP_FPS)
    analysis_components.fps_two = analysis_components.vid_two.get(cv2.cv.CV_CAP_PROP_FPS)
    analysis_components.writer = tool_set.GrayBlockWriter(name_prefix,
                                                  analysis_components.vid_one.get(cv2.cv.CV_CAP_PROP_FPS))
    analysis_components.time_manager = time_manager
    ranges = list()
    #dir = os.path.split(fileOne)[0]
    kernel = np.ones((5, 5), np.uint8)
    try:
        while (analysis_components.vid_one.isOpened() and analysis_components.vid_two.isOpened()):
            ret_one, analysis_components.frame_one = analysis_components.vid_one.read()
            if not ret_one:
                analysis_components.vid_one.release()
                break
            elapsed_time = analysis_components.vid_one.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
            ret_two, analysis_components.frame_two = analysis_components.vid_two.read()
            if not ret_two:
                analysis_components.vid_two.release()
                break
            if time_manager.isBeforeTime(elapsed_time):
                continue
            if time_manager.isPastTime(elapsed_time):
                break
            # if applyConstraintsToOutput:
            #     elapsed_time = analysis_components.frame_two.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
            #     if startSegment and startSegment > elapsed_time:
            #          continue
            #    if endSegment and endSegment < elapsed_time:
            #        break
            analysis_components.elapsed_time_one = elapsed_time
            analysis_components.elapsed_time_two = analysis_components.vid_two.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
            diff = np.abs(analysis_components.frame_one - analysis_components.frame_two)
            #Image.fromarray(analysis_components.frame_one).save(dir + '/vidpng/v1_'+str(elapsed_time) + '.png')
            #Image.fromarray(analysis_components.frame_two).save(dir + '/vidpng/v2_' + str(elapsed_time) + '.png')
            #Image.fromarray(diff).save(dir + '/vidpng/diff_' + str(elapsed_time) + '.png')
            analysis_components.mask = np.zeros((analysis_components.frame_one.shape[0],analysis_components.frame_one.shape[1])).astype('uint8')
            diff  = cv2.cvtColor(diff,cv2.COLOR_RGBA2GRAY)
            analysis_components.mask[diff > 0.0001] = 255
            opening = cv2.erode(analysis_components.mask, kernel,2)
            analysis_components.mask = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
            opFunc(analysis_components,ranges)
        analysis_components.mask = 0
        opFunc(analysis_components,ranges)
        analysis_components.writer.release()
    finally:
        analysis_components.vid_one.release()
        analysis_components.vid_two.release()
        analysis_components.writer.close()
    return ranges,[]

def _getVideoFrame(video,frame_time):
    while video.isOpened():
        ret, frame = video.read()
        if not ret:
            break
        elapsed_time = video.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
        if elapsed_time >= frame_time:
            return frame,elapsed_time
    return None,None

def interpolateMask(mask_file_name_prefix,
                    directory,
                    video_masks,
                    start_file_name,
                    dest_file_name,
                    arguments={}):
    """
    :param mask_file_name_prefix:
    :param directory:
    :param video_masks:
    :param start_file_name:
    :param dest_file_name:
    :return: maskname, mask, analysis, errors
    """
    if tool_set.fileType(start_file_name) == 'image':
        image = tool_set.openImage(start_file_name)
        new_mask_set = []
        for mask_set in video_masks:
            change = dict()
            reader = tool_set.GrayBlockReader(os.path.join(directory,
                                                                    mask_set['videosegment']))
            writer = tool_set.GrayBlockWriter(os.path.join(directory,mask_file_name_prefix),
                                              reader.fps)
            destination_video = cv2.VideoCapture(dest_file_name)
            try:
                first_mask = None
                count = 0
                vid_frame_time=0
                max_analysis = 0
                while True:
                    frame_time = reader.current_frame_time()
                    mask = reader.read()
                    if mask is None:
                        break
                    if frame_time < vid_frame_time:
                        continue
                    frame,vid_frame_time = _getVideoFrame(destination_video,frame_time)
                    if frame is None:
                         new_mask = np.ones(mask.shape) * 255
                    else:
                        new_mask, analysis = tool_set.interpolateMask(ImageWrapper(mask),image, ImageWrapper(frame))
                        if new_mask is None:
                            new_mask = np.asarray(tool_set.convertToMask(image))
                            max_analysis+=1
                        if first_mask is None:
                            change['mask'] = new_mask
                            change['starttime'] = frame_time
                            first_mask = new_mask
                    count+=1
                    writer.write(new_mask,vid_frame_time)
                    if max_analysis > 10:
                        break
                change['endtime'] = vid_frame_time
                change['frames'] = count
                change['videosegment'] = os.path.split(writer.filename)[1]
                if first_mask is not None:
                    new_mask_set.append(change)
            finally:
                reader.close()
                writer.close()
                destination_video.release()
        return new_mask_set,[]
    # Masks cannot be generated for video to video....yet
    return [],[]

def pullFrameNumber(video_file, frame_number):
    """

    :param video_file:
    :param frame_number:
    :return:
    """

    frame = None
    video_capture = cv2.VideoCapture(video_file)
    while (video_capture.isOpened() and frame_number > 0):
        ret, frame = video_capture.read()
        if not ret:
            break
        frame_number-=1
    elapsed_time = video_capture.get(cv2.cv.CV_CAP_PROP_POS_MSEC)
    video_capture.release()
    ImageWrapper(frame).save(video_file[0:video_file.rfind('.')] + '.png')
    return time.strftime("%H:%M:%S", time.gmtime(elapsed_time / 1000)) + '.%03d' % (elapsed_time % 1000)

def main(argv=None):
    print pullFrameNumber('/Users/ericrobertson/Documents/movie/videoSample5.mp4',
                            50)
    #print formMaskDiff2('/Users/ericrobertson/Documents/movie/videoSample5.mp4',
    #                     '/Users/ericrobertson/Documents/movie/videoSample6.mp4', "/Users/ericrobertson/Documents/movie/v5_v6", 'SelectCutFrames')

if __name__ == "__main__":
    import sys
    sys.exit(main())
