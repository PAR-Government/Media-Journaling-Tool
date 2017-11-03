import numpy as np
from subprocess import call, Popen, PIPE
import os
import json
from datetime import datetime
import tool_set
import time
from image_wrap import ImageWrapper
from maskgen_loader import  MaskGenLoader
import logging
from cv2api import cv2api_delegate
import cv2
from cachetools import LRUCache
from cachetools import cached
from threading import RLock

meta_lock = RLock()
meta_cache = LRUCache(maxsize=24)


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

def __buildHist(filename):
    cap = cv2api_delegate.videoCapture(filename)
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


def __buildMasks(filename, histandcount):
    maskprefix = filename[0:filename.rfind('.')]
    histnorm = histandcount[0] / histandcount[1]
    values = np.where((histnorm <= 0.95) & (histnorm > (256 / histandcount[1])))[0]
    cap = cv2api_delegate.videoCapture(filename)
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
            elapsed_time = cap.get(cv2api_delegate.prop_pos_msec)
            cv2.imwrite(maskprefix + '_mask_' + str(elapsed_time) + '.png', gray)
            break
    cap.release()


def buildMasksFromCombinedVideoOld(filename):
    h, pc = __buildHist(filename)
    hist = h / pc
    return __buildMasks(filename, hist)


def buildMasksFromCombinedVideo(filename,time_manager):
    """

    :param filename: str
    :param time_manager: tool_set.VidTimeManager
    :return:
    """
    capIn = cv2api_delegate.videoCapture(filename)
    capOut = tool_set.GrayBlockWriter(filename[0:filename.rfind('.')],
                             capIn.get(cv2api_delegate.prop_fps))
    amountRead = 0
    try:
        ranges = []
        startTime = None
        startFrame = 0
        count = 0
        THRESH=16
        HISYORY=10
        #fgbg = cv2.BackgroundSubtractorMOG2(varThreshold=THRESH,history=HISYORY,bShadowDetection=False)
        #LEARN_RATE = 0.03
        #first = True
        sample = None
        baseline = None
        kernel = np.ones((3, 3), np.uint8)
        last_time =0
        elapsed_time = 0
        while capIn.isOpened():
            ret, frame = capIn.read()
            if not ret:
                break
            amountRead+=1
            if sample is None:
                sample = np.ones(frame[:, :, 0].shape).astype('uint8')
                mean_value = np.median(frame[:,:,1])
                baseline = np.ones(frame[:, :, 0].shape).astype('uint8') * mean_value
            last_time = elapsed_time
            elapsed_time = capIn.get(cv2api_delegate.prop_pos_msec)
            time_manager.updateToNow(elapsed_time)
            if time_manager.isBeforeTime():
                continue
            if time_manager.isPastTime():
                break
            #thresh = fgbg.apply(frame, learningRate=LEARN_RATE)
            #if first:
            #    first = False
           #     continue
            #      gray = frame[:,:,1]
            #      laplacian = cv2.Laplacian(frame,cv2.CV_64F)
            #      thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY, 11, 1)
            #      ret, thresh = cv2.threshold(gray,0,255,cv2.THRESH_BINARY+cv2.THRESH_OTSU)
            thresh = frame[:,:,1] - baseline
            result = thresh.copy()
            result[:, :] = 0
            result[abs(thresh) > 1] = 255
            #opening = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
            #closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
            totalMatch = sum(sum(abs(result) > 1))
            #result = result
            if totalMatch > 0:
                count += 1
                result = result.astype('uint8')
                result = 255 - result
                if startTime is None:
                    startTime = last_time
                    startFrame = time_manager.frameSinceBeginning
                    sample = result
                    capOut.release()
                capOut.write(result, last_time, amountRead)
            else:
                if startTime is not None:
                    ranges.append(
                        {'starttime': startTime,
                         'endtime': last_time,
                         'startframe':startFrame,
                         'endframe': time_manager.frameSinceBeginning,
                         'frames': count,
                         'rate': capIn.get(cv2api_delegate.prop_fps),
                         'mask': sample,
                         'videosegment': os.path.split(capOut.filename)[1]})
                    capOut.release()
                    count = 0
                startTime = None
        if startTime is not None:
            ranges.append({'starttime': startTime,
                           'endtime': last_time,
                           'startframe': startFrame,
                           'endframe': time_manager.frameSinceBeginning,
                           'frames': time_manager.frameSinceBeginning-startFrame,
                           'rate': capIn.get(cv2api_delegate.prop_fps),
                           'mask': sample,
                           'videosegment': os.path.split(capOut.filename)[1]})
            capOut.release()
    finally:
        capIn.release()
        capOut.close()
    if amountRead == 0:
        raise ValueError('Mask Computation Failed to a read videos.  FFMPEG and OPENCV may not be installed correctly or the videos maybe empty.')
    return ranges


def __invertSegment(segmentFileName, prefix):
    """
     Invert a single video file (gray scale)
     """
    capIn = tool_set.GrayBlockReader(segmentFileName)
    capOut = tool_set.GrayBlockWriter(prefix,capIn.fps)
    try:
        while True:
            frame_time = capIn.current_frame_time()
            frame_count = capIn.current_frame()
            frame = capIn.read()
            if frame is not None:
                frame = abs(frame - np.ones(frame.shape) * 255)
                capOut.write(frame,frame_time, frame_count)
            else:
                break
    finally:
        capIn.close()
        capOut.close()
    return capOut.filename


def invertVideoMasks(videomasks, start, end):
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
        maskdata['videosegment'] = __invertSegment(maskdata['videosegment'], prefix)
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

def processMetaStreams(stream):
    streams = []
    temp = {}
    while True:
        line = stream.readline()
        if line is None or len(line) == 0:
            break
        if '[STREAM]' in line or '[FORMAT]' in line:
            while True:
                line = stream.readline()
                if '[/STREAM]' in line or '[/FORMAT]' in line:
                    streams.append(temp)
                    temp = {}
                    break
                else:
                    setting = line.split('=')
                    temp[setting[0]] = '='.join(setting[1:]).strip()

    return streams

def sortFrames(frames):
    for k, v in frames.iteritems():
        frames[k] = sorted(v, key=lambda meta: meta['pkt_pts_time'])

def __addMetaToFrames(frames, meta):
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
            __addMetaToFrames(frames, meta)
            meta = {}
        else:
            parts = line.split('=')
            if len(parts) > 1:
                meta[parts[0].strip()] = parts[1].strip()
    __addMetaToFrames(frames, meta)
    return frames


def ffmpegToolTest():
    ffmpegcommand = [os.getenv('MASKGEN_FFPROBETOOL', 'ffprobe'), '-L']
    try:
        p = Popen(ffmpegcommand, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
    except:
        return ffmpegcommand[0]+ ' not installed properly'

    ffmpegcommand = [os.getenv('MASKGEN_FFPROBETOOL', 'ffmpeg'), '-L']
    try:
        p = Popen(ffmpegcommand, stdout=PIPE, stderr=PIPE)
        stdout, stderr = p.communicate()
    except:
        return ffmpegcommand[0] + ' not installed properly'
    return None

#   sortFrames(frames)

def getMeta(file, with_frames=False, show_streams=False):
    def runProbe(func, args=None):
        ffmpegcommand = [os.getenv('MASKGEN_FFMPEG', 'ffprobe'), file]
        if args != None:
            ffmpegcommand.append(args)
        p = Popen(ffmpegcommand, stdout=PIPE, stderr=PIPE)
        try:
            return func(p.stdout)
        finally:
            p.stdout.close()
            p.stderr.close()

    if with_frames:
        frames = runProbe(processFrames,args='-show_frames')
    else:
        frames = {}
    if show_streams:
        meta = runProbe(processMetaStreams, args='-show_streams')
    else:
        meta = runProbe(processMeta, args=None)

    return meta, frames

def getShape(video_file):
    """

    :param video_file:
    :return: width,height
    """
    meta, frames = getMeta(video_file,show_streams=True)
    width = 0
    height =0
    for item in meta:
        if 'width' in item:
            width = int(item['width'])
        if 'height' in item:
            height = int(item['height'])
    return width,height


def getMaskSetForEntireVideo(video_file, start_time='00:00:00.000', end_time=None, media_types=['video'],channel=0):
    return getMaskSetForEntireVideoForTuples(video_file,
                                      start_time_tuple=tool_set.getMilliSecondsAndFrameCount(start_time),
                                      end_time_tuple = tool_set.getMilliSecondsAndFrameCount(end_time) if end_time is not None and end_time != '0' else None,
                                      media_types=media_types,channel=channel)

def getMaskSetForEntireVideoForTuples(video_file, start_time_tuple=(0,0), end_time_tuple=None, media_types=['video'],
                                 channel=0):
    """
    build a mask set for the entire video
    :param video_file:
    :return: list of dict
    """
    st = start_time_tuple
    et = end_time_tuple
    calculate_frames = st[0] > 0  or st[1] > 0 or et is not None
    meta, frames = getMeta(video_file, show_streams=True,with_frames=calculate_frames)
    found_num = 0
    results = []
    for item in meta:
        if 'codec_type' in item and item['codec_type'] in media_types:
            if found_num != channel:
                found_num+=1
                continue
            mask = {}
            fr = item['r_frame_rate'] if 'r_frame_rate' in item else (item['avg_frame_rate'] if 'avg_frame_rate' in item else '30000/1001')
            if item['codec_type'] == 'video':
                parts = fr.split('/')
                rate = float(parts[0])/int(parts[1]) if len(parts)>0 else float(parts[0])
            else:
                rate = 1.0/int(item['sample_rate']) * 1000
            mask['rate'] = rate
            mask['starttime'] = 0
            mask['startframe'] = 1
            mask['endtime'] = float(item['duration'])*1000
            mask['endframe'] = int(item['nb_frames']) if 'nb_frames' in item  else int(mask['endtime']/rate)
            mask['frames'] = mask['endframe']
            mask['type']=item['codec_type']
            count = 0
            if calculate_frames:
                frame_set = frames[item['index']]
                aptime = 0
                framessince_start = 0
                startcomplete = False
                for packet in frame_set:
                    count += 1
                    lasttime = aptime*1000
                    aptime = __getOrder(packet,'pkt_pts_time',aptime)
                    if aptime*1000 >= st[0] and not startcomplete:
                        if framessince_start >= st[1]:
                            startcomplete = True
                            mask['starttime'] = lasttime
                            mask['startframe'] = count
                            framessince_start = 0
                            if et is None:
                                break
                        else:
                            framessince_start+=1
                    elif et is not None and aptime*1000 >= et[0]:
                        if framessince_start >= et[1]:
                            mask['endtime'] = lasttime
                            mask['endframe'] = count
                            break
                        else:
                            framessince_start += 1
                mask['frames'] = mask['endframe'] - mask['startframe']  + 1
            results.append(mask)
    return results  if len(results) > 0 else None

def get_ffmpeg_version():
    ffcommand = os.getenv('MASKGEN_FFMPEG', 'ffmpeg')
    command = [ffcommand,'-version']
    try:
        pcommand = Popen(command, stdout=PIPE, stderr=PIPE)
        stdout, stderr = pcommand.communicate()
        if pcommand.returncode != 0:
            logging.getLogger('maskgen').error(str(stderr) if stderr is not None else '')
        else:
            return stdout.split()[2][0:3]
    except OSError as e:
        logging.getLogger('maskgen').error("FFmpeg not installed")
        logging.getLogger('maskgen').error(str(e))
    return '?'

def runffmpeg(args, noOutput=True):
    ffcommand = os.getenv('MASKGEN_FFMPEG', 'ffmpeg')
    command = [ffcommand]
    command.extend(args)
    try:
        pcommand =  Popen(command, stdout=PIPE if not noOutput else None, stderr=PIPE)
        stdout, stderr =  pcommand.communicate()
        if pcommand.returncode != 0:
            error =  str(stdout) + (str(stderr) if stderr is not None else '')
            raise ValueError(error)
    except OSError as e:
        logging.getLogger('maskgen').error( "FFmpeg not installed")
        logging.getLogger('maskgen').error(str(e))
        raise e

def __aggregate(k, oldValue, newValue, summary):
    """
    Apply to numeric values, aummarize the diffence
    :param k:
    :param oldValue:
    :param newValue:
    :param summary:
    :return:
    """
    try:
        num1 = float(oldValue)
        num2 = float(newValue)
        if k in summary:
            summary[k] =  (summary[k][0]+(num2 - num1),summary[k][1]+1)
        else:
            summary[k] = ((num2 - num1), 1)
        return True
    except:
        return False

# str(ffmpeg.compareMeta({'f':1,'e':2,'g':3},{'f':1,'y':3,'g':4}))=="{'y': ('a', 3), 'e': ('d', 2), 'g': ('c', 4)}"
def compareMeta(oneMeta, twoMeta, skipMeta=None, streamId=0,  meta_diff=None, summary=dict()):
    diff = {}
    for k, v in oneMeta.iteritems():
        if skipMeta is not None and k in skipMeta:
            continue
        meta_key = str(streamId) + ':' + k
        if k in twoMeta and twoMeta[k] != v:
            if meta_diff is not None and  meta_key not in meta_diff:
                diff[k] = ('change', v, twoMeta[k])
                meta_diff[meta_key] = ('change', v, twoMeta[k])
            elif meta_diff is not None:
                if meta_diff[meta_key][2] != twoMeta[k]:
                    if not __aggregate(k, v, twoMeta[k], summary):
                        diff[k] = ('change', v, twoMeta[k])
            else:
                diff[k] = ('change', v, twoMeta[k])
        if k not in twoMeta:
            if meta_diff is not None and  meta_key not in meta_diff:
                diff[k] = ('delete', v)
                meta_diff[meta_key] = ('delete', v)
            elif meta_diff is None :
                diff[k] = ('delete', v)
    for k, v in twoMeta.iteritems():
        if k not in oneMeta:
            meta_key = str(streamId) + ':' + k
            if meta_diff is not None and meta_key not in meta_diff:
                diff[k] = ('add', v)
                meta_diff[meta_key] = ('add', v)
            elif meta_diff is None:
                diff[k] = ('add', v)
    return diff

def __getOrder(packet, orderAttr, lasttime, pkt_duration_time='pkt_duration_time'):
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
            logging.getLogger('maskgen').warning("Error get order packet " + str(packet))
            raise e

def getIntFromPacket(key, packet):
    if key in packet:
        try:
            return int(packet[key])
        except:
            pass
    return 0

def __updateSummary(summary, streamId, apos, bpos, aptime):
    diff = {}
    for k, v in summary.iteritems():
        diff[str(streamId) + ':' + k + '.total'] = ('change',0,v[0])
        diff[str(streamId) + ':' + k + '.frames'] = ('change',0,v[1])
        diff[str(streamId) + ':' + k + '.average'] = ('change',0,v[0]/v[1])
    return ('change', apos, bpos, aptime, diff)

# video_tools.compareStream([{'i':0,'h':1},{'i':1,'h':1},{'i':2,'h':1},{'i':3,'h':1},{'i':5,'h':2},{'i':6,'k':3}],[{'i':0,'h':1},{'i':3,'h':1},{'i':4,'h':9},{'i':4,'h':2}], orderAttr='i')
# [('delete', 1.0, 2.0, 2), ('add', 4.0, 4.0, 2), ('delete', 5.0, 6.0, 2)]
def compareStream(a, b, orderAttr='pkt_pts_time', streamId=0, meta_diff=dict(), skipMeta=None, counters={}):
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
   # a = sorted(a,key=lambda apacket: apacket[orderAttr])
    #b = sorted(b, key=lambda apacket: apacket[orderAttr])
    summary = dict()
    summary_start_time = None
    summary_start = None
    summary_end = None
    while apos < len(a) and bpos < len(b):
        apacket = a[apos]
        if orderAttr not in apacket:
            apos += 1
            continue
        aptime  =  __getOrder(apacket, orderAttr, aptime)
        bpacket = b[bpos]
        if orderAttr not in bpacket:
            bpos += 1
            continue
        bptime = __getOrder(bpacket, orderAttr, bptime)
        for k in counters.keys():
            counters[k][0] = counters[k][0] + getIntFromPacket(k,apacket)
            counters[k][1] = counters[k][1] + getIntFromPacket(k,bpacket)
        if aptime == bptime or \
                (aptime < bptime and (apos+1) < len(a) and __getOrder(a[apos+1], orderAttr, aptime) > bptime) or \
                (aptime > bptime and (bpos+1) < len(b) and __getOrder(b[bpos+1], orderAttr, bptime) < aptime):
            summary_start_time = aptime if summary_start is None else summary_start_time
            summary_start = apos if summary_start is None else summary_start
            summary_end = apos
            metaDiff = compareMeta(apacket, bpacket, skipMeta=skipMeta,streamId=streamId,meta_diff=meta_diff,summary=summary)
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
                    aptime = __getOrder(apacket, orderAttr, aptime)
            #diff.append(('delete', start, end, c))
        elif aptime > bptime:
            start = bptime
            c = 0
            while aptime > bptime and bpos < len(b):
                end = bptime
                c += 1
                bpos += 1
                if bpos < len(b):
                    bpacket = b[bpos]
                    bptime = __getOrder(bpacket, orderAttr, bptime)
            # diff.append(('add', start, end, c))
        else:
            diff.append(__updateSummary(summary, streamId, summary_start, summary_end, summary_start_time))
            summary_start_time = None
            summary_start = None
            summary_end = None
            summary.clear()

    diff.append(__updateSummary(summary, streamId, summary_start, summary_end, summary_start_time))
    if apos < len(a):
        aptime = start = __getOrder(a[apos], orderAttr, aptime)
        c = len(a) - apos
        apacket = a[len(a) - 1]
        aptime = __getOrder(apacket, orderAttr, aptime)
        diff.append(('delete', start, aptime, c))
    elif bpos < len(b):
        bptime = start = __getOrder(b[bpos], orderAttr, bptime)
        c = len(b) - bpos
        bpacket = b[len(b) - 1]
        bptime = __getOrder(bpacket, orderAttr, bptime)
        diff.append(('add', start, bptime, c))

    return diff

def compareFrames(one_frames, two_frames, meta_diff=dict(), summarize=[],skip_meta={''}, counters={}):
    diff = {}
    for streamId, packets in one_frames.iteritems():
        if streamId in two_frames:
            diff[streamId] = ('change',
                              compareStream(packets, two_frames[streamId],streamId=streamId,meta_diff=meta_diff, skipMeta=skip_meta,counters=counters))
        else:
            diff[streamId] = ('delete', [])
    for streamId, packets in two_frames.iteritems():
        if streamId not in one_frames:
            diff[streamId] = ('add', [])
    return diff


# video_tools.formMetaDataDiff('/Users/ericrobertson/Documents/movie/videoSample.mp4','/Users/ericrobertson/Documents/movie/videoSample1.mp4')
def formMetaDataDiff(file_one, file_two, frames=True):
    """
    Obtaining frame and video meta-data, compare the two videos, identify changes, frame additions and frame removals
    """
    one_meta, one_frames = getMeta(file_one, with_frames=frames)
    two_meta, two_frames = getMeta(file_two, with_frames=frames)
    meta_diff = compareMeta(one_meta, two_meta)
    counters= {}
    counters['interlaced_frame'] = [0,0]
    counters['key_frame'] = [0, 0]
    if frames:
        frame_diff = compareFrames(one_frames, two_frames,
                                   meta_diff=meta_diff,
                                   skip_meta=['pkt_pos', 'pkt_size'], counters = counters)
        if counters['interlaced_frame'][0] - counters['interlaced_frame'][1] != 0:
            meta_diff ['interlaced_frames'] = ('change',counters['interlaced_frame'][0] , counters['interlaced_frame'][1])
        if counters['key_frame'][0] - counters['key_frame'][1] != 0:
            meta_diff ['key_frames'] = ('change',counters['key_frame'][0] , counters['key_frame'][1])
    else:
        frame_diff = {}
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

def removeVideoFromAudio(filename,outputname=None):
    import tempfile
    if outputname is None:
        suffix = filename[filename.find('.'):]
        newfilename = tempfile.mktemp(prefix='rmfa', suffix=suffix, dir='.')
    else:
        newfilename = outputname
    ffmpegcommand = os.getenv('MASKGEN_FFMPEGTOOL', 'ffmpeg')
    command = [ffmpegcommand, '-y', '-i', filename,'-vn','-acodec','copy',newfilename]
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    try:
        if stderr is not None:
            for line in stderr.splitlines():
                logging.getLogger('maskgen').warning("FFMPEG error for {} is {}".format(filename, line))
        return newfilename if p.returncode == 0 else None
    except OSError as e:
        logging.getLogger('maskgen').error("FFMPEG invocation error for {} is {}".format(filename, str(e)))



def x265(filename ,outputname=None, crf=0, remove_video=False):
    return __vid_compress(filename,
                          ['-loglevel','error','-c:v','libx265','-preset','medium','-x265-params', '--lossless', '-crf',str(crf),'-c:a','aac','-b:a','128k'],
                         'hvec',
                          outputname=outputname,
                          remove_video=remove_video)

def lossy(filename, outputname=None, crf=0,remove_video=False):
    return __vid_compress(filename,
                          ['-loglevel','error'],
                         'h264',
                          outputname=outputname,
                          suffix = 'mov',
                          remove_video=remove_video)

def x264fast(filename, outputname=None, crf=0,remove_video=False):
    return __vid_compress(filename,
                          ['-loglevel','error','-c:v', 'libx264', '-preset', 'ultrafast',  '-crf', str(crf)],
                         'h264',
                          outputname=outputname,
                          remove_video=remove_video)

def x264(filename, outputname=None, crf=0,remove_video=False):
    return __vid_compress(filename,
                          ['-loglevel','error','-c:v', 'libx264', '-preset', 'medium',  '-crf', str(crf)],
                         'h264',
                          outputname=outputname,
                          remove_video=remove_video)


def vid_md5(filename):
    ffmpegcommand = os.getenv('MASKGEN_FFMPEGTOOL', 'ffmpeg')
    prefix = filename[0:filename.rfind('.')]
    outFileName = prefix + '_compressed.mp4'
    if filename == outFileName:
        return filename
    command = [ffmpegcommand, '-i', filename,'-loglevel','error','-map','0:v', '-f','md5','-']
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    try:
        if stderr is not None:
            for line in stderr.splitlines():
                logging.getLogger('maskgen').warning("FFMPEG error for {} is {}".format(filename, line))
        return stdout.strip() if p.returncode == 0 else None
    except OSError as e:
        logging.getLogger('maskgen').error("FFMPEG invocation error for {} is {}".format(filename, str(e)))

def __vid_compress(filename, expressions, criteria, suffix='avi', outputname=None, remove_video=False):
    #md5 = vid_md5(filename)
    one_meta, one_frames = getMeta(filename, with_frames=False)
    execute_remove= False
    execute_compress = True
    input_filename = filename
    #see if already compressed
    if one_meta is not None:
        for k,v in one_meta.iteritems():
            if 'Stream' in k and 'Video' in v and remove_video:
                execute_remove= True
            if 'Stream' in k and criteria in v:
                execute_compress = False
    prefix = input_filename[0:filename.rfind('.')]
    if not input_filename.endswith(suffix):
        execute_compress = True
    outFileName = prefix + '_compressed.' + suffix if outputname is None else outputname
    ffmpegcommand = os.getenv('MASKGEN_FFMPEGTOOL', 'ffmpeg')
    if  execute_remove:
        input_filename = removeVideoFromAudio(input_filename, outputname=outFileName if not execute_compress else None)
    elif input_filename == outFileName:
        return input_filename

    if not execute_compress:
        return input_filename

    command = [ffmpegcommand, '-y','-i', input_filename]
    command.extend(expressions)
    command.append(outFileName)
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    try:
        if stderr is not None:
            for line in stderr.splitlines():
                logging.getLogger('maskgen').warning("FFMPEG error for {} is {}".format(filename, line))
        return outFileName if p.returncode == 0 else None
    except OSError as e:
        logging.getLogger('maskgen').error("FFMPEG invocation error for {} is {}".format(filename, str(e)))
    finally:
        if input_filename != filename:
            os.remove(input_filename)


def _runCommand(command,outputCollector=None):
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

def getFrameRate(fileOne, default=None):
    ffmpegcommand = os.getenv('MASKGEN_FFPROBETOOL', 'ffprobe')
    results = []
    errors = _runCommand([ffmpegcommand,
                          '-v' ,'0', '-of', 'compact=p=0','-show_entries','stream=r_frame_rate',
                          fileOne],
                         outputCollector=results)
    if len(results) > 0:
        for result in results:
            rate = result.split('=')[1].strip().split('/')
            if len(rate) == 1 and float(rate[0]) > 0:
                return float(rate[0])
            if len(rate) == 2 and float(rate[1]) > 0:
                return float(rate[0]) / float(rate[1])
    return default

def toAudio(fileOne,outputName=None):
        """
        Consruct wav files
        """
        name = fileOne + '.wav' if outputName is None else outputName
        ffmpegcommand = os.getenv('MASKGEN_FFMPEGTOOL', 'ffmpeg')
        if os.path.exists(name):
            os.remove(name)
        errors = _runCommand([ffmpegcommand, '-ac', '1', '-i', fileOne, '-vn',name])
        return name if len(errors) == 0 else None, errors

# video_tools.formMaskDiff('/Users/ericrobertson/Documents/movie/s1/videoSample5.mp4','/Users/ericrobertson/Documents/movie/s1/videoSample6.mp4')
def __formMaskDiffWithFFMPEG(fileOne, fileTwo, prefix, op, time_manager, codec=['-vcodec', 'r210']):
    """
    Construct a diff video.  The FFMPEG provides degrees of difference by intensity variation in the green channel.
    The normal intensity is around 98.
    """
    ffmpegcommand = os.getenv('MASKGEN_FFMPEGTOOL', 'ffmpeg')
    postFix = fileOne[fileOne.rfind('.'):]
    outFileName = prefix + postFix
    command = [ffmpegcommand, '-y']
    #if startSegment:
    #    command.extend(['-ss', startSegment])
    #    if endSegment:
    #        command.extend(['-t', getDuration(startSegment, endSegment)])
    command.extend(['-i', fileOne])
    #if startSegment:
    #    command.extend(['-ss', startSegment])
    #    if endSegment:
    #        command.extend(['-t', getDuration(startSegment, endSegment)])
    #command.extend(['-i', fileTwo, '-map','0:v','-filter_complex', 'blend=all_mode=difference', '-qp', '0', outFileName])
    command.extend(
        ['-i', fileTwo, '-map', '0:v', '-filter_complex', 'blend=all_mode=difference'])
    command.extend(codec)
    command.append( outFileName)
    p = Popen(command, stdout=PIPE,stderr=PIPE)
    stdout, stderr = p.communicate()
    errors = []
    sendErrors = False
    try:
        if stderr is not None:
            for line in stderr.splitlines():
                if len(line) > 2:
                    errors.append(line)
        sendErrors = p.returncode != 0
    except OSError as e:
        sendErrors = True
        errors.append(str(e))
    if not sendErrors:
        result = buildMasksFromCombinedVideo(outFileName, time_manager)
    else:
        result = []
    try:
        os.remove(outFileName)
    except OSError:
        print 'video diff process failed'

    return result, errors if sendErrors  else []


class VidAnalysisComponents:
    vid_one = None
    vid_two = None
    frame_one = None
    rate_one = 0
    rate_two = 0
    frame_two = None
    mask = None
    writer = None
    fps = None
    time_manager = None
    frame_two_mask = None
    frame_one_mask = None
    """
    @type time_manager: tool_set.VidTimeManager
    @type elapsed_time_one: int
    @type elapsed_time_two: int
    """

    def __init__(self):
        self.one_count = 0
        self.two_count = 0
        self.elapsed_time_one = 0
        self.elapsed_time_two = 0

    def grabOne(self):
        res = self.vid_one.grab()
        self.grabbed_one = res
        if res:
            elapsed_time_one = self.vid_one.get(cv2api_delegate.prop_pos_msec)
            self.rate_one = elapsed_time_one - self.elapsed_time_one
            self.elapsed_time_one = elapsed_time_one
            self.one_count+=1
        return res

    def grabTwo(self):
        res = self.vid_two.grab()
        self.grabbed_two = res
        if res:
            elapsed_time_two = self.vid_two.get(cv2api_delegate.prop_pos_msec)
            self.rate_two = elapsed_time_two - self.elapsed_time_two
            self.elapsed_time_two = elapsed_time_two
            self.two_count += 1
        return res

    def retrieveOne(self):
        res,self.frame_one = self.vid_one.retrieve()
        return res, self.frame_one

    def retrieveTwo(self):
        res, self.frame_two = self.vid_two.retrieve()
        return res,self.frame_two



def cutDetect(vidAnalysisComponents, ranges=list(),arguments={}):
    """
    Find a region of cut frames given the current starting point
    :param vidAnalysisComponents: VidAnalysisComponents
    :param ranges: collection of meta-data describing then range of cut frames
    :return:
    """
    diff_in_time = abs(vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.elapsed_time_two)
    if (__changeCount(vidAnalysisComponents.mask) > 0 and
                diff_in_time < vidAnalysisComponents.fps_one) or not vidAnalysisComponents.vid_two.isOpened():
        cut = {}
        cut['starttime'] = vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one
        cut['startframe'] = vidAnalysisComponents.time_manager.frameSinceBeginning
        cut['rate'] =  vidAnalysisComponents.fps_one,
        cut['type'] = 'video'
        end_time = 0
        count = 1
        cut['mask'] = vidAnalysisComponents.mask
        if type(cut['mask']) == int:
            cut['mask'] = vidAnalysisComponents.frame_one_mask
        while (vidAnalysisComponents.vid_one.isOpened()):
            ret_one, frame_one = vidAnalysisComponents.vid_one.read()
            if not ret_one:
                vidAnalysisComponents.vid_one.release()
                break
            end_time = vidAnalysisComponents.vid_one.get(cv2api_delegate.prop_pos_msec)
            vidAnalysisComponents.time_manager.updateToNow(end_time)
            diff = 0 if vidAnalysisComponents.frame_two is None else np.abs(frame_one - vidAnalysisComponents.frame_two)
            if __changeCount(diff) == 0 and vidAnalysisComponents.vid_two.isOpened():
                break
            count+=1
            if vidAnalysisComponents.time_manager.isPastTime():
                break
        cut['endtime'] = end_time
        cut['endframe'] = vidAnalysisComponents.time_manager.frameSinceBeginning
        cut['frames'] = count
        ranges.append(cut)
        return False
    return True

def addDetect(vidAnalysisComponents, ranges=list(),arguments={}):
    """
    Find a region of added frames given the current starting point
    :param vidAnalysisComponents:
    :param ranges: collection of meta-data describing then range of add frames
    :return:
    """
    frame_count_diff = vidAnalysisComponents.vid_one.get(cv2api_delegate.prop_frame_count) - \
       vidAnalysisComponents.vid_two.get(cv2api_delegate.prop_frame_count)

    diff_in_time = abs(vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.elapsed_time_two)
    if (__changeCount(vidAnalysisComponents.mask) > 0 and
                diff_in_time < vidAnalysisComponents.fps_one) or not vidAnalysisComponents.vid_one.isOpened():
        addition = {}
        addition['starttime'] = vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one
        addition['startframe'] = vidAnalysisComponents.time_manager.frameSinceBeginning
        addition['rate'] = vidAnalysisComponents.fps_one
        addition['type'] = 'video'
        end_time = None
        count = 1
        addition['mask'] = vidAnalysisComponents.mask
        if type(addition['mask']) == int:
            addition['mask'] = vidAnalysisComponents.frame_two_mask
        while (vidAnalysisComponents.vid_two.isOpened()):
            ret_two, frame_two = vidAnalysisComponents.vid_two.read()
            if not ret_two:
                vidAnalysisComponents.vid_two.release()
                break
            end_time = vidAnalysisComponents.vid_two.get(cv2api_delegate.prop_pos_msec)
            vidAnalysisComponents.time_manager.updateToNow(end_time)

            diff = 0 if vidAnalysisComponents.frame_one is None else np.abs(vidAnalysisComponents.frame_one - frame_two)
            if __changeCount(diff) == 0 and vidAnalysisComponents.vid_one.isOpened():
                break
            count+=1
            if vidAnalysisComponents.time_manager.isPastTime():
                break
        addition['endtime'] = end_time
        addition['endframe'] = addition['startframe'] + count
        addition['frames'] = count
        ranges.append(addition)
        return False
    return True

def __changeCount(mask):
    if isinstance(mask,np.ndarray):
        return __changeCount(sum(mask))
    return mask

def detectChange(vidAnalysisComponents, ranges=list(), arguments={}):
    """
       Find a region of changed frames given the current starting point
       :param vidAnalysisComponents:
       :param ranges: collection of meta-data describing then range of changed frames
       :return:
       """
    diff_in_time = abs(vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.elapsed_time_two)
    if __changeCount(vidAnalysisComponents.mask) > 0 and diff_in_time < vidAnalysisComponents.fps:
        vidAnalysisComponents.writer.write(255-vidAnalysisComponents.mask,
                                           vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one,
                                           vidAnalysisComponents.time_manager.frameSinceBeginning)
        if len(ranges) == 0 or 'endtime' in ranges[-1]:
            change = dict()
            change['mask'] = vidAnalysisComponents.mask
            change['starttime'] = vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one
            change['rate'] = vidAnalysisComponents.fps_one
            change['startframe'] = vidAnalysisComponents.time_manager.frameSinceBeginning
            change['frames'] = 1
            change['type'] = 'video'
            ranges.append(change)
        else:
            ranges[-1]['frames']+=1
    elif len(ranges) > 0 and 'endtime' not in ranges[-1]:
        change = ranges[-1]
        change['videosegment'] = os.path.split(vidAnalysisComponents.writer.filename)[1]
        change['endtime'] = vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one
        change['rate'] = vidAnalysisComponents.fps
        change['endframe'] = vidAnalysisComponents.time_manager.frameSinceBeginning
        change['type'] = 'video'
        vidAnalysisComponents.writer.release()
    return True

def cropCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None,analysis=dict()):
    """
    Determine Crop region for analysis
    :param fileOne:
    :param fileTwo:
    :param name_prefix:
    :param time_manager:
    :param arguments:
    :param analysis:
    :return:
    """
    entireVideoMaskSet = getMaskSetForEntireVideo(fileOne)
    analysis_components = VidAnalysisComponents()
    analysis_components.vid_one = cv2api_delegate.videoCapture(fileOne)
    analysis_components.vid_two = cv2api_delegate.videoCapture(fileTwo)
    analysis_components.fps = analysis_components.vid_one.get(cv2api_delegate.prop_fps)
    analysis_components.frame_one_mask = \
        np.zeros((int(analysis_components.vid_one.get(cv2api_delegate.prop_frame_height)),
                  int(analysis_components.vid_one.get(cv2api_delegate.prop_frame_width)))).astype('uint8')
    analysis_components.frame_two_mask = \
        np.zeros((int(analysis_components.vid_two.get(cv2api_delegate.prop_frame_height)),
                  int(analysis_components.vid_two.get(cv2api_delegate.prop_frame_width)))).astype('uint8')
    analysis_components.fps_one = analysis_components.vid_one.get(cv2api_delegate.prop_fps)
    analysis_components.fps_two = analysis_components.vid_two.get(cv2api_delegate.prop_fps)
    analysis_components.time_manager = time_manager
    try:
        while (analysis_components.vid_one.isOpened() and analysis_components.vid_two.isOpened()):
            ret_one = analysis_components.grabOne()
            if not ret_one:
                analysis_components.vid_one.release()
                break
            ret_two = analysis_components.grabTwo()
            if not ret_two:
                analysis_components.vid_two.release()
                break
            time_manager.updateToNow(analysis_components.elapsed_time_one)
            if time_manager.isBeforeTime():
                continue
            ret_one, frame_one = analysis_components.retrieveOne()
            ret_two, frame_two = analysis_components.retrieveTwo()
            if time_manager.isPastTime():
                break
            compare_result, analysis_result  = tool_set.cropCompare(frame_one, frame_two)
            analysis.update(analysis_result)
            # go a few more rounds?
        analysis_components.mask = 0
    finally:
        analysis_components.vid_one.release()
        analysis_components.vid_two.release()
    if analysis_components.one_count == 0:
        raise ValueError(
            'Mask Computation Failed to a read videos.  FFMPEG and OPENCV may not be installed correctly or the videos maybe empty.')
    change = {}
    change['starttime'] = 0
    change['startframe'] = 1
    change['rate'] = analysis_components.fps_one,
    change['mask'] = compare_result
    change['endtime'] = entireVideoMaskSet[0]['endtime']
    change['endframe'] =  entireVideoMaskSet[0]['endframe']
    change['frames'] = entireVideoMaskSet[0]['frames']
    return [change],[]

def cutCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None,analysis={}):
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager, cutDetect, arguments=arguments)

def pasteCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None,analysis={}):
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager, addDetect, arguments=arguments)

def detectCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None,analysis={}):
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager, detectChange, arguments=arguments)

def formMaskDiff(fileOne,
                 fileTwo,
                 name_prefix,
                 opName,
                 startSegment=None,
                 endSegment=None,
                 analysis=None,
                 alternateFunction=None,
                 arguments= {}):
    preferences = MaskGenLoader()
    diffPref = preferences['video compare']
    diffPref = arguments['video compare'] if 'video compare' in arguments else diffPref
    time_manager = tool_set.VidTimeManager(startTimeandFrame=startSegment,stopTimeandFrame=endSegment)
    if alternateFunction is not None:
        return alternateFunction(fileOne, fileTwo, name_prefix, time_manager, arguments=arguments, analysis=analysis)
    if  (diffPref is None or diffPref in ['2','ffmpeg']):
        result = __formMaskDiffWithFFMPEG(fileOne, fileTwo, name_prefix, opName, time_manager)
    else:
        result = __runDiff(fileOne, fileTwo, name_prefix,time_manager, detectChange, arguments=arguments)
    analysis['startframe'] = time_manager.getStartFrame()
    analysis['stopframe'] = time_manager.getEndFrame()
    return result

def audioWrite(fileOne, amount):
    import wave, struct, random
    count = 0
    wf = wave.open(fileOne,'wb')
    try:
        wf.setparams((2, 2, 44100, 0, 'NONE', 'not compressed'))
        while amount > 0:
            value = random.randint(-32767, 32767)
            packed_value = struct.pack('h', value)
            wf.writeframesraw(packed_value)
            amount-=1
    finally:
        wf.close()
    return count

def audioCompare(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    """
    :param fileOne:
    :param fileTwo:
    :param name_prefix:
    :param time_manager:
    :param arguments:
    :return:
    @type time_manager: VidTimeManager
    """
    import wave
    channel = arguments['Copy Stream'] if 'Copy Stream' in arguments else 'all'
    fileOneAudio,errorsone = toAudio(fileOne)
    fileTwoAudio,errorstwo = toAudio(fileTwo)
    maxdiff = None
    if 'startframe' in arguments and 'endframe' in arguments:
        maxdiff = arguments['endframe'] - arguments['startframe']
    if len(errorsone) > 0 and len(errorstwo) == 0:
        try:
            ftwo = wave.open(fileTwoAudio, 'rb')
            counttwo = ftwo.getnframes()
            startframe= time_manager.getExpectedStartFrameGiveRate(ftwo.getframerate(),defaultValue=1)
            endframe = startframe+counttwo
            return [{'startframe': startframe,
                         'starttime': float(startframe) / float(ftwo.getframerate())*1000.0,
                         'rate':ftwo.getframerate(),
                         'endframe': endframe,
                         'endtime': float(endframe) / float(ftwo.getframerate())*1000.0,
                         'type': 'audio',
                         'frames': counttwo}], []
        finally:
            ftwo.close()
    if len(errorstwo) > 0:
        return list(),errorstwo
    try:

        fone = wave.open(fileOneAudio,'rb')
        try:
            ftwo = wave.open(fileTwoAudio,'rb')
            countone = fone.getnframes()
            counttwo = ftwo.getnframes()
            onechannels = fone.getnchannels()
            twochannels = ftwo.getnchannels()
            onewidth =fone.getsampwidth()
            twowidth = ftwo.getsampwidth()
            twoskipchannel = onewidth if onechannels < twochannels else 1
            oneskipchannel = onewidth if onechannels > twochannels else 1
            startonechannel = onewidth if channel == 'right' and oneskipchannel> 1 else 0
            starttwochannel = onewidth if channel == 'right' and twoskipchannel > 1 else 0
            framerateone = fone.getframerate()
            if fone.getframerate() != ftwo.getframerate() or onewidth != twowidth:
                time_manager.updateToNow(float(countone) / float(framerateone))
                ftwo = wave.open(fileTwoAudio, 'rb')
                counttwo = ftwo.getnframes()
                startframe = time_manager.getExpectedStartFrameGiveRate(ftwo.getframerate(), defaultValue=1)
                endframe = time_manager.getExpectedEndFrameGiveRate(ftwo.getframerate(),defaultValue=counttwo)
                return [{'startframe': startframe,
                         'starttime': float(startframe) / float(ftwo.getframerate()) * 1000.0,
                         'rate': ftwo.getframerate(),
                         'endframe': endframe,
                         'endtime': float(endframe) / float(ftwo.getframerate()) * 1000.0,
                         'type': 'audio',
                         'frames': counttwo}], []
            start = None
            totalonecount = 0
            sections = []
            section = None
            block = 8192
            end = None
            while countone > 0 and counttwo > 0:
                toRead = min([block, counttwo,countone])
                framesone = fone.readframes( toRead)
                framestwo = ftwo.readframes( toRead)
                countone -= toRead
                counttwo -= toRead
                framesizeone = onewidth * onechannels
                framesizetwo = twowidth * twochannels
                for i in range(toRead):
                    totalonecount+=1
                    allone = sum([ord(c) for c in framesone[i*framesizeone + startonechannel:i*framesizeone + framesizeone:oneskipchannel]])
                    alltwo = sum([ord(c) for c in framestwo[i*framesizetwo + starttwochannel:i*framesizetwo + framesizetwo:twoskipchannel]])
                    diff = abs(allone-alltwo)
                    time_manager.updateToNow(totalonecount/float(framerateone))
                    if diff > 1:
                        if section is not None and end is not None and totalonecount-end >= framerateone:
                            section['endframe'] = end
                            section['endtime'] = float(end) / float(framerateone) * 1000.0
                            section['frames'] = end - start
                            sections.append(section)
                            section = None
                        end = totalonecount
                        if section is None:
                            start = totalonecount
                            section = {'startframe': start,
                             'starttime': float(start-1) / float(framerateone),
                             'endframe': end ,
                             'endtime': float(end) / float(framerateone),
                             'rate': framerateone,
                             'type' : 'audio',
                             'frames': 1}
                        elif maxdiff is not None and end-start > maxdiff:
                            countone = 0
                            counttwo = 0
                            break
            if section is not None:
                section['endframe'] = end
                section['endtime'] = float(end) / float(framerateone) * 1000.0
                section['frames'] = end - start
                sections.append(section)
            startframe = time_manager.getExpectedStartFrameGiveRate(float(framerateone))
            stopframe = time_manager.getExpectedEndFrameGiveRate(float(framerateone))
            errors = ['Channel selection is all however only one channel is provided.'] if channel == 'all' and onechannels > twochannels else []
            if len(sections) == 0: #or (startframe is not None and abs(sections[0]['startframe'] - startframe) > 2):
                starttime = (startframe - 1) / float(framerateone) * 1000.0
                if stopframe is None:
                    if maxdiff is not None:
                        stopframe= startframe + maxdiff
                    else:
                        stopframe = fone.getnframes()
                errors = ['Warning: Could not find sample in source media']
                sections =  [{'startframe': startframe,
                     'starttime': starttime,
                     'rate': framerateone,
                     'endframe':stopframe,
                     'type': 'audio',
                     'endtime': float(stopframe) / float(framerateone)*1000.0,
                     'frames': stopframe-startframe}
                ]
            return sections,errors
        finally:
            ftwo.close()
    finally:
        fone.close()
    return [],['Unable to open one of the audio streams']

def audioSample(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    """
    :param fileOne:
    :param fileTwo:
    :param name_prefix:
    :param time_manager:
    :param arguments:
    :return:
    @type time_manager: VidTimeManager
    """
    import wave
    fileOneAudio,errorsone = toAudio(fileOne)
    fileTwoAudio,errorstwo = toAudio(fileTwo)
    channel = arguments['Copy Stream'] if 'Copy Stream' in arguments else 'all'
    try:
        fone = wave.open(fileOneAudio,'rb')
        try:
            ftwo = wave.open(fileTwoAudio,'rb')
            countone = fone.getnframes()
            counttwo = ftwo.getnframes()
            onechannels = fone.getnchannels()
            twochannels = ftwo.getnchannels()
            onewidth =fone.getsampwidth()
            twowidth = ftwo.getsampwidth()
            framerateone = fone.getframerate()
            frameratetwo = ftwo.getframerate()
            if fone.getframerate() != ftwo.getframerate() or onewidth != twowidth:
                time_manager.updateToNow(float(counttwo) / float(frameratetwo))
                return [{'startframe': 1,
                         'starttime': 0,
                         'rate':frameratetwo,
                         'endframe': counttwo,
                         'type':'audio',
                         'endtime': float(counttwo) / float(frameratetwo)*1000.0,
                         'frames': counttwo}], []
            framesizetwo = twowidth * twochannels
            framesizeone = onewidth * onechannels
            block = 8192
            toReadTwo = min([block, counttwo])
            framestwo = ftwo.readframes(toReadTwo)
            toReadOne = min([toReadTwo * 2, countone])
            framesone = fone.readframes(toReadOne)
            position = -1
            framestwolen = len(framestwo)
            skip=onewidth if onechannels != twochannels else 1
            start=onewidth if channel == 'right' else 0
            alltwo = sum([ord(c) for c in framestwo])
            while toReadOne > 0 and toReadTwo > 0 and position < 0 and not time_manager.isPastStartTime():
                countone -= toReadOne
                time_manager.updateToNow((fone.getnframes() - countone) / float(framerateone)*1000.0, frames=toReadOne)
                if not time_manager.isBeforeTime():
                    allone = sum([ord(c) for c in framesone[ start:start + framestwolen * skip:skip]])
                    for i in range(toReadTwo):
                        if i > 0:
                            # adjust allone by one frame
                            allone = allone - \
                                     sum([ord(c) for c in framesone[
                                    (i-1)* framesizeone + start:i* framesizeone + start:skip]]) + \
                                     sum([ord(c) for c in framesone[
                                    (i - 1)* framesizeone + framestwolen*skip + start:i * framesizeone + framestwolen*skip + start:skip]])
                        diff = abs(allone - alltwo)
                        if diff == 0:
                            position = i
                            break
                toReadOne = min(countone,toReadTwo)
                if toReadOne >= toReadTwo:
                    framesone = framesone[framestwolen*skip:] + fone.readframes(toReadOne)
            if position < 0:
                startframe = time_manager.getExpectedStartFrameGiveRate(float(framerateone), defaultValue =1)
                errors = ['Warning: Could not find sample in source media']
            else:
                startframe =  position
                errors = []
            starttime = (startframe-1) / float(framerateone)*1000.0
            return [{'startframe': startframe,
                     'starttime': starttime,
                     'rate': framerateone,
                     'endframe': startframe + ftwo.getnframes(),
                     'type': 'audio',
                     'endtime': float(startframe + ftwo.getnframes()) / float(framerateone)*1000.0,
                     'frames': ftwo.getnframes()}], errors
        finally:
            ftwo.close()
    finally:
        fone.close()
    return [],['Unable to open one of the audio streams']


def audioDelete(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    """
    :param fileOne:
    :param fileTwo:
    :param name_prefix:
    :param time_manager:
    :param arguments:
    :return:
    @type time_manager: VidTimeManager
    """
    import wave
    fileOneAudio,errorsone = toAudio(fileOne)
    fileTwoAudio,errorstwo = toAudio(fileTwo)
    channel = arguments['Copy Stream'] if 'Copy Stream' in arguments else 'all'
    try:
        fone = wave.open(fileOneAudio,'rb')
        try:
            ftwo = wave.open(fileTwoAudio,'rb')
            countone = fone.getnframes()
            counttwo = ftwo.getnframes()
            onechannels = fone.getnchannels()
            twochannels = ftwo.getnchannels()
            onewidth =fone.getsampwidth()
            twowidth = ftwo.getsampwidth()
            framerateone = fone.getframerate()
            if fone.getframerate() != ftwo.getframerate() or onewidth != twowidth:
                time_manager.updateToNow(float(countone) / float(framerateone))
                return [{'startframe': 1,
                         'starttime': 0,
                         'rate':framerateone,
                         'endframe': countone,
                         'type':'audio',
                         'endtime': float(countone) / float(framerateone),
                         'frames': countone}], []
            toRead = min([2048, countone, counttwo])
            framestwo = ftwo.readframes(toRead)
            framesone = fone.readframes(toRead)
            skip=onewidth if onechannels != twochannels else 1
            start=onewidth if channel == 'right' else 0
            mismatches = []
            while toRead > 0 and len(mismatches) == 0:
                mismatches = [i for i in range(len(framestwo)) if framestwo[i] != framesone[i*skip+start]]
                countone -=  toRead
                counttwo -= toRead
                toRead = min([2048, countone, counttwo])
                framestwo = ftwo.readframes(toRead)
                framesone = fone.readframes(toRead)
            if len(mismatches) > 0:
                startframe = mismatches[0]/twowidth
            else:
                startframe = ftwo.getnframes() - fone.getnframes()
            starttime = (startframe-1) / float(framerateone)
            return [{'startframe': startframe,
                     'starttime': starttime,
                     'rate': framerateone,
                     'endframe': startframe + ftwo.getnframes(),
                     'type': 'audio',
                     'endtime': float(startframe + ftwo.getnframes()) / float(framerateone),
                     'frames': ftwo.getnframes()}], []
        finally:
            ftwo.close()
    finally:
        fone.close()

def __runDiff(fileOne, fileTwo, name_prefix, time_manager, opFunc, arguments={}):
    """
      compare frame to frame of each video
     :param fileOne:
     :param fileTwo:
     :param name_prefix:
     :param time_manager:
     :param opFunc: analysis function applied to each frame
     :param arguments:
     :return:
     @type time_manager: VidTimeManager
     """
    analysis_components = VidAnalysisComponents()
    analysis_components.vid_one = cv2api_delegate.videoCapture(fileOne)
    analysis_components.vid_two = cv2api_delegate.videoCapture(fileTwo)
    analysis_components.fps = analysis_components.vid_one.get(cv2api_delegate.prop_fps)
    analysis_components.frame_one_mask = \
        np.zeros((int(analysis_components.vid_one.get(cv2api_delegate.prop_frame_height)),
                  int(analysis_components.vid_one.get(cv2api_delegate.prop_frame_width)))).astype('uint8')
    analysis_components.frame_two_mask = \
        np.zeros((int(analysis_components.vid_two.get(cv2api_delegate.prop_frame_height)),
                  int(analysis_components.vid_two.get(cv2api_delegate.prop_frame_width)))).astype('uint8')
    analysis_components.fps_one = analysis_components.vid_one.get(cv2api_delegate.prop_fps)
    analysis_components.fps_two = analysis_components.vid_two.get(cv2api_delegate.prop_fps)
    analysis_components.writer = tool_set.GrayBlockWriter(name_prefix,
                                                  analysis_components.vid_one.get(cv2api_delegate.prop_fps))
    analysis_components.time_manager = time_manager
    ranges = list()
    try:
        done = False
        while (analysis_components.vid_one.isOpened() and analysis_components.vid_two.isOpened()):
            ret_one = analysis_components.grabOne()
            if not ret_one:
                analysis_components.vid_one.release()
                break
            ret_two = analysis_components.grabTwo()
            if not ret_two:
                analysis_components.vid_two.release()
                break
            time_manager.updateToNow(analysis_components.elapsed_time_one)
            if time_manager.isBeforeTime():
                continue
            ret_one, frame_one =analysis_components.retrieveOne()
            ret_two, frame_two = analysis_components.retrieveTwo()
            if time_manager.isPastTime():
                break
            diff = np.abs(frame_one - frame_two)
            analysis_components.mask = np.zeros((frame_one.shape[0],frame_one.shape[1])).astype('uint8')
            diff  = cv2.cvtColor(diff,cv2.COLOR_RGBA2GRAY)
            analysis_components.mask[diff > 0.0001] = 255
            #opening = cv2.erode(analysis_components.mask, kernel,1)
            #analysis_components.mask = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
            if not opFunc(analysis_components,ranges,arguments):
                done = True
                break
        analysis_components.mask = 0
        if analysis_components.grabbed_one and analysis_components.frame_one is None:
            analysis_components.retrieveOne()
        if analysis_components.grabbed_two and analysis_components.frame_two is None:
            analysis_components.retrieveTwo()
        if not done:
            opFunc(analysis_components,ranges,arguments)
        analysis_components.writer.release()
    finally:
        analysis_components.vid_one.release()
        analysis_components.vid_two.release()
        analysis_components.writer.close()
    if analysis_components.one_count == 0:
        raise ValueError(
            'Mask Computation Failed to a read videos.  FFMPEG and OPENCV may not be installed correctly or the videos maybe empty.')
    return ranges,[]

def __getVideoFrame(video, frame_time):
    while video.isOpened():
        ret = video.grab()
        if not ret:
            break
        elapsed_time = video.get(cv2api_delegate.prop_pos_msec)
        if elapsed_time >= frame_time:
            ret,frame = video.retrieve()
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
            rate = reader.fps
            change = dict()
            destination_video = cv2api_delegate.videoCapture(dest_file_name)
            reader = tool_set.GrayBlockReader(os.path.join(directory,
                                                                    mask_set['videosegment']))
            try:
                writer = tool_set.GrayBlockWriter(os.path.join(directory,mask_file_name_prefix),
                                                  reader.fps)

                try:
                    first_mask = None
                    count = 0
                    vid_frame_time=0
                    max_analysis = 0
                    while True:
                        frame_time = reader.current_frame_time()
                        frame_no = reader.current_frame()
                        mask = reader.read()
                        if mask is None:
                            break
                        if frame_time < vid_frame_time:
                            continue
                        frame,vid_frame_time = __getVideoFrame(destination_video, frame_time)
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
                                change['rate'] = rate
                                change['type'] = 'video'
                                change['startframe'] = frame_no
                                first_mask = new_mask
                        count+=1
                        writer.write(new_mask,vid_frame_time,frame_no)
                        if max_analysis > 10:
                            break
                    change['endtime'] = vid_frame_time
                    change['endframe'] = frame_no
                    change['frames'] = count
                    change['rate'] = rate
                    change['type'] = 'video'
                    change['videosegment'] = os.path.split(writer.filename)[1]
                    if first_mask is not None:
                        new_mask_set.append(change)
                finally:
                    writer.close()
            finally:
                reader.close()
                destination_video.release()
        return new_mask_set,[]
    # Masks cannot be generated for video to video....yet
    return [],[]


def dropFramesFromMask(bounds,
                       video_masks,
                       keepTime = False,
                       expectedType = 'video'):
    """
    slide frames back given start and end removal times
    :param start_time: start time of removed frames
    :param end_time: end time of removed frmes
    :param directory:
    :param video_masks:
    :param keepTime: If True, then frame times and counts do not change ( in the case of an overlay ).  Essentially
    just dropping intersecting masks
    :return: new set of video masks
    """
    def dropFrameFromMask(bound,
                          video_masks,
                          keepTime=False,
                          expectedType='video'
                          ):
        import time
        drop_sf = bound['startframe'] if 'startframe' in bound else 1
        drop_ef = bound['endframe'] if 'endframe' in bound and bound['endframe'] > 0 else None
        new_mask_set = []
        for mask_set in video_masks:
            if 'type' in mask_set and mask_set['type'] != expectedType:
                new_mask_set.append(mask_set)
                continue
            mask_sf = mask_set['startframe']
            mask_ef = mask_set['endframe'] if 'endframe' in mask_set or mask_set['endframe'] == 0 else None
            rate = mask_set['rate']
            if   mask_ef is not None and drop_sf - mask_ef > 0:
                new_mask_set.append(mask_set)
                continue
            if (drop_ef is None or (mask_ef is not None and drop_ef - mask_ef >= 0)) and \
                    (drop_sf - mask_sf <=0):
                # started after drop and subsummed by drop
                continue
            #occurs after drop region and time is not alterered
            if keepTime and drop_ef is not None and drop_ef - mask_sf <= 0:
                new_mask_set.append(mask_set)
                continue
            if 'videosegment' not in mask_set:
                new_mask_set.extend(dropFramesWithoutMask([bound],[mask_set],keepTime=keepTime))
                continue
            mask_file_name = mask_set['videosegment']
            reader = tool_set.GrayBlockReader(mask_set['videosegment'])
            mask_file_name_prefix = mask_file_name[0:mask_file_name.rfind('.')] + str(time.clock())
            writer = tool_set.GrayBlockWriter(mask_file_name_prefix,
                                                  reader.fps)
            if keepTime:
                elapsed_count = 0
                elapsed_time = 0
            else:
                if drop_ef is not None:
                    elapsed_time = bound['endtime'] - bound['starttime']
                    elapsed_count = drop_ef - drop_sf
                else:
                    elapsed_time = 0
                    elapsed_count = 0
            try:
                startcount = mask_set['startframe']
                starttime = mask_set['starttime']
                skipRead = False
                written_count = 0
                diff_sf = drop_sf - mask_sf
                # if mask starts before drop, then write out some of the mask
                if diff_sf > 0:
                    while True:
                        last_time = reader.current_frame_time()
                        frame_count = reader.current_frame()
                        mask = reader.read()
                        if mask is None:
                            break
                        diff_current = drop_sf - frame_count
                        if diff_current <= 0:
                            skipRead = True
                            break
                        writer.write(mask, last_time,frame_count)
                        written_count += 1
                    if written_count > 0:
                            change = dict()
                            change['starttime'] = starttime
                            change['type'] = mask_set['type']
                            change['startframe'] = startcount
                            change['endtime'] = bound['starttime']
                            change['endframe'] = frame_count
                            change['frames'] = diff_sf
                            change['rate'] = rate
                            change['videosegment'] = writer.filename
                            new_mask_set.append(change)
                            writer.release()
                # else: covers the case of start occuring before OR after the end of the drop
                starttime = None
                written_count = 0
                if drop_ef is not None and drop_ef - mask_ef < 0:
                    while True:
                        if skipRead:
                            skipRead = False
                        else:
                            last_time = reader.current_frame_time()
                            frame_count = reader.current_frame()
                            mask = reader.read()
                        if mask is None:
                            break
                        diff_ef = drop_ef - frame_count
                        # if diff_ef > 0, then the start occured before the drop
                        if diff_ef <= 0:
                            if starttime is None:
                                starttime = last_time - elapsed_time
                            writer.write(mask, last_time - elapsed_time, drop_ef + written_count)
                            written_count += 1
                if written_count > 0:
                    change = dict()
                    change['starttime'] = starttime
                    change['type'] = mask_set['type']
                    change['startframe'] = mask_set['endframe'] - elapsed_count - written_count
                    change['endtime'] = mask_set['endtime'] - elapsed_time
                    change['endframe'] = mask_set['endframe'] - elapsed_count
                    change['frames'] = written_count
                    change['rate'] = rate
                    change['videosegment'] = writer.filename
                    new_mask_set.append(change)
                    writer.release()
            finally:
                reader.close()
                writer.close()
        return new_mask_set
    new_mask_set = video_masks
    for bound in bounds:
        new_mask_set = dropFrameFromMask(bound,new_mask_set,keepTime=keepTime,expectedType=expectedType)
    return new_mask_set

def dropFramesWithoutMask(bounds,
                       video_masks,
                       keepTime = False,
                       expectedType = 'video'):
    """
    slide frames back given start and end removal times
    :param start_time: start time of removed frames
    :param end_time: end time of removed frmes
    :param directory:
    :param video_masks:
    :param keepTime: If True, then frame times and counts do not change ( in the case of an overlay ).  Essentially
    just dropping intersecting masks
    :return: new set of video masks
    """
    def dropFramesWithoutMaskBound(bound,
                       video_masks,
                       keepTime = False,
                       expectedType = 'video'):
        drop_sf = bound['startframe'] if 'startframe' in bound else 1
        drop_ef = bound['endframe'] if 'endframe' in bound and bound['endframe'] > 0 else None
        new_mask_set = []
        for mask_set in video_masks:
            if 'type' in mask_set and mask_set['type'] != expectedType:
                new_mask_set.append(mask_set)
                continue
            mask_sf = mask_set['startframe']
            mask_ef = mask_set['endframe'] if 'endframe' in mask_set or mask_set['endframe'] == 0 else None
            rate = mask_set['rate']
            # before remove region
            if drop_sf - mask_ef > 0:
                new_mask_set.append(mask_set)
                continue
                # at the end and time is not change
            if keepTime and drop_ef is not None and (drop_ef - mask_sf) <= 0:
                new_mask_set.append(mask_set)
                continue
            if (drop_ef is None or (mask_ef is not None and drop_ef - mask_ef >= 0)) and \
                    (drop_sf - mask_sf <= 0):
                # started after drop and subsummed by drop
                continue
            #occurs after drop region
            start_diff_frame = drop_sf - mask_sf
            if start_diff_frame > 0:
                change = dict()
                change['starttime'] = mask_set['starttime']
                change['type'] = mask_set['type']
                change['startframe'] = mask_set['startframe']
                change['endtime'] = mask_set['starttime'] + start_diff_frame*1000/rate
                change['endframe'] = mask_set['startframe'] + start_diff_frame
                change['frames'] = change['endframe'] - change['startframe']
                change['rate'] = rate
                new_mask_set.append(change)
            if drop_ef is not None:
                 end_diff_frame = drop_ef  - mask_ef
                 if end_diff_frame < 0:
                    end_adjust_frame = drop_ef - drop_sf
                    change = dict()
                    if keepTime:
                        change['starttime'] = bound['endtime']
                        change['startframe'] = drop_ef
                        change['type'] = mask_set['type']
                        change['endframe'] = mask_set['endframe']
                        change['endtime'] = mask_set['endtime']
                        change['frames'] = change['endframe'] - change['startframe']
                        change['rate'] = rate
                    else:
                        if drop_ef - mask_sf <= 0:
                            change['startframe'] = mask_set['startframe'] -  end_adjust_frame
                            change['starttime'] =  mask_set['starttime'] -  end_adjust_frame*1000/rate
                        else:
                            change['starttime']  = bound['starttime']
                            change['startframe'] = bound['startframe']
                        change['endtime'] = mask_set['endtime'] -  end_adjust_frame*1000/rate
                        change['endframe'] = mask_set['endframe'] -  end_adjust_frame
                        change['frames'] = change['endframe'] - change['startframe']
                        change['type'] = mask_set['type']
                    change['rate'] = rate
                    new_mask_set.append(change)
        return new_mask_set
    new_mask_set = video_masks
    for bound in bounds:
        new_mask_set = dropFramesWithoutMaskBound(bound, new_mask_set, keepTime=keepTime, expectedType=expectedType)
    return new_mask_set

def insertFramesToMask(bounds,
                       video_masks,
                       expectedType='video'):
    """
    Slide mask frames forward to accomodate inserted frames given the insertion start and end time
    :param start_time: insertion start time.
    :param end_time:insertion end time.
    :param directory:
    :param video_masks:
    :return: new set of video masks
    """
    import time
    def insertFramesToMaskForBound(bound,
                       video_masks,
                       expectedType='video'):
        add_sf = bound['startframe'] if 'startframe' in bound else 1
        add_ef = bound['endframe'] if 'endframe' in bound and bound['endframe'] > 0 else None
        add_st = bound['starttime'] if 'starttime' in bound else 0
        add_et = bound['endtime'] if 'endtime' in bound and bound['endtime'] > 0 else None
        new_mask_set = []
        for mask_set in video_masks:
            if 'type' in mask_set and mask_set['type'] != expectedType:
                new_mask_set.append(mask_set)
                continue
            mask_sf = mask_set['startframe']
            mask_ef = mask_set['endframe'] if 'endframe' in mask_set or mask_set['endframe'] == 0 else None
            rate = mask_set['rate']
            if  add_sf - mask_ef > 0:
                new_mask_set.append(mask_set)
                continue
            if 'videosegment' not in  mask_set:
                new_mask_set.extend(insertFramesWithoutMask([bound],[mask_set]))
                continue
            mask_file_name = mask_set['videosegment']
            reader = tool_set.GrayBlockReader(mask_set['videosegment'])
            mask_file_name_prefix = mask_file_name[0:mask_file_name.rfind('.')] + str(time.clock())
            writer = tool_set.GrayBlockWriter( mask_file_name_prefix,
                                                  reader.fps)
            if add_ef is None:
                elapsed_time = 0
                elapsed_count = 0
            else:
                elapsed_count = add_ef - add_sf
                elapsed_time = add_et - add_st
            try:
                # deal with the case where the mask starts before the added section and end after
                count = mask_set['startframe']
                written_count = 0
                skipread = False
                startcount = count
                if add_sf - mask_sf > 0:
                    while True:
                        frame_count = reader.current_frame()
                        frame_time = reader.current_frame_time()
                        mask = reader.read()
                        if mask is None:
                            break
                        diff_sf = add_sf - frame_count
                        if diff_sf <= 0:
                            skipread = True
                            break
                        writer.write(mask, frame_time, frame_count)
                        written_count += 1
                        count += 1
                    if written_count > 0:
                        change = dict()
                        change['starttime'] = mask_set['starttime']
                        change['startframe'] = mask_set['startframe']
                        change['endtime'] = frame_time
                        change['endframe'] = startcount + written_count
                        change['frames'] = written_count
                        change['rate'] = rate
                        change['type'] = mask_set['type']
                        change['videosegment'] = writer.filename
                        new_mask_set.append(change)
                        writer.release()
                    written_count = 0
                starttime = None
                while True:
                    if not skipread:
                         frame_count = reader.current_frame()
                         frame_time = reader.current_frame_time()
                         mask = reader.read()
                    else:
                        skipread = False
                    if starttime is None:
                        starttime = frame_time + elapsed_time
                        startcount = frame_count + elapsed_count
                    if mask is None:
                        break
                    writer.write(mask, frame_time + elapsed_time,frame_count + elapsed_count)
                    written_count += 1
                if written_count > 0:
                    change = dict()
                    change['starttime'] = starttime
                    change['startframe'] = startcount
                    change['endtime'] =  mask_set['endtime'] + elapsed_time
                    change['endframe'] = startcount + written_count
                    change['frames'] = written_count
                    change['rate'] = rate
                    change['type'] = mask_set['type']
                    change['videosegment'] = writer.filename
                    new_mask_set.append(change)
                    writer.release()
            finally:
                reader.close()
                writer.close()
        return new_mask_set

    new_mask_set = video_masks
    for bound in bounds:
        new_mask_set = insertFramesToMaskForBound(bound, new_mask_set,  expectedType=expectedType)
    return new_mask_set


def _maskTransform( video_masks, func, expectedType='video'):
    """
    Crop masks
    :param start_time: insertion start time.
    :param end_time:insertion end time.
    :param directory:
    :param video_masks:
    :return: new set of video masks
    """
    import time
    new_mask_set = []
    for mask_set in video_masks:
        if 'type' in mask_set and mask_set['type'] != expectedType:
            new_mask_set.append(mask_set)
            continue
        change = dict()
        change['starttime'] = mask_set['starttime']
        change['startframe'] = mask_set['startframe']
        change['endtime'] = mask_set['endtime']
        change['endframe'] =mask_set['endframe']
        change['frames'] = mask_set['frames']
        change['type'] = mask_set['type']
        change['rate'] = mask_set['rate']
        change['videosegment'] = mask_set['videosegment']
        try:
            mask_file_name = mask_set['videosegment']
            reader = tool_set.GrayBlockReader(mask_set['videosegment'])
            mask_file_name_prefix = mask_file_name[0:mask_file_name.rfind('.')] + str(time.clock())
            writer = tool_set.GrayBlockWriter( mask_file_name_prefix,
                                                  reader.fps)
            while True:
                frame_time = reader.current_frame_time()
                frame_count = reader.current_frame()
                mask = reader.read()
                if mask is None:
                    break
                mask = func(mask)
                writer.write(mask, frame_time, frame_count)
            change['videosegment'] = writer.filename
            new_mask_set.append(change)
        except Exception as e:
            logging.getLogger('maskgen').error('Failed to transform {} using {}'.format(mask_set['videosegment'],
                                                                                        str(func)))
            logging.getLogger('maskgen').error(e)
        finally:
            reader.close()
            writer.close()
    return new_mask_set

def get_video_orientation_change(source, target):
    source_data = getMeta(source, show_streams=True)[0]
    donor_data = getMeta(target, show_streams=True)[0]

    def get_channel_data(source_data, codec_type):
        for data in source_data:
            if data['codec_type'] == codec_type:
                return data

    def orient_rotation_positive(rotate):
        rotate = -rotate
        if rotate < 0:
            rotate = 360 + rotate
        return rotate

    def get_item(data, item, default_value):
        if data is None or item not in data:
            return default_value
        return data[item]

    source_channel_data = get_channel_data(source_data, 'video')
    target_channel_data = get_channel_data(donor_data, 'video')

    return int(get_item(target_channel_data, 'rotation', 0)) - int(get_item(source_channel_data, 'rotation', 0))

def insertMask(video_masks,box, size):
    """
    Insert mask insize larger mask
    :param directory
    :param video_masks
    :param box - tuple (upper left x, upper left y, lower right x , lower right y)
    :param size of the new mask
    :return: new set of video masks
    """
    from functools import partial
    def insertMaskWithBox(box,size,mask):
        newRes = np.zeros(size).astype('uint8')
        newRes[box[0]:box[2], box[1]:box[3]] = mask[0:(box[2] - box[0]), 0:(box[3] - box[1])]
        return newRes
    return _maskTransform(video_masks,partial(insertMaskWithBox,box,size))

def cropMask(video_masks, box):
    """
    Crop masks
    :param directory
    :param video_masks
    :param box - tuple (upper left x, upper left y, lower right x , lower right y)
    """
    from functools import partial
    def croptMaskWithBox(box, mask):
        return mask[box[0]:box[2], box[1]:box[3]]

    return _maskTransform(video_masks, partial(croptMaskWithBox, box))


def flipMask(video_masks, size, direction):
    """
    resize mask
    :param directory
    :param video_masks
    :param size of the new mask
    :return: new set of video masks
    """
    from functools import partial
    def flipMaskGivenSize(size, direction, mask):
         return cv2.flip(mask, 1 if direction == 'horizontal' else (-1 if direction == 'both' else 0))
    return _maskTransform(video_masks, partial(flipMaskGivenSize, size, direction))

def resizeMask(video_masks, size):
    """
    resize mask
    :param directory
    :param video_masks
    :param size of the new mask
    :return: new set of video masks
    """
    from functools import partial
    def resizeMaskGivenSize(size, mask):
         return cv2.resize(mask, size)
    return _maskTransform(video_masks, partial(resizeMaskGivenSize, size))

def rotateMask(degrees,video_masks, expectedDims=None,cval = 0):
    """
    resize mask
    :param directory
    :param video_masks
    :param size of the new mask
    :return: new set of video masks
    """
    from functools import partial
    def rotateMaskGivenDegrees(degrees, cval, expectedDims, mask):
         return tool_set.__rotateImage(degrees, mask,expectedDims=expectedDims,cval=cval)
    return _maskTransform(video_masks, partial(rotateMaskGivenDegrees,degrees,cval,expectedDims))

def insertFramesWithoutMask(bounds,
                       video_masks,
                       expectedType='video'):
    """
       slide frames back given start and end removal times
       :param start_time: start time of removed frames
       :param end_time: end time of removed frmes
       :param directory:
       :param video_masks:
       :param keepTime: If True, then frame times and counts do not change ( in the case of an overlay ).  Essentially
       just dropping intersecting masks
       :return: new set of video masks
    """
    def insertFramesWithoutMaskForBound(bound,
                       video_masks,
                       expectedType='video'):
        add_sf = bound['startframe'] if 'startframe' in bound else 1
        add_ef = bound['endframe'] if 'endframe' in bound and bound['endframe'] > 0 else None
        add_st = bound['starttime'] if 'starttime' in bound else 0
        add_et = bound['endtime'] if 'endtime' in bound and bound['endtime'] > 0 else None
        new_mask_set = []
        for mask_set in video_masks:
            if 'type' in mask_set and mask_set['type'] != expectedType:
                new_mask_set.append(mask_set)
                continue
            mask_sf = mask_set['startframe']
            mask_ef = mask_set['endframe'] if 'endframe' in mask_set or mask_set['endframe'] == 0 else None
            rate = mask_set['rate']
            #before addition
            if add_sf - mask_ef > 0:
                new_mask_set.append(mask_set)
                continue
            start_diff_count= add_sf - mask_sf
            end_adjust_count = add_ef - add_sf if add_ef is not None else -1
            end_adjust_time = add_et - add_st if add_ef is not None else -1
            if start_diff_count > 0:
                change = dict()
                change['starttime'] = mask_set['starttime']
                change['startframe'] = mask_set['startframe']
                change['endtime'] = mask_set['starttime'] + start_diff_count/1000.0 * rate
                change['endframe'] = mask_set['startframe'] + start_diff_count
                change['frames'] = change['endframe'] - change['startframe']
                change['type'] = mask_set['type']
                change['rate'] = rate
                new_mask_set.append(change)
                if end_adjust_count >= 0:
                    change = dict()
                    change['starttime'] =  add_et
                    change['startframe'] = add_ef
                    change['endtime'] = mask_set['endtime'] + end_adjust_count/1000.0 * rate
                    change['endframe'] = mask_set['endframe'] + end_adjust_count
                    change['frames'] = change['endframe'] - change['startframe']
                    change['rate'] = rate
                    change['type'] = mask_set['type']
                    new_mask_set.append(change)
            elif end_adjust_count >= 0:
                change = dict()
                change['starttime'] = mask_set['starttime'] +  end_adjust_time
                change['startframe'] = mask_set['startframe'] + end_adjust_count
                change['endtime'] = mask_set['endtime'] + end_adjust_time
                change['endframe'] = mask_set['endframe'] + end_adjust_count
                change['frames'] = change['endframe'] - change['startframe']
                change['rate'] = rate
                change['type'] = mask_set['type']
                new_mask_set.append(change)
        return new_mask_set

    new_mask_set = video_masks
    for bound in bounds:
        new_mask_set = insertFramesWithoutMaskForBound(bound, new_mask_set, expectedType=expectedType)
    return new_mask_set

def pullFrameNumber(video_file, frame_number):
    """

    :param video_file:
    :param frame_number:
    :return:
    """

    frame = None
    video_capture = cv2api_delegate.videoCapture(video_file)
    while (video_capture.isOpened() and frame_number > 0):
        ret = video_capture.grab()
        if not ret:
            break
        frame_number-=1
    ret, frame = video_capture.retrieve()
    elapsed_time = video_capture.get(cv2api_delegate.prop_pos_msec)
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
