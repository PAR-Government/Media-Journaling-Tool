# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import logging
import os
import time
from subprocess import Popen, PIPE
from threading import RLock
from maskgen import exif


import cv2
import ffmpeg_api
import numpy as np
import tool_set
from cachetools import LRUCache
from cachetools import cached
from cachetools.keys import hashkey
from cv2api import cv2api_delegate
from image_wrap import ImageWrapper
from maskgen_loader import  MaskGenLoader
from support import getValue

global meta_cache
global count_cache
meta_lock = RLock()
count_lock = RLock()
meta_cache = LRUCache(maxsize=124)
count_cache = LRUCache(maxsize=124)


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


def __build_histogram_for_single_frame(filename):
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


def __build_masks_from_videofile(filename, histandcount):
    maskprefix = os.path.splitext(filename)[0]
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
            totalMatch += np.sum(matches)
            result[matches] = 0
        if totalMatch > 0:
            elapsed_time = cap.get(cv2api_delegate.prop_pos_msec)
            cv2.imwrite(maskprefix + '_mask_' + str(elapsed_time) + '.png', gray)
            break
    cap.release()


def build_masks_from_combined_video_not_used(filename):
    h, pc = __build_histogram_for_single_frame(filename)
    hist = h / pc
    return __build_masks_from_videofile(filename, hist)

def get_frames_from_segment(segment):
    if 'frames' not in segment:
        if 'rate' in segment or ('startframe' in segment and 'endframe' in segment):
            return get_end_frame_from_segment(segment) - get_start_frame_from_segment(segment)
        return 1
    return segment['frames']

def get_start_frame_from_segment(segment):
    from math import floor
    if 'startframe' not in segment:
        rate = get_rate_from_segment(segment)
        segment['startframe'] = int(floor(segment['starttime']*rate/1000.0)) + 1
    return segment['startframe']

def get_end_frame_from_segment(segment):
    from math import floor
    if 'endframe' not in segment:
        rate = get_rate_from_segment(segment)
        segment['endframe'] = int(floor(segment['endtime']*rate/1000.0))
    return segment['endframe']

def get_start_time_from_segment(segment):
    if 'starttime' not in segment:
        segment['starttime'] = (segment['startframe']-1)*1000.0/segment['rate']
    return segment['starttime']

def get_end_time_from_segment(segment):
    if 'endtime' not in segment:
        segment['endtime'] = segment['endframe']*1000.0/segment['rate']
    return segment['endtime']

def get_rate_from_segment(segment):
    if 'rate' not in segment:
        segment['rate'] = (segment['endtime'] - segment['starttime'])/float(segment['frames'])
    return segment['rate']

def build_masks_from_green_mask(filename, time_manager, fidelity=1, morphology=True):
    """

    :param filename: str
    :param time_manager: tool_set.VidTimeManager
    :return:
    """
    capIn = cv2api_delegate.videoCapture(filename)
    capOut = tool_set.GrayBlockWriter(os.path.splitext(filename)[0],
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
            result[abs(thresh) > fidelity] = 255
            if morphology:
                opening = cv2.morphologyEx(result, cv2.MORPH_OPEN, kernel)
                closing = cv2.morphologyEx(opening, cv2.MORPH_CLOSE, kernel)
                result = closing
            totalMatch = np.sum(abs(result) > 1)
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
                         'endframe': time_manager.frameSinceBeginning-1,
                         'frames': count,
                         'rate': capIn.get(cv2api_delegate.prop_fps),
                         'mask': sample,
                         'type':'video',
                         'videosegment': os.path.split(capOut.filename)[1]})
                    capOut.release()
                    count = 0
                startTime = None
            last_time = elapsed_time
        if startTime is not None:
            ranges.append({'starttime': startTime,
                           'endtime': last_time,
                           'startframe': startFrame,
                           'endframe': time_manager.frameSinceBeginning-1,
                           'frames': time_manager.frameSinceBeginning-startFrame,
                           'rate': capIn.get(cv2api_delegate.prop_fps),
                           'mask': sample,
                           'type': 'video',
                           'videosegment': os.path.split(capOut.filename)[1]})
            capOut.release()
    finally:
        capIn.release()
        capOut.close()
    if amountRead == 0:
        raise ValueError('Mask Computation Failed to a read videos.  FFMPEG and OPENCV may not be installed correctly or the videos maybe empty.')
    return ranges


def __invert_mask_from_segment(segmentFileName, prefix):
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
        maskdata['videosegment'] = __invert_mask_from_segment(maskdata['videosegment'], prefix)
        result.append(maskdata)
    return result


global loaded_codecs
loaded_codecs = None
def get_valid_codecs(codec_type='video'):
    """
    Returns a list of valid Codecs given a string determining which type of codec.
    :param codec_type: string, determines kind of codec.
    :returns: a list of strings, codec names.
    """
    global loaded_codecs
    if loaded_codecs is None:
        codecs = (ffmpeg_api.run_ffmpeg(['-codecs'], False).split("\n")[10:-1]
              + ffmpeg_api.run_ffmpeg(['-encoders'], False).split("\n")[10:-1])
        loaded_codecs = {'audio':[],'video':[]}
        for line in codecs:
            for codec_type_sel in ['audio','video']:
                codec = parse_codec_list(line, codec_type_sel)
                if codec is not None and len(codec) > 0:
                    loaded_codecs[codec_type_sel].append(codec)
    return loaded_codecs[codec_type]

def parse_codec_list(line, codec_type='video'):
    """
    Parse through ffmpegs codec lists
    :param line: string to parse
    :param codecType: string of which codec type to look for.
    :returns: string of codec name
    """
    query = "V" if codec_type == 'video' else "A"
    testOne = "E" in line[1:7] and query in line[1:7]
    testTwo = query == line[1:7][0]
    if testOne or testTwo:
        return str.strip(line[8:29])
    else:
        return ''


def get_shape_of_video(video_file):
    """

    :param video_file:
    :return: width,height
    """
    meta, frames = ffmpeg_api.get_meta_from_video(video_file, show_streams=True)
    width = 0
    height =0
    for item in meta:
        if 'width' in item:
            width = int(item['width'])
        if 'height' in item:
            height = int(item['height'])
    return width,height

def get_frame_count_only(video_file):
    meta, frames = ffmpeg_api.get_meta_from_video(video_file, show_streams=True, with_frames=True, media_types=['video'])
    index = ffmpeg_api.get_stream_indices_of_type(meta, 'video')[0]
    return len(frames[index])

def get_frame_time(video_frame, last_time, rate):
    try:
        return float(video_frame['pkt_pts_time']) * 1000
    except:
        try:
            return float(video_frame['pkt_dts_time']) * 1000
        except:
            return last_time + rate

@cached(count_cache,lock=count_lock)
def get_frame_count(video_file, start_time_tuple=(0, 1), end_time_tuple=None):
    frmcnt = 0
    startcomplete = False
    mask = {'starttime':0,'startframe':1,'endtime':0,'endframe':1,'frames':0,'rate':0}
    meta, frames = ffmpeg_api.get_meta_from_video(video_file, show_streams=True, with_frames=True, media_types=['video'])
    indices = ffmpeg_api.get_stream_indices_of_type(meta, 'video')
    if not indices:
        return None
    index = indices[0]
    rate = ffmpeg_api.get_video_frame_rate_from_meta(meta, frames)
    video_frames = frames[index]
    time_manager = tool_set.VidTimeManager(startTimeandFrame=start_time_tuple,stopTimeandFrame=end_time_tuple)
    aptime = 0
    lasttime = 0
    for pos in range(1,len(video_frames)):
        frmcnt += 1
        aptime = get_frame_time(video_frames[pos], aptime, rate)
        time_manager.updateToNow(aptime)
        if not time_manager.beforeStartTime and not startcomplete:
                startcomplete = True
                mask['starttime'] = lasttime
                mask['startframe'] = time_manager.frameCountWhenStarted
                mask['endtime'] = lasttime
                mask['endframe'] = time_manager.frameCountWhenStarted
                mask['rate'] = rate
        elif time_manager.isEnd():
                break
        lasttime = aptime
    if not time_manager.isEnd():
        mask['endtime'] = aptime
        mask['endframe'] = len(video_frames)
    else:
        mask['endtime'] = lasttime
        mask['endframe'] = frmcnt
    if not startcomplete and aptime > 0:
            mask['starttime'] = lasttime
            mask['startframe'] = frmcnt
            mask['rate'] = rate
    try:
            mask['frames'] = mask['endframe'] - mask['startframe'] + 1
    except:
            mask['frames'] = 0
    return mask

def maskSetFromConstraints(rate, start_time=(0,1), end_time=(0,1)):
    """
    Depending on variable or constraint frame rate, the time may not be accurate.
    For accuracy, use get_frame_count.
    :param rate: FPS
    :param start_time: millis + frames
    :param end_time: millis + frames
    :return:
    """
    import math
    # artificial increment: (time, frame) where time and frame > 0 means frame AFTER time.
    # where (time,frame) where time == 0 and frame > 0 means frame.
    start_adj = 1 if start_time[0] > 0 else 0
    end_adj = 1 if end_time[0] > 0 else 0
    startframe = int(math.floor(start_time[0]*rate/1000.0) + start_time[1]) + start_adj
    endframe =  int(math.floor(end_time[0]*rate/1000.0) + end_time[1]) + end_adj
    return  {'starttime':(startframe-1)*1000.0/rate,
             'startframe': int(startframe),
             'endtime': (endframe-1)*1000/rate,
             'endframe': int(endframe),
             'frames':endframe - startframe + 1}

class MetaDataLocator:

    def __init__(self):
        pass

    def get_meta(self,with_frames=False, show_streams=True,media_types=['video']):
        pass

    def get_filename(self):
        pass

    def get_frame_attribute(self, name, default=None, audio=False):
        pass

class FileMetaDataLocator(MetaDataLocator):

    def __init__(self, video_filename):
        MetaDataLocator.__init__(self)
        self.video_filename = video_filename

    def get_meta(self, with_frames=False, show_streams=True, media_types=['video']):
        return ffmpeg_api.get_meta_from_video(self.video_filename,
                                              with_frames=with_frames,
                                              show_streams=show_streams,
                                              media_types=media_types)


    def get_filename(self):
        return self.video_filename

    def get_frame_attribute(self, name, default=None, audio=False):
        return ffmpeg_api.get_frame_attribute(self.video_filename, name, default=default, audio=audio)

def get_frame_rate(locator, default=None, audio=False):
    """

    :param locator:
    :param default:
    :param audio:
    :return:
    @type locator: MetaDataLocator
    """
    rate = locator.get_frame_attribute( 'sample_rate' if audio else 'r_frame_rate', default=None, audio=audio)
    if not audio and rate is None:
        rate =locator.get_frame_attribute('avg_frame_rate', default=rate, audio=audio)
    if rate is None:
        duration = locator.get_frame_attribute('duration', default=None, audio=audio)
        frames = locator.get_frame_attribute('nb_frames', default=None, audio=audio)
        if frames is not None and duration is not None:
            rate = frames + '/' + duration
    if rate is None:
        return default
    parts = rate.split('/')
    if len(parts) == 1 and float(rate) > 0:
        return float(rate)
    if len(parts) == 2 and float(parts[1]) > 0:
        return float(parts[0]) / float(parts[1])
    return default


def get_duration(locator, default=None, audio=False):
    """
        duration in milliseconds for media
    :param locator:
    :param default:
    :param audio:
    :return:
    @type locator: MetaDataLocator
    """
    duration = locator.get_frame_attribute('duration', default=None, audio=audio)
    if duration is None or duration[0]== 'N':
        maskset = getMaskSetForEntireVideo(locator,media_types=['audio'] if audio else ['video'])
        if not maskset:
            return default
        frames= maskset[0]['frames']
        rate = maskset[0]['rate']
        return 1000.0 * int(frames) / float(rate)
    return float(duration) *1000.0

def getMaskSetForEntireVideo(locator, start_time='00:00:00.000', end_time=None, media_types=['video'],channel=0):
    """
       build a mask set for the entire video
       :param locator: a function that returns video_file, meta, frames
       :return: list of dict
       @type locator: MetaDataLocator
       """
    return getMaskSetForEntireVideoForTuples(locator,
                                      start_time_tuple=tool_set.getMilliSecondsAndFrameCount(start_time, defaultValue=(0,1)),
                                      end_time_tuple = tool_set.getMilliSecondsAndFrameCount(end_time) if end_time is not None and end_time != '0' else None,
                                      media_types=media_types,channel=channel)

def meta_key(*args, **kwargs):
    import copy
    newkargs  = copy.copy(kwargs)
    newargs = tuple([args[0].get_filename()])
    if 'media_types'  in kwargs:
        newkargs['media_types'] = '.'.join(sorted(kwargs['media_types']))
    else:
        newkargs['media_types'] = 'video'
    if 'start_time_tuple' not in kwargs:
        newkargs['start_time_tuple'] = (0,1)
    if 'channel' not in kwargs:
        newkargs['channel'] = 0
    return hashkey(*newargs, **newkargs)

@cached(meta_cache,lock=meta_lock,key=meta_key)
def getMaskSetForEntireVideoForTuples(locator, start_time_tuple=(0,1), end_time_tuple=None, media_types=['video'],
                                 channel=0):
    """
    build a mask set for the entire video
    :param locator: a function that returns video_file, meta, frames
    :return: list of dict
    @type locator: MetaDataLocator
    """
    video_file = locator.get_filename()
    meta, frames = locator.get_meta(show_streams=True, media_types=media_types)
    found_num = 0
    results = []
    for item in meta:
        if 'codec_type' in item and item['codec_type'] in media_types:
            if found_num != channel:
                found_num+=1
                continue
            mask = {}
            if item['codec_type'] == 'video':
                rate = ffmpeg_api.get_video_frame_rate_from_meta(meta, frames)
            else:
                rate = float(item['sample_rate'])
            mask['rate'] = rate
            mask['type'] = item['codec_type']
            if mask['type'] == 'video':
                if ffmpeg_api.is_vfr(meta[ffmpeg_api.get_stream_indices_of_type(meta, 'video')[0]]):
                    maskupdate = get_frame_count(video_file, start_time_tuple=start_time_tuple,
                                                 end_time_tuple=end_time_tuple)
                    mask.update(maskupdate)
                elif end_time_tuple in [None,(0,0)]:
                    try:
                       mask.update(maskSetFromConstraints(rate,start_time_tuple,(0, int(item['nb_frames']))))
                    except:
                        mask.update(get_frame_count(video_file, start_time_tuple=start_time_tuple))
                elif end_time_tuple is None:
                    # input provides frames, so assume constant frame rate as time is just a reference point
                    mask.update(get_frame_count(video_file, start_time_tuple=start_time_tuple))
                else:
                    mask.update(maskSetFromConstraints(rate, start_time_tuple, end_time_tuple))

                mask['mask'] = np.zeros((int(item['height']),int(item['width'])),dtype = np.uint8)
            else:
                mask['starttime'] = start_time_tuple[0] + (start_time_tuple[1]-1)/rate*1000.0
                mask['startframe'] = int(mask['starttime']*rate/1000.0) + 1
                if end_time_tuple is not None:
                    mask['endtime'] = end_time_tuple[0] + end_time_tuple[1] / rate * 1000.0
                else:
                    mask['endtime'] = float(item['duration']) * 1000 if ('duration' in item and item['duration'][0] != 'N') else 1000 * int(item['nb_frames']) / rate
                mask['endframe'] = int(mask['endtime']*rate/1000.0)
                mask['frames'] = mask['endframe'] - mask['startframe'] + 1
                mask['type']   = item['codec_type']
            if start_time_tuple == end_time_tuple:
                mask['endtime'] = mask['starttime']
                mask['endframe'] = mask['startframe']
                mask['frames'] = mask['endframe'] - mask['startframe'] + 1
            results.append(mask)
    return results


def get_ffmpeg_version():
    command = [ffmpeg_api.get_ffmpeg_tool(),'-version']
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

def __aggregate_numeric_meta(k, oldValue, newValue, summary):
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

def compare_meta_set(oneMeta, twoMeta, skipMeta=None, streamId='',  meta_diff=None, summary=dict()):
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
                if (meta_diff[meta_key][0] == 'change' and meta_diff[meta_key][2] != twoMeta[k]) or \
                        (meta_diff[meta_key][0] == 'add' and meta_diff[meta_key][1] != twoMeta[k]) or \
                        meta_diff[meta_key][0] == 'delete':
                    if not __aggregate_numeric_meta(k, v, twoMeta[k], summary):
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

def compare_meta_from_streams(oneMeta, twoMeta):
    meta_diff = {}
    for id,item in oneMeta.iteritems():
        compare_meta_set(item,
                    twoMeta[id] if id in twoMeta else {},
                    streamId=id,
                    meta_diff=meta_diff)
    for id,item in twoMeta.iteritems():
        if id not in oneMeta:
            compare_meta_set({},
                        item,
                        streamId=id,
                        meta_diff=meta_diff)
    return meta_diff

def __get_frame_order(packet, orderAttr, lasttime, pkt_duration_time='pkt_duration_time'):
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

def __update_summary(summary, streamId, apos, bpos, aptime):
    diff = {}
    for k, v in summary.iteritems():
        diff[str(streamId) + ':' + k + '.total'] = ('change',0,v[0])
        diff[str(streamId) + ':' + k + '.frames'] = ('change',0,v[1])
        diff[str(streamId) + ':' + k + '.average'] = ('change',0,v[0]/v[1])
    return ('change', apos, bpos, aptime, diff)

# video_tools.compareStream([{'i':0,'h':1},{'i':1,'h':1},{'i':2,'h':1},{'i':3,'h':1},{'i':5,'h':2},{'i':6,'k':3}],[{'i':0,'h':1},{'i':3,'h':1},{'i':4,'h':9},{'i':4,'h':2}], orderAttr='i')
# [('delete', 1.0, 2.0, 2), ('add', 4.0, 4.0, 2), ('delete', 5.0, 6.0, 2)]
def compare_video_stream_meta(a, b, orderAttr='pkt_pts_time', streamId=0, meta_diff=dict(), skipMeta=None, counters={}):
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
        aptime  =  __get_frame_order(apacket, orderAttr, aptime)
        bpacket = b[bpos]
        if orderAttr not in bpacket:
            bpos += 1
            continue
        bptime = __get_frame_order(bpacket, orderAttr, bptime)
        for k in counters.keys():
            counters[k][0] = counters[k][0] + getIntFromPacket(k,apacket)
            counters[k][1] = counters[k][1] + getIntFromPacket(k,bpacket)
        if aptime == bptime or \
                (aptime < bptime and (apos+1) < len(a) and __get_frame_order(a[apos+1], orderAttr, aptime) > bptime) or \
                (aptime > bptime and (bpos+1) < len(b) and __get_frame_order(b[bpos+1], orderAttr, bptime) < aptime):
            summary_start_time = aptime if summary_start is None else summary_start_time
            summary_start = apos if summary_start is None else summary_start
            summary_end = apos
            metaDiff = compare_meta_set(apacket, bpacket, skipMeta=skipMeta, streamId=streamId, meta_diff=meta_diff, summary=summary)
            if len(metaDiff) > 0:
                diff.append(('change', apos, bpos, aptime, metaDiff))
            apos += 1
            bpos += 1
        elif aptime < bptime:
            c = 0
            while aptime < bptime and apos < len(a):
                apos += 1
                c += 1
                if apos < len(a):
                    apacket = a[apos]
                    aptime = __get_frame_order(apacket, orderAttr, aptime)
        elif aptime > bptime:
            c = 0
            while aptime > bptime and bpos < len(b):
                c += 1
                bpos += 1
                if bpos < len(b):
                    bpacket = b[bpos]
                    bptime = __get_frame_order(bpacket, orderAttr, bptime)
        else:
            diff.append(__update_summary(summary, streamId, summary_start, summary_end, summary_start_time))
            summary_start_time = None
            summary_start = None
            summary_end = None
            summary.clear()

    diff.append(__update_summary(summary, streamId, summary_start, summary_end, summary_start_time))
    if apos < len(a):
        aptime = start = __get_frame_order(a[apos], orderAttr, aptime)
        c = len(a) - apos
        apacket = a[len(a) - 1]
        aptime = __get_frame_order(apacket, orderAttr, aptime)
        diff.append(('delete', start, aptime, c))
    elif bpos < len(b):
        bptime = start = __get_frame_order(b[bpos], orderAttr, bptime)
        c = len(b) - bpos
        bpacket = b[len(b) - 1]
        bptime = __get_frame_order(bpacket, orderAttr, bptime)
        diff.append(('add', start, bptime, c))

    return diff

def compare_frames(one_frames, two_frames, meta_diff=dict(), summarize=[], skip_meta={''}, counters={}):
    diff = {}
    for streamId, packets in one_frames.iteritems():
        if streamId in two_frames:
            diff[streamId] = ('change',
                              compare_video_stream_meta(packets, two_frames[streamId], streamId=streamId, meta_diff=meta_diff, skipMeta=skip_meta, counters=counters))
        else:
            diff[streamId] = ('delete', [])
    for streamId, packets in two_frames.iteritems():
        if streamId not in one_frames:
            diff[streamId] = ('add', [])
    return diff


def _align_streams_meta(meta_and_frames, excludeAudio=True):

    def make_stream_id(stream={}, mappings=[]):
        audio_layout_map = {'1': 'mono', '2': 'stereo'}
        stream_type = stream['codec_type'] if 'codec_type' in stream else 'other'
        id = stream_type
        if stream_type == 'audio' and 'channel_layout' in stream:
            layout = stream['channel_layout']
            if ((layout is None) or (stream['channel_layout'] == 'unknown')) and 'channels' in stream:
                channels = stream['channels']
                if channels in audio_layout_map:
                    id = audio_layout_map[channels]
            else:
                id = layout
        tally = len([mapping for mapping in mappings if id in mapping])
        if tally > 0:
            id = id + str(tally)
        return id

    aligned_meta = {}
    aligned_frames = {}
    meta = meta_and_frames[0]
    frames = meta_and_frames[1]
    do_frames = len(frames) > 0
    for pos in range(len(meta)):
        stream = meta[pos]
        if getValue(stream,'codec_type','na') == 'na':
            continue
        if not excludeAudio or (excludeAudio and getValue(stream,'codec_type','na') != 'audio'):
            id = make_stream_id(stream, list(aligned_meta.keys()))
            aligned_meta[id] = stream
            if do_frames:
                aligned_frames[id] = frames[pos]

    return aligned_meta, aligned_frames

def form_meta_data_diff(file_one, file_two, frames=True, media_types=['audio', 'video']):
    """
    Obtaining frame and video meta-data, compare the two videos, identify changes, frame additions and frame removals
    """
    one_meta, one_frames = _align_streams_meta(ffmpeg_api.get_meta_from_video(file_one, show_streams=True, with_frames=frames, media_types=media_types), excludeAudio= not 'audio' in media_types)
    two_meta, two_frames = _align_streams_meta(ffmpeg_api.get_meta_from_video(file_two, show_streams=True, with_frames=frames, media_types=media_types), excludeAudio= not 'audio' in media_types)
    meta_diff = compare_meta_from_streams(one_meta, two_meta)
    counters= {}
    counters['interlaced_frame'] = [0,0]
    counters['key_frame'] = [0, 0]
    if frames:
        frame_diff = compare_frames(one_frames, two_frames,
                                    meta_diff=meta_diff,
                                    skip_meta=['pkt_pos', 'pkt_size'], counters = counters)
        if counters['interlaced_frame'][0] - counters['interlaced_frame'][1] != 0:
            meta_diff ['interlaced_frames'] = ('change',counters['interlaced_frame'][0] , counters['interlaced_frame'][1])
        if counters['key_frame'][0] - counters['key_frame'][1] != 0:
            meta_diff ['key_frames'] = ('change',counters['key_frame'][0] , counters['key_frame'][1])
    else:
        frame_diff = {}
    return meta_diff, frame_diff

def remove_video_leave_audio(filename, outputname=None):
    import tempfile
    if outputname is None:
        suffix = filename[filename.find('.'):]
        newfilename = tempfile.mktemp(prefix='rmfa', suffix=suffix, dir='.')
    else:
        newfilename = outputname
    ffmpegcommand = ffmpeg_api.get_ffmpeg_tool()
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
                          ['-loglevel', 'error', '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', str(crf)],
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

def x264(filename, outputname=None, crf=0,remove_video=False, additional_args=[]):
    args = ['-loglevel','error','-c:v', 'libx264', '-preset', 'medium',  '-crf', str(crf)]
    if additional_args  is not None:
        args.extend (additional_args)
    return __vid_compress(filename,
                          ['-loglevel','error','-c:v', 'libx264', '-preset', 'medium',  '-crf', str(crf)],
                         'h264',
                          outputname=outputname,
                          remove_video=remove_video)

def vid_md5(filename):
    ffmpegcommand = ffmpeg_api.get_ffmpeg_tool()
    outFileName = os.path.splitext(filename)[0] + '_compressed.mp4'
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

def __vid_compress(filename, expressions, dest_codec, suffix='avi', outputname=None, remove_video=False):
    """

    :param filename:
    :param expressions: ffmpeg array of expressions
    :param dest_codec:
    :param suffix: the output suffix
    :param outputname: the output file name, with None use <inputfilename>_compressed.<suffix>
    :param remove_video: if intent is to leave only audio stream
    :return:
    """
    one_meta, one_frames = ffmpeg_api.get_meta_from_video(filename, show_streams=True, with_frames=False)
    input_filename = filename
    # has video?
    if one_meta is None:
        return input_filename
    indices = ffmpeg_api.get_stream_indices_of_type(one_meta, 'video')
    if indices is None or len(indices) == 0:
        return input_filename
    # file has video, determine the codec of the video
    index = indices[0]
    codec = getValue(one_meta[index],'codec_long_name',getValue(one_meta[index],'codec_name', 'raw'))
    # is compressed?
    execute_compress = 'raw' in codec and not input_filename.endswith('_compressed.' + suffix)

    outFileName = os.path.splitext(input_filename)[0] + '_compressed.' + suffix if outputname is None else outputname
    ffmpegcommand = ffmpeg_api.get_ffmpeg_tool()

    # has video and want to remove it
    if remove_video:
        # use compressed name if not executing compression
        input_filename = remove_video_leave_audio(input_filename, outputname=outFileName if not execute_compress else None)
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

def outputRaw(input_filename, output_filename):
    ffmpegcommand = ffmpeg_api.get_ffmpeg_tool
    command = [ffmpegcommand, '-y','-i', input_filename]
    command.extend(['-vcodec', 'rawvideo'])
    command.append(output_filename)
    p = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = p.communicate()
    try:
        if stderr is not None:
            for line in stderr.splitlines():
                logging.getLogger('maskgen').warning("FFMPEG error for {} is {}".format(input_filename, line))
        return output_filename if p.returncode == 0 else None
    except OSError as e:
        logging.getLogger('maskgen').error("FFMPEG invocation error for {} is {}".format(input_filename, str(e)))
    return None

def toAudio(fileOne,outputName=None, channel=None, start=None,end=None):
        """
        Consruct wav files
        """
        import shutil
        if start is None and end is None and channel is None and fileOne.lower().endswith('.wav'):
            if outputName is None:
                return fileOne,[]
            elif fileOne != outputName:
                shutil.copy(fileOne,outputName)
            return outputName,[]
        name = fileOne + '.wav' if outputName is None else outputName
        ffmpegcommand = ffmpeg_api.get_ffmpeg_tool()
        if os.path.exists(name):
            os.remove(name)
        ss = None
        to = None
        if start is not None:
            rate = get_frame_rate(FileMetaDataLocator(fileOne), audio=True)
            ss = tool_set.getDurationStringFromMilliseconds(tool_set.getMilliSecondsAndFrameCount(start,rate=rate)[0])
        if end is not None:
            rate = get_frame_rate(FileMetaDataLocator(fileOne), audio=True)
            to = tool_set.getDurationStringFromMilliseconds(tool_set.getMilliSecondsAndFrameCount(end,rate=rate)[0])
        if channel == 'left':
            fullCommand = [ffmpegcommand,'-y','-i', fileOne, '-map_channel', '0.1.0',  '-vn']
        elif channel == 'right':
            fullCommand = [ffmpegcommand,'-y','-i', fileOne, '-map_channel', '0.1.1',  '-vn']
        else:
            fullCommand =[ffmpegcommand, '-y','-i', fileOne,  '-vn']
        if ss is not None:
            fullCommand.extend(["-ss",ss])
        if to is not None:
            fullCommand.extend(["-to", to])
        fullCommand.append(name)
        errors = tool_set.runCommand(fullCommand)
        return name if len(errors) == 0 else None, errors

# video_tools.formMaskDiff('/Users/ericrobertson/Documents/movie/s1/videoSample5.mp4','/Users/ericrobertson/Documents/movie/s1/videoSample6.mp4')
def __form_mask_using_ffmpeg_diff(fileOne, fileTwo, prefix, op, time_manager, codec=['-vcodec', 'r210']):
    """
    Construct a diff video.  The FFMPEG provides degrees of difference by intensity variation in the green channel.
    The normal intensity is around 98.
    """
    ffmpegcommand = ffmpeg_api.get_ffmpeg_tool()
    outFileName = prefix + os.path.splitext(fileOne)[1]
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
        result = build_masks_from_green_mask(outFileName, time_manager)
    else:
        result = []
    try:
        os.remove(outFileName)
    except OSError:
        logging.getLogger('maskgen').warn('video diff process failed')

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
        self.grabbed_one = False
        self.grabbed_two = False
        self.frame_one = None
        self.frame_two = None
        self.file_one = None
        self.file_two = None

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
    orig_vid = getMaskSetForEntireVideo(FileMetaDataLocator(vidAnalysisComponents.file_one))
    cut_vid = getMaskSetForEntireVideo(FileMetaDataLocator(vidAnalysisComponents.file_two))
    diff_in_frames = orig_vid[0]['frames'] - cut_vid[0]['frames']
    vidAnalysisComponents.time_manager.setStopFrame (vidAnalysisComponents.time_manager.frameSinceBeginning + diff_in_frames - 1)
    if __changeCount(vidAnalysisComponents.mask) > 0 or not vidAnalysisComponents.vid_two.isOpened():
        cut = {}
        cut['starttime'] = vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one
        cut['startframe'] = vidAnalysisComponents.time_manager.frameSinceBeginning
        cut['rate'] = vidAnalysisComponents.fps_one
        cut['type'] = 'video'
        end_time = vidAnalysisComponents.time_manager.milliNow
        cut['mask'] = vidAnalysisComponents.mask
        if type(cut['mask']) == int:
            cut['mask'] = vidAnalysisComponents.frame_one_mask
        while (vidAnalysisComponents.vid_one.isOpened()):
            ret_one, frame_one = vidAnalysisComponents.vid_one.read()
            if not ret_one:
                vidAnalysisComponents.vid_one.release()
                break
            diff = 0 if vidAnalysisComponents.frame_two is None else np.abs(frame_one - vidAnalysisComponents.frame_two)
            if __changeCount(diff) == 0 and vidAnalysisComponents.vid_two.isOpened():
                break
            vidAnalysisComponents.time_manager.updateToNow(
                vidAnalysisComponents.vid_one.get(cv2api_delegate.prop_pos_msec))
            end_time = vidAnalysisComponents.time_manager.milliNow
            if vidAnalysisComponents.time_manager.isPastTime():
                break
        cut['endtime'] = end_time
        cut['endframe'] = vidAnalysisComponents.time_manager.getEndFrame()
        cut['frames'] = cut['endframe'] - cut['startframe'] + 1
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
    frame_count_diff = int(vidAnalysisComponents.vid_two.get(cv2api_delegate.prop_frame_count) - \
       vidAnalysisComponents.vid_one.get(cv2api_delegate.prop_frame_count)) - 1

    if __changeCount(vidAnalysisComponents.mask) > 0 or not vidAnalysisComponents.vid_one.isOpened():
        addition = {}
        addition['starttime'] = vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one
        addition['startframe'] = vidAnalysisComponents.time_manager.frameSinceBeginning
        addition['rate'] = vidAnalysisComponents.fps_one
        addition['type'] = 'video'
        end_time = vidAnalysisComponents.time_manager.milliNow
        addition['mask'] = vidAnalysisComponents.mask
        if type(addition['mask']) == int:
            addition['mask'] = vidAnalysisComponents.frame_two_mask
        while (vidAnalysisComponents.vid_two.isOpened() and frame_count_diff > 0):
            ret_two, frame_two = vidAnalysisComponents.vid_two.read()
            if not ret_two:
                vidAnalysisComponents.vid_two.release()
                break
            diff = 0 if vidAnalysisComponents.frame_one is None else np.abs(vidAnalysisComponents.frame_one - frame_two)
            if __changeCount(diff) == 0 and vidAnalysisComponents.vid_one.isOpened():
                break
            vidAnalysisComponents.time_manager.updateToNow(vidAnalysisComponents.vid_two.get(cv2api_delegate.prop_pos_msec))
            frame_count_diff-=1
            if frame_count_diff == 0:
                break
            end_time = vidAnalysisComponents.time_manager.milliNow
        addition['endtime'] = end_time
        addition['endframe'] = vidAnalysisComponents.time_manager.frameSinceBeginning
        addition['frames'] = addition['endframe'] - addition['startframe'] + 1
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
    if __changeCount(vidAnalysisComponents.mask) > 0:
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
        # advanced one frame...so back one frame.
        adjust = -1 if vidAnalysisComponents.time_manager.isPastTime() else 0
        change['endframe'] = change['startframe'] +  ranges[-1]['frames'] - 1
        change['frames']  = ranges[-1]['frames']
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
    entireVideoMaskSet = getMaskSetForEntireVideo(FileMetaDataLocator(fileOne))
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
            compare_result, analysis_result  = tool_set.cropCompare(frame_one, frame_two, arguments=analysis)
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
    change['type'] = 'video'
    change['rate'] = analysis_components.fps_one
    change['mask'] = compare_result
    change['endtime'] = entireVideoMaskSet[0]['endtime']
    change['endframe'] =  entireVideoMaskSet[0]['endframe']
    change['frames'] = entireVideoMaskSet[0]['frames']
    return [change],[]

def cutCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None,analysis={}):
    """

    :param fileOne:
    :param fileTwo:
    :param name_prefix:
    :param time_manager:
    :param arguments:
    :param analysis:
    :return:
    @retype: list of dict
    """
    maskSet, errors =  __runDiff(fileOne, fileTwo, name_prefix, time_manager, cutDetect, arguments=arguments)
    audioMaskSetOne = getMaskSetForEntireVideo(FileMetaDataLocator(fileOne), media_types=['audio'])
    audioMaskSetTwo = getMaskSetForEntireVideo(FileMetaDataLocator(fileTwo), media_types=['audio'])
    # audio was not dropped
    if len(maskSet) > 0 and len(audioMaskSetOne) > 0 and len(audioMaskSetTwo)>0:
        # audio was changed
        if audioMaskSetOne[0]['frames'] != audioMaskSetTwo[0]['frames']:
            startframe = 1+int(maskSet[0]['starttime']*audioMaskSetOne[0]['rate']/1000.0)
            realframediff = audioMaskSetOne[0]['frames'] - audioMaskSetTwo[0]['frames']
            maskSet.append({
                'starttime':maskSet[0]['starttime'],
                'startframe':startframe,
                'endtime':maskSet[0]['starttime'] + realframediff*1000.0/audioMaskSetOne[0]['rate'],
                'endframe':startframe + realframediff - 1,
                'frames':realframediff,
                'type':'audio',
                'rate':audioMaskSetOne[0]['rate']
            })
        else:
            errors.append('Audio must also be cut if the audio and video are in source and target files')
    return maskSet, errors

def pasteCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None,analysis={}):
    if arguments['add type'] == 'replace':
        return __runDiff(fileOne, fileTwo, name_prefix, time_manager, detectChange, arguments=arguments)
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager, addDetect, arguments=arguments)

def warpCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None,analysis={}):
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager, addDetect, arguments=arguments)

def detectCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None,analysis={}):
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager, detectChange, arguments=arguments)

def clampToEnd(filename, sets_tuple, media_type):
    """

    :param filename:
    :param sets:
    :return:
    @type filename: str
    @type sets: list
    """
    realmasks = getMaskSetForEntireVideo(FileMetaDataLocator(filename),
                             media_types=[media_type])
    if sets_tuple is None:
        return realmasks

    for mask in sets_tuple[0]:
        realmask = [rl for rl in realmasks if rl['type'] == mask['type']][0]
        if realmask['endframe'] < mask['endframe']:
            mask['endframe'] = realmask['endframe']
            mask['endtime'] = realmask['endtime']
            mask['frames'] = mask['endframe'] - mask['startframe'] + 1
    return sets_tuple


def fixVideoMasks(graph, source, edge, media_types=['video'], channel=0):
        video_masks = getValue(edge, 'videomasks', [])
        if len(video_masks) > 0:
            return
        video_masks = getMaskSetForEntireVideo(FileMetaDataLocator(graph.get_image_path(source)),
                                                           start_time=getValue(edge, 'arguments.Start Time',
                                                                               defaultValue='00:00:00.000'),
                                                           end_time=getValue(edge, 'arguments.End Time'),
                                                           media_types=media_types,
                                                           channel=channel)

        def justFixIt(graph, source, start_time, end_time, media_types):
            """
            Use the final node as a way to find the mask set
            :param graph:
            :param source:
            :return:
            @type graph: ImageGraph
            """

            def findBase(graph, node):
                """
                :param graph:
                :param node:
                :return:
                @type graph: ImageGraph
                @rtype : str
                """
                preds = graph.predecessors(node)
                if len(preds) == 0:
                    return node
                for pred in preds:
                    if getValue(graph.get_edge(pred, node), 'op', 'Donor') != 'Donor':
                        return findBase(graph, pred)

            def findFinal(graph, node):
                """
                :param graph:
                param node:
                :return:
                @type graph: ImageGraph
                @rtype : str
                """

                succs = graph.successors(node)
                if len(succs) == 0:
                    return node
                for succ in succs:
                    if getValue(graph.get_edge(node, succ), 'op', 'Donor') != 'Donor':
                        return findFinal(graph, succ)
            finalNode = findFinal(graph, source)
            if finalNode is not None:
                return getMaskSetForEntireVideo(
                    FileMetaDataLocator(os.path.join(graph.dir, getValue(graph.get_node(finalNode), 'file'))),
                    start_time=start_time, end_time=end_time, media_types=media_types)
            return []

        if video_masks is None or len(video_masks) == 0:
            video_masks = justFixIt(graph, source,
                                    getValue(edge, 'arguments.Start Time',
                                             defaultValue='00:00:00.000'),
                                    getValue(edge, 'arguments.End Time'),
                                    media_types)
        for item in video_masks:
            item.pop('mask')
        edge['masks count'] = len(video_masks)
        edge['videomasks'] = video_masks


def formMaskDiffForImage(vidFile,
                 image_wrapper,
                 name_prefix,
                 opName,
                 startSegment=None,
                 endSegment=None,
                 analysis=None,
                 alternateFunction=None,
                 arguments= {}):
    """
    compare the image to each frame of the select region of the video or zip file.

    :param vidFile: the zip or video file to compare to the image
    :param image_wrapper:  the imae
    :param name_prefix: the name of the mask file
    :param opName: the operation name
    :param startSegment:  the start of frames to compare
    :param endSegment:  then end of frames to compare
    :param analysis:
    :param alternateFunction: alternate comparison
    :param arguments:
    :return:videomask with the GrayMask container
    @type image_wrapper: ImageWrapper
    """
    time_manager = tool_set.VidTimeManager(startTimeandFrame=startSegment,stopTimeandFrame=endSegment)
    if alternateFunction is not None:
        return alternateFunction(vidFile, image_wrapper, name_prefix, time_manager, arguments=arguments, analysis=analysis)
    result,analysis_result,exifdiff = __runImageDiff(vidFile, image_wrapper, name_prefix,time_manager)
    if analysis is not None:
        analysis['startframe'] = time_manager.getStartFrame()
        analysis['stopframe'] = time_manager.getEndFrame()
        if exifdiff is not None:
            analysis['exifdiff'] = exifdiff
        analysis.update(analysis_result)
    return result

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
    if  diffPref in ['2','ffmpeg']:
        result = __form_mask_using_ffmpeg_diff(fileOne, fileTwo, name_prefix, opName, time_manager)
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

class AudioReader:

    def __init__(self,filename, channel, block=8192):
        import wave
        self.handle = wave.open(filename, 'rb')
        self.count = self.handle.getnframes()
        self.channels = self.handle.getnchannels()
        self.width = self.handle.getsampwidth()
        self.skipchannel = 1
        self.startchannel = self.width if channel == 'right' and self.skipchannel > 1 else 0
        self.channel = channel
        self.framesize = self.width * self.channels
        self.block = block
        self.buffer = self.handle.readframes(min(self.count,block))
        self.block_pos = 0
        self.pos = 0
        self.framerate = self.handle.getframerate()

    def setskipchannel(self, skipchannel):
        self.skipchannel = skipchannel
        self.startchannel =self.width if self.channel == 'right' and self.skipchannel > 1 else 0

    def read(self):
        if self.pos >= self.count:
            return False
        if self.pos == self.block_pos + self.block:
            self.buffer = self.handle.readframes(min(self.count-self.block_pos, self.block))
            self.block_pos += self.block
        self.pos += 1
        return True

    def getData(self):
        position = self.pos - self.block_pos  - 1
        return self.buffer[position * self.framesize + self.startchannel:position * self.framesize + self.framesize + self.startchannel:self.skipchannel]


    def getOrd(self):
        position = self.pos - self.block_pos - 1
        return sum([ord(c) for c in self.buffer[
                                        position * self.framesize + self.startchannel:position * self.framesize + self.framesize + self.startchannel:self.skipchannel]])

    def hasMore(self):
        return self.pos < self.count

    def close(self):
        self.handle.close()

class AudioCompare:

    def __init__(self, fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
        """
        :param fileOne:
        :param fileTwo:
        :param name_prefix:
        :param time_manager:
        :param arguments:
        :return:
        @type time_manager: VidTimeManager
        """
        self.channel = arguments['Copy Stream'] if 'Copy Stream' in arguments else 'all'
        fileOneAudio,errorsone = toAudio(fileOne)
        fileTwoAudio,errorstwo = toAudio(fileTwo)
        self.fileOneAudio = fileOneAudio
        self.fileTwoAudio = fileTwoAudio
        self.maxdiff = None
        if 'startframe' in arguments and 'endframe' in arguments:
           self.maxdiff = arguments['endframe'] - arguments['startframe']
        self.errorsone = errorsone
        self.errorstwo = errorstwo
        self.time_manager = time_manager
        self.analysis = analysis
        self.name_prefix = name_prefix


    def __compare(self):
        framerateone = self.fone.framerate
        frameratetwo = self.ftwo.framerate
        start = None
        sections = []
        section = None
        end = None
        while self.fone.hasMore() and self.ftwo.hasMore():
            self.fone.read()
            self.ftwo.read()
            allone = self.fone.getOrd()
            alltwo = self.ftwo.getOrd()
            diff = abs(allone - alltwo)
            self.time_manager.updateToNow(self.fone.pos / float(framerateone))
            if diff > 1:
                if section is not None and end is not None and self.fone.pos - end >= framerateone:
                    section['endframe'] = end
                    section['endtime'] = float(end) / float(framerateone) * 1000.0
                    section['frames'] = end - start + 1
                    sections.append(section)
                    section = None
                end = self.fone.pos
                if section is None:
                    start = self.fone.pos
                    section = {'startframe': start,
                               'starttime': float(start - 1) / float(framerateone) * 1000.0,
                               'endframe': end,
                               'endtime': float(end) / float(framerateone) * 1000.0,
                               'rate': framerateone,
                               'type': 'audio',
                               'frames': 1}
                    if self.time_manager.spansToEnd():
                        section['endframe'] = self.ftwo.count
                        section['rate'] = frameratetwo
                        section['endtime'] = section['endframe'] / float(frameratetwo) * 1000.0
                        section['frames'] = section['endframe'] - start + 1
                        return [section], []
                elif self.maxdiff is not None and end - start > self.maxdiff:
                    break
        if section is not None:
            section['endframe'] = end
            section['endtime'] = float(end) / float(framerateone) * 1000.0
            section['frames'] = end - start + 1
            sections.append(section)
        errors = [
            'Channel selection is all however only one channel is provided.'] if self.channel == 'all' and self.fone.channels > self.ftwo.channels else []
        if len(sections) == 0:  # or (startframe is not None and abs(sections[0]['startframe'] - startframe) > 2):
            startframe = self.time_manager.getExpectedStartFrameGiveRate(float(framerateone))
            stopframe = self.time_manager.getExpectedEndFrameGiveRate(float(framerateone))
            starttime = (startframe - 1) / float(framerateone) * 1000.0
            if stopframe is None:
                if self.maxdiff is not None:
                    stopframe = startframe + self.maxdiff
                else:
                    stopframe = self.fone.count
            errors = ['Warning: Could not find sample in source media']
            sections = [{'startframe': startframe,
                         'starttime': starttime,
                         'rate': framerateone,
                         'endframe': stopframe,
                         'type': 'audio',
                         'endtime': float(stopframe) / float(framerateone) * 1000.0,
                         'frames': stopframe - startframe + 1}
                        ]
        return sections, errors

    def __findMatch(self,matches=8):
        matchcount = 0
        dataone = [self.fone.getOrd()]
        while self.fone.hasMore() and matchcount < matches:
            self.fone.read()
            dataone.append(self.fone.getOrd())
            matchcount+=1
        totalmatches = matchcount
        while self.ftwo.hasMore() > 0 and matchcount>0:
            self.ftwo.read()
            datatwo=self.ftwo.getOrd()
            diff = abs(dataone[totalmatches-matchcount] - datatwo)
            if diff == 0:
                matchcount -= 1
            else:
                #while matchcount < matches:
                #    self.fone.read()
                matchcount = totalmatches


    def __insert(self):
        framerateone = self.fone.framerate
        section = None
        while self.fone.hasMore()  and self.ftwo.hasMore() > 0 and section is None:
            self.fone.read()
            self.ftwo.read()
            allone = self.fone.getOrd()
            alltwo = self.ftwo.getOrd()
            diff = abs(allone - alltwo)
            self.time_manager.updateToNow(self.ftwo.pos / float(framerateone))
            if diff > 1:
                start = self.ftwo.pos
                self.__findMatch()
                end = self.ftwo.pos
                section = {'startframe': start,
                           'starttime': float(start - 1) / float(framerateone),
                           'endframe': end,
                           'endtime': float(end) / float(framerateone),
                           'rate': framerateone,
                           'type': 'audio',
                           'frames': end-start+1}
                break
        if section is not None:
            return [section], []
        else:
            return [],['Warning: Could not find insertio point in target media']
        return sections, errors

    def __initiateCompare(self,compareFunc):
        import wave
        if len(self.errorsone) > 0 and len(self.errorstwo) == 0:
            try:
                ftwo = wave.open(self.fileTwoAudio, 'rb')
                counttwo = ftwo.getnframes()
                startframe = self.time_manager.getExpectedStartFrameGiveRate(ftwo.getframerate(), defaultValue=1)
                endframe = startframe + counttwo  - 1
                return [{'startframe': startframe,
                         'starttime': float(startframe) / float(ftwo.getframerate()) * 1000.0,
                         'rate': ftwo.getframerate(),
                         'endframe': endframe,
                         'endtime': float(endframe) / float(ftwo.getframerate()) * 1000.0,
                         'type': 'audio',
                         'frames': counttwo}], []
            finally:
                ftwo.close()
        if len(self.errorstwo) > 0:
            return list(), self.errorstwo
        self.fone = AudioReader(self.fileOneAudio, self.channel, 8192)
        try:
            self.ftwo = AudioReader(self.fileTwoAudio,self.channel, 8192)
            self.fone.setskipchannel ( self.fone.width if self.fone.channels > self.ftwo.channels else 1 )
            self.ftwo.setskipchannel ( self.ftwo.width if self.fone.channels < self.ftwo.channels else 1 )
            if self.fone.framerate != self.ftwo.framerate or self.fone.width != self.ftwo.width:
                self.time_manager.updateToNow(float(self.count) / float(self.fone.framerate))
                startframe = self.time_manager.getExpectedStartFrameGiveRate(self.ftwo.framerate, defaultValue=1)
                endframe = self.time_manager.getExpectedEndFrameGiveRate(self.ftwo.framerate, defaultValue=self.ftwo.count)
                return [{'startframe': startframe,
                         'starttime': float(startframe) / float(self.ftwo.framerate) * 1000.0,
                         'rate': self.ftwo.framerate,
                         'endframe': endframe,
                         'endtime': float(endframe) / float(self.ftwo.framerate) * 1000.0,
                         'type': 'audio',
                         'frames': self.ftwo.count}], []
            return compareFunc()
        finally:
            self.ftwo.close()
            self.fone.close()

    def audioCompare(self):
        return clampToEnd(self.fileTwoAudio, self.__initiateCompare(self.__compare), 'audio')

    def audioInsert(self):
        return clampToEnd(self.fileTwoAudio, self.__initiateCompare(self.__insert), 'audio')


def audioInsert(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    ac = AudioCompare(fileOne,fileTwo,name_prefix,time_manager,arguments=arguments,analysis=analysis)
    return ac.audioInsert()

def audioCompare(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    ac = AudioCompare(fileOne,fileTwo,name_prefix,time_manager,arguments=arguments,analysis=analysis)
    return ac.audioCompare()

def audioAddCompare(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    if 'add type' in arguments and arguments['add type'] == 'insert':
        return audioInsert(fileOne,fileTwo,name_prefix,time_manager,arguments=arguments,analysis=analysis)
    else:
        return audioCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=arguments, analysis=analysis)

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
    fileOneAudio,errorsone = toAudio(fileOne)
    fileTwoAudio,errorstwo = toAudio(fileTwo)
    channel = arguments['Copy Stream'] if 'Copy Stream' in arguments else 'all'
    fone = AudioReader(fileOneAudio, channel)
    try:
        ftwo = AudioReader(fileTwoAudio,channel='all')
        fone.setskipchannel(fone.width if fone.channels > ftwo.channels else 1)
        ftwo.setskipchannel(ftwo.width if fone.channels < ftwo.channels else 1)
        try:
            if fone.framerate != ftwo.framerate or fone.width != ftwo.width:
                time_manager.updateToNow(float(ftwo.count) / float(ftwo.framerate))
                return [{'startframe': 1,
                         'starttime': 0,
                         'rate':ftwo.framerate,
                         'endframe': ftwo.count,
                         'type':'audio',
                         'endtime': float(ftwo.count) / float(ftwo.framerate)*1000.0,
                         'frames': ftwo.count}], []
            while fone.hasMore():
                fone.read()
                time_manager.updateToNow(float(fone.pos) / float(fone.framerate)*1000.0)
                if not time_manager.isBeforeTime():
                    break
            if ftwo.hasMore():
                ftwo.read()
            while fone.hasMore():
                diff = abs(fone.getOrd() - ftwo.getOrd())
                if diff == 0:
                    break
                fone.read()
            startframe = fone.pos - 1
            while fone.hasMore() and ftwo.hasMore():
                fone.read()
                ftwo.read()
                diff = abs(fone.getOrd() - ftwo.getOrd())
                if diff != 0:
                    break
            if ftwo.hasMore():
                startframe = time_manager.getExpectedStartFrameGiveRate(float(fone.framerate), defaultValue =1)
                errors = ['Warning: Could not find sample in source media']
            else:
                errors = []
            starttime = (startframe-1) / float(fone.framerate)*1000.0
            return [{'startframe': startframe,
                     'starttime': starttime,
                     'rate': fone.framerate,
                     'endframe': startframe + ftwo.count- 1,
                     'type': 'audio',
                     'endtime': float(startframe + ftwo.count) / float(fone.framerate)*1000.0,
                     'frames': ftwo.count}], errors
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
                     'endframe': startframe + ftwo.getnframes() -1 ,
                     'type': 'audio',
                     'endtime': float(startframe + ftwo.getnframes()) / float(framerateone),
                     'frames': ftwo.getnframes()}], []
        finally:
            ftwo.close()
    finally:
        fone.close()


def buildCaptureTool(vidFile):
    if os.path.splitext(vidFile)[1].lower() == '.zip':
        return tool_set.ZipCapture(vidFile)
    else:
        return cv2api_delegate.videoCapture(vidFile)

def __runImageDiff(vidFile, img_wrapper, name_prefix, time_manager, arguments={}):
    """
      compare frame to frame of each video
     :param vidFile:
     :param img_wrapper:
     :param name_prefix:
     :param time_manager:
     :return:
     @type time_manager: VidTimeManager
     @type img_wrapper: ImageWrapper
     """
    vid_cap = buildCaptureTool(vidFile)
    fps = vid_cap.get(cv2api_delegate.prop_fps)
    writer = tool_set.GrayBlockWriter(name_prefix, fps)
    mask_set = {'rate': fps,'type':'video','startframe':1,'starttime':0}
    exifdiff = None
    try:
        last_time = 0
        while vid_cap.isOpened():
            ret_one = vid_cap.grab()
            elapsed_time = vid_cap.get(cv2api_delegate.prop_pos_msec)
            if not ret_one:
                break
            time_manager.updateToNow(elapsed_time)
            if time_manager.isBeforeTime():
                mask_set['startframe'] = time_manager.frameSinceBeginning
                mask_set['starttime'] = elapsed_time - fps
                continue
            if time_manager.isPastTime():
                break
            ret, frame =vid_cap.retrieve()
            if exifdiff is None:
                exifforvid = vid_cap.get_exif()
                exifdiff = exif.comparexif_dict(exifforvid, img_wrapper.get_exif())
            args = {'tolerance':0.1}
            args.update(arguments)
            mask,analysis,error = tool_set.createMask(ImageWrapper(frame),img_wrapper,
                                invert=True,
                                arguments=args,
                                alternativeFunction=tool_set.convertCompare)
            if 'mask' not in mask_set:
                mask_set['mask'] = mask.to_array()
            writer.write(mask.to_array(),last_time,time_manager.frameSinceBeginning)
            last_time = elapsed_time
        mask_set['endframe'] = time_manager.frameSinceBeginning
        mask_set['frames'] = mask_set['endframe'] - mask_set['startframe'] + 1
        mask_set['endtime'] = elapsed_time - fps
        mask_set['videosegment'] = writer.get_file_name()
        return [mask_set], analysis, exifdiff
    finally:
        vid_cap.release()
        writer.close()
    return [], analysis, exif.comparexif_dict(exif,img_wrapper.get_exif())

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
    analysis_components.file_one = fileOne
    analysis_components.file_two = fileTwo
    analysis_components.vid_one = buildCaptureTool(fileOne)
    analysis_components.vid_two = buildCaptureTool(fileTwo)
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
            if time_manager.isPastTime():
                break
            ret_one, frame_one =analysis_components.retrieveOne()
            ret_two, frame_two = analysis_components.retrieveTwo()
            if frame_one.shape != frame_two.shape:
                return getMaskSetForEntireVideo(FileMetaDataLocator(fileOne)),[]
            analysis_components.mask = tool_set.__diffMask(ImageWrapper(frame_one).to_16BitGray().to_array(),
                                       ImageWrapper(frame_two).to_16BitGray().to_array(),
                                       True,
                                       {'tolerance':0.1})[0]
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

def __get_video_frame(video, frame_time):
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
                        frame,vid_frame_time = __get_video_frame(destination_video, frame_time)
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
            if keepTime and drop_ef is not None and drop_ef - mask_sf < 0:
                new_mask_set.append(mask_set)
                continue
            if 'videosegment' not in mask_set:
                new_mask_set.extend(dropFramesWithoutMask([bound],[mask_set],keepTime=keepTime))
                continue
            mask_file_name = mask_set['videosegment']
            reader = tool_set.GrayBlockReader(mask_set['videosegment'])
            writer = reader.create_writer()
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
                            change['endtime'] = last_time
                            change['endframe'] = frame_count - 1
                            change['frames'] = change['endframe']-change['startframe']+1
                            change['rate'] = rate
                            change['error'] = getValue(mask_set, 'error', 0)
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
                    change['startframe'] = mask_set['endframe'] - elapsed_count - written_count + 1
                    change['endtime'] = last_time - elapsed_time
                    change['endframe'] = mask_set['endframe'] - elapsed_count
                    change['frames'] = written_count
                    change['rate'] = rate
                    change['error'] = getValue(mask_set, 'error', 0)
                    change['videosegment'] = writer.filename
                    new_mask_set.append(change)
                    writer.release()
            finally:
                reader.close()
                writer.close()
        return new_mask_set
    new_mask_set = video_masks
    if bounds is None:
        return new_mask_set
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
        drop_st = bound['starttime'] if 'starttime' in bound else 0
        drop_et = bound['endtime'] if 'endtime' in bound and bound['endtime'] > 0 else None
        new_mask_set = []
        for mask_set in video_masks:
            if 'type' in mask_set and mask_set['type'] != expectedType:
                new_mask_set.append(mask_set)
                continue
            mask_sf = mask_set['startframe']
            mask_st = mask_set['starttime']
            mask_ef = mask_set['endframe'] if 'endframe' in mask_set or mask_set['endframe'] == 0 else None
            rate = mask_set['rate']
            # before remove region
            if drop_sf - mask_ef > 0:
                new_mask_set.append(mask_set)
                continue
                # at the end and time is not change
            if keepTime and drop_ef is not None and (drop_ef - mask_sf) < 0:
                new_mask_set.append(mask_set)
                continue
            if (drop_ef is None or (mask_ef is not None and drop_ef - mask_ef >= 0)) and \
                    (drop_sf - mask_sf <= 0):
                # started after drop and subsummed by drop
                continue
            #occurs after drop region
            start_diff_frame = drop_sf - mask_sf
            start_diff_time = drop_st - mask_st
            if start_diff_frame > 0:
                change = dict()
                change['starttime'] = mask_set['starttime']
                change['type'] = mask_set['type']
                change['startframe'] = mask_set['startframe']
                change['endtime'] = mask_set['starttime'] + start_diff_time - 1000.0/rate
                change['endframe'] = mask_set['startframe'] + start_diff_frame - 1
                change['frames'] = change['endframe'] - change['startframe'] + 1
                change['rate'] = rate
                change['error'] = getValue(mask_set, 'error', 0)
                new_mask_set.append(change)
            if drop_ef is not None:
                 end_diff_frame = drop_ef  - mask_ef
                 if end_diff_frame < 0:
                    end_adjust_frame = drop_ef - drop_sf + 1
                    end_adjust_time = drop_et - drop_st + 1000.0/rate
                    change = dict()
                    if keepTime:
                        change['starttime'] = bound['endtime'] + 1000.0/rate
                        change['startframe'] = drop_ef + 1
                        change['type'] = mask_set['type']
                        change['error'] = getValue(mask_set, 'error', 0)
                        change['endframe'] = mask_set['endframe']
                        change['endtime'] = mask_set['endtime']
                        change['frames'] = change['endframe'] - change['startframe']  + 1
                        change['rate'] = rate
                    else:
                        if drop_ef - mask_sf < 0:
                            change['startframe'] = mask_set['startframe'] -  end_adjust_frame
                            change['starttime'] =  mask_set['starttime'] -  end_adjust_time
                        else:
                            change['starttime']  = bound['starttime']
                            change['startframe'] = bound['startframe']
                        change['endtime'] = mask_set['endtime'] -  end_adjust_time
                        change['endframe'] = mask_set['endframe'] -  end_adjust_frame
                        change['frames'] = change['endframe'] - change['startframe'] + 1
                        change['type'] = mask_set['type']
                        change['error'] = getValue(mask_set, 'error', 0)
                    change['rate'] = rate
                    new_mask_set.append(change)
        return new_mask_set
    new_mask_set = video_masks
    if bounds is None:
        return new_mask_set
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
    return insertFrames(bounds, video_masks, expectedType=expectedType)


def reverseNonVideoMasks(composite_mask_set, edge_video_mask):
    new_mask_set = []
    if composite_mask_set['startframe'] < edge_video_mask['startframe']:
        if composite_mask_set['endframe'] >= edge_video_mask['endframe']:
            return [composite_mask_set]
        change = dict()
        diff_time = composite_mask_set['endtime'] - composite_mask_set['starttime']
        change['starttime'] = composite_mask_set['starttime']
        change['startframe'] = composite_mask_set['startframe']
        change['type'] = composite_mask_set['type']
        change['rate'] = composite_mask_set['rate']
        change['error'] = getValue(composite_mask_set, 'error', 0)
        change['endtime'] = edge_video_mask['starttime'] - 1000.0/composite_mask_set['rate']
        change['endframe'] = edge_video_mask['startframe'] -1
        change['frames'] = change['endframe'] - change['startframe'] + 1
        frames_left_over = composite_mask_set['frames'] - change['frames']
        time_left_over = diff_time - (change['endtime'] - change['starttime'])
        new_mask_set.append(change)
        change = dict()
        change['startframe'] = edge_video_mask['endframe'] - frames_left_over + 1
        change['starttime'] = edge_video_mask['endtime'] - time_left_over + 1000.0/composite_mask_set['rate']
        change['type'] = composite_mask_set['type']
        change['rate'] = composite_mask_set['rate']
        change['error'] = getValue(composite_mask_set, 'error', 0)
        change['endtime'] = edge_video_mask['endtime']
        change['endframe'] = edge_video_mask['endframe']
        change['frames'] = change['endframe'] - change['startframe'] + 1
        new_mask_set.append(change)
    else:
        if composite_mask_set['endframe'] <= edge_video_mask['endframe']:
            return [composite_mask_set]
        change = dict()
        diff_frame = edge_video_mask['endframe'] - composite_mask_set['startframe']
        diff_time = edge_video_mask['endtime'] - composite_mask_set['starttime']
        change['startframe'] = edge_video_mask['startframe']
        change['starttime'] = edge_video_mask['starttime']
        change['type'] = composite_mask_set['type']
        change['rate'] = composite_mask_set['rate']
        change['error'] = getValue(composite_mask_set, 'error', 0)
        change['endtime'] = change['starttime'] + diff_time
        change['endframe'] = change['startframe'] + diff_frame
        change['frames'] = change['endframe'] - change['startframe'] + 1
        new_mask_set.append(change)
        change = dict()
        change['startframe'] = edge_video_mask['endframe'] + 1
        change['starttime'] = edge_video_mask['endtime'] + 1000.0/composite_mask_set['rate']
        change['type'] = composite_mask_set['type']
        change['rate'] = composite_mask_set['rate']
        change['error'] = getValue(composite_mask_set, 'error', 0)
        change['endtime'] = composite_mask_set['endtime']
        change['endframe'] = composite_mask_set['endframe']
        change['frames'] = change['endframe'] - change['startframe'] +1
        new_mask_set.append(change)
    return new_mask_set

def reverseMasks(edge_video_masks, composite_video_masks):
    """
    Reverse Masks
    :param func: the transforming function
    :param expectedType:
    :param video_masks:
    :return: new set of video masks
    """
    import time
    new_mask_set = []
    mask_types = set([composite_video_mask['type'] for composite_video_mask in composite_video_masks])
    for mask_type in mask_types:
        for mask_set in composite_video_masks:
            if mask_set['type'] != mask_type:
                continue
            for edge_video_mask in edge_video_masks:
                if edge_video_mask['type'] != mask_set['type']:
                    continue
                if edge_video_mask['endframe'] < mask_set['startframe'] or \
                   edge_video_mask['startframe'] > mask_set['endframe']:
                    new_mask_set.append(mask_set)
                    continue
                if 'videosegment' not in mask_set:
                    new_mask_set.extend(reverseNonVideoMasks(mask_set,edge_video_mask))
                    continue
                mask_file_name = mask_set['videosegment']
                reader = tool_set.GrayBlockReader(mask_set['videosegment'])
                try:
                    frame_count = mask_set['startframe']
                    if  frame_count < edge_video_mask['startframe']:
                        writer = reader.create_writer()
                        change = dict()
                        change['starttime'] = mask_set['starttime']
                        change['startframe'] = mask_set['startframe']
                        change['type'] = mask_set['type']
                        change['rate'] = mask_set['rate']
                        change['error'] = getValue(mask_set, 'error', 0)
                        frame_count = mask_set['startframe']
                        for i in range(edge_video_mask['startframe']-frame_count):
                            frame_time = reader.current_frame_time()
                            frame_count = reader.current_frame()
                            mask = reader.read()
                            if mask is None:
                                break
                            writer.write(mask, frame_time, frame_count)
                        change['videosegment'] = writer.filename
                        writer.close()
                        change['endtime'] = frame_time
                        change['endframe'] = frame_count
                        change['frames'] = change['endframe'] - change['startframe'] + 1
                        new_mask_set.append(change)

                    if frame_count <= edge_video_mask['endframe']:
                        writer = reader.create_writer()
                        change = dict()
                        masks = []
                        start_time = frame_time
                        for i in range(edge_video_mask['endframe']-frame_count):
                            frame_time = reader.current_frame_time()
                            mask = reader.read()
                            if mask is None:
                                break
                            masks.insert(0,mask)
                        if edge_video_mask['endframe']>=mask_set['endframe']:
                            change['startframe'] =  edge_video_mask['endframe']-len(masks)  + 1
                            change['starttime'] = edge_video_mask['endtime'] - (frame_time - start_time) + 1000.0/mask_set['rate']
                            change['endframe'] = edge_video_mask['endframe']
                            change['endtime'] = edge_video_mask['endtime']
                        else:
                            change['startframe'] =  edge_video_mask['startframe']
                            change['starttime'] =  edge_video_mask['starttime']
                            change['endframe'] =change['startframe'] + len(masks)
                            change['endtime'] = change['starttime'] + (frame_time - start_time)
                        change['frames'] = change['endframe'] - change['startframe'] + 1
                        change['type'] = mask_set['type']
                        change['rate'] = mask_set['rate']
                        change['error'] = getValue(mask_set, 'error', 0)
                        frame_time = change['starttime']
                        frame_count = change['startframe']
                        diff_time = (change['endtime'] - change['starttime'])/(change['frames'] - 1)
                        for mask in masks:
                            writer.write(mask, frame_time, frame_count)
                            frame_count += 1
                            frame_time += diff_time
                        change['videosegment'] = writer.filename
                        new_mask_set.append(change)
                        writer.close()

                    if edge_video_mask['endframe'] < mask_set['endframe']:
                        writer = reader.create_writer()
                        change = dict()
                        change['startframe'] = edge_video_mask['endframe'] + 1
                        change['starttime'] = edge_video_mask['endtime'] + 1
                        change['endframe'] = mask_set['endframe']
                        change['endtime'] = mask_set['endtime']
                        change['frames'] = change['endframe'] - change['startframe'] + 1
                        change['type'] = mask_set['type']
                        change['rate'] = mask_set['rate']
                        change['error'] = getValue(mask_set, 'error', 0)
                        while True:
                            frame_time = reader.current_frame_time()
                            frame_count = reader.current_frame()
                            mask = reader.read()
                            if mask is None:
                                break
                            writer.write(mask, frame_time, frame_count)
                        change['videosegment'] = writer.filename
                        new_mask_set.append(change)
                        writer.close()
                except Exception as e:
                    logging.getLogger('maskgen').error(e)
                finally:
                    reader.close()
    return new_mask_set

def _maskTransform( video_masks, func, expectedType='video', funcReturnsList=False):
    """
    Tranform masks given the mask function.
    If the transforming funciton supports lists:
        signature: edge_video_masks,  next mask,frame_time,frame_count
        When mask is empty, the function is called one more time with None
        The function returns a list of tuples [ (mask, frame time, frame count) ]
    If the transforming function does not support lists:
        signature: edge_video_masks, next mask,frame_time,frame_count
        The function is not called with a None mask
    :param video_masks: ithe set of video masks to walk through and transform
    :param func: the transforming function
    :param expectedType:
    :param video_masks:
    :return: new set of video masks
    """
    new_mask_set = []
    for mask_set in video_masks:
        if 'type' in mask_set and mask_set['type'] != expectedType or \
            'videosegment' not in mask_set:
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
        change['error'] = getValue(mask_set, 'error', 0)
        change['videosegment'] = mask_set['videosegment']
        mask_file_name = mask_set['videosegment']
        reader = tool_set.GrayBlockReader(mask_set['videosegment'])
        try:
            writer = reader.create_writer()
            while True:
                frame_time = reader.current_frame_time()
                frame_count = reader.current_frame()
                mask = reader.read()
                if funcReturnsList:
                    for new_mask_tuple in func(mask, frame_time, frame_count):
                        writer.write(new_mask_tuple[0], new_mask_tuple[1], new_mask_tuple[2])
                if mask is None:
                    break
                if not funcReturnsList:
                    new_mask = func(mask)
                    writer.write(new_mask, frame_time, frame_count)
            change['videosegment'] = writer.filename
            new_mask_set.append(change)

        except Exception as e:
            logging.getLogger('maskgen').error('Failed to transform {} using {}'.format(mask_set['videosegment'],
                                                                                        str(func)))
            logging.getLogger('maskgen').error(e)
        finally:
            reader.close()
            if writer is not None:
                writer.close()
    return new_mask_set

def inverse_intersection_for_mask(mask, video_masks):
    """
    Return the altered video masks that represent the mask as it applies to the unchanged pixels
    :param mask:
    :param video_masks:
    :return:
    """
    import copy
    new_mask_set = []
    for mask_set in video_masks:
        change = copy.copy(mask_set)
        if 'videosegment' in change:
            mask_file_name = mask_set['videosegment']
            new_mask_file_name = os.path.splitext(mask_file_name)[0] + str(time.clock())
            reader = tool_set.GrayBlockReader(mask_file_name)
            writer = tool_set.GrayBlockWriter(new_mask_file_name,reader.fps)
            while True:
                frame_time = reader.current_frame_time()
                frame_count = reader.current_frame()
                frame = reader.read()
                if frame is not None:
                    # ony those pixels that are unchanged from the original
                    # TODO Handle orientation change
                    if frame.shape != mask.shape:
                        frame = cv2.resize(frame, (mask.shape[1],mask.shape[0]))
                    frame = mask * ((255-frame)/255)
                    writer.write(frame, frame_time, frame_count)
                else:
                    break
            change['videosegment'] = writer.get_file_name()
        new_mask_set.append(change)
    return new_mask_set

def extractMask(video_masks, frame_time):
    """
    Extract one mask from a group of videomasks given the frame_time

    :param video_masks:
    :param frame_time: time or frame number
    :return:
    """
    extract_time_tuple = tool_set.getMilliSecondsAndFrameCount(frame_time, defaultValue=(0, 1))
    timeManager = tool_set.VidTimeManager(extract_time_tuple)
    if video_masks is None:
        return None
    frames = 0
    mask = None
    for mask_set in video_masks:
        timeManager.updateToNow(mask_set['endtime'],mask_set['endframe']-frames)
        frames = mask_set['endframe']
        if timeManager.isPastStartTime():
            if 'videosegment' in mask_set:
                timeManager = tool_set.VidTimeManager(extract_time_tuple)
                timeManager.updateToNow(mask_set['starttime'], mask_set['startframe'])
                reader = tool_set.GrayBlockReader(mask_set['videosegment'])
                while True:
                    frame_time = reader.current_frame_time()
                    mask = reader.read()
                    if mask is None:
                        break
                    timeManager.updateToNow(frame_time,1)
                    if timeManager.isPastStartTime():
                        break
                reader.close()
                break
    return mask

def insertMask(video_masks,box, size):
    """
    Insert mask inside larger mask
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

def xxxreverseMasks(edge_video_masks,composite_video_masks):
    """
    Commented out since the other implementation works.  This is an attempt to get reverseMasks to work in _maskTransform
    reverse order composite masks within a section of edge_video_masks
    :param directory
    :param video_masks
    :param size of the new mask
    :return: new set of video masks
    """
    from functools import partial
    # need to keep a list masks so they can be sent back in reverse order
    memory = {
        'compiled_mask_list' : list(),
        'start_time':0,
        'start_count':0}

    def compileResult(memory, frame_time, frame_count):
        if memory['start_count'] > 0:
            diff_count = frame_count - memory['start_count']
            diff_time = (frame_time - memory['start_time']) / diff_count
            current_time = memory['start_time']
            current_count = memory['start_count']
            memory['start_count'] = 0
        else:
            diff_time = 0
            current_time=frame_time
            current_count = frame_count
        mask_list = memory['compiled_mask_list']
        memory['compiled_mask_list'] = list()
        for item in mask_list:
            current_count+=1
            current_time+=diff_time
            yield (item,current_time-diff_time,current_count-1)

    def compileReverseMask(edge_video_masks, memory, mask,frame_time,frame_count):
        if mask is None:
            return compileResult(memory,frame_time,frame_count)
        for video_mask in edge_video_masks:
            if video_mask['startframe'] <= frame_count and video_mask['endframe'] > frame_count:
                # in the reverse region, save the mask (insert in front)
                if memory['start_count']== 0:
                    memory['start_time'] = frame_time
                    memory['start_count'] = frame_count
                memory['compiled_mask_list'].insert(0,mask)
                return []
            else:
                #outside the region, append the mask in order to the list
                memory['compiled_mask_list'].append(mask)
                return compileResult(memory,frame_time,frame_count)
    return _maskTransform(composite_video_masks, partial(compileReverseMask,edge_video_masks,memory),funcReturnsList=True)

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

def removeIntersectionOfMaskSets(setOne, setTwo):
    """
    from set two from set one
    :param setOne:
    :param setTwo:
    :return:
    @type setOne: list of dict
    @type setOne: list of dict
    """
    result = setTwo
    processedTwo = []
    for itemOne in setOne:
        nextrun = result
        result = []
        for posTwo in range(len(nextrun)):
            itemTwo = nextrun[posTwo]
            if itemTwo['endframe'] < itemOne['startframe'] or \
                itemTwo['startframe'] > itemOne['endframe']:
                continue
            processedTwo.append(posTwo)
            diff_sf = itemTwo['startframe'] - itemOne['startframe']
            if diff_sf < 0:
                result.append( {'starttime': itemTwo['starttime'],
                        'endtime': itemOne['starttime'] - 1000.0/itemOne['rate'],
                        'startframe': itemTwo['startframe'],
                        'endframe': itemOne['startframe'] - 1,
                        'rate': itemOne['rate'],
                        'frames': itemOne['startframe'] - itemTwo['startframe'],
                         'type': itemTwo['type']
                })
            diff_ef = itemTwo['endframe'] - itemOne['endframe']
            if diff_ef > 0:
                if itemTwo['startframe'] > itemOne['startframe']:
                    continue
                result.append({'starttime': itemOne['starttime'] + 1000.0 / itemOne['rate'],
                               'endtime': itemTwo['endtime'],
                               'startframe': itemOne['startframe'] + 1,
                               'endframe': itemTwo['endframe'],
                               'rate': itemOne['rate'],
                               'frames': itemTwo['endframe'] - itemOne['startframe'],
                               'type': itemTwo['type']
                               })
        for posTwo in range(len(nextrun)):
            if posTwo not in processedTwo:
                result.append(nextrun[posTwo])
        processedTwo = []
    result.extend(setOne)
    return sorted(result, key=lambda meta: meta['startframe'])



def insertFrames(bounds,
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
        add_sf = getValue(bound,'startframe',0)
        add_ef = getValue(bound,'endframe',0)
        add_st = getValue(bound,'starttime',0)
        add_et = getValue(bound,'endtime',0)
        new_mask_set = []

        def transfer(reader, writer, adjust_time, adjust_count, howmany):
            while howmany > 0:
                frame_count = reader.current_frame()
                frame_time = reader.current_frame_time()
                mask = reader.read()
                if mask is None:
                    break
                howmany-=1
                writer.write(mask, frame_time + adjust_time, frame_count + adjust_count)

        for mask_set in video_masks:
            reader = None
            if 'type' in mask_set and mask_set['type'] != expectedType:
                new_mask_set.append(mask_set)
                continue
            mask_sf = getValue(mask_set,'startframe',0)
            mask_ef = getValue(mask_set,'endframe',0)
            rate = mask_set['rate']
            #before addition
            if add_sf - mask_ef > 0:
                new_mask_set.append(mask_set)
                continue
            start_diff_count= add_sf - mask_sf
            start_diff_time = add_st - getValue(mask_set,'starttime',0)
            end_adjust_count = add_ef - add_sf + 1
            end_adjust_time = add_et - add_st + 1000.0/rate
            if start_diff_count > 0:
                change = dict()
                change['starttime'] = mask_set['starttime']
                change['startframe'] = mask_set['startframe']
                change['endtime'] = mask_set['starttime'] + start_diff_time - 1000.0/mask_set['rate']
                change['endframe'] = mask_set['startframe'] + start_diff_count - 1
                change['frames'] = change['endframe'] - change['startframe'] + 1
                change['type'] = mask_set['type']
                change['error'] = getValue(mask_set,'error',0)
                change['rate'] = rate
                if 'videosegment' in mask_set:
                    reader = tool_set.GrayBlockReader(mask_set['videosegment'])
                    writer = reader.create_writer()
                    transfer(reader, writer, 0, 0, change['frames'])
                    change['videosegment'] = writer.filename
                    writer.close()
                new_mask_set.append(change)
                if end_adjust_count >= 0:
                    # split in the middle
                    change = dict()
                    change['starttime'] =  add_et + 1000.0/rate
                    change['startframe'] = add_ef + 1
                    change['endtime'] = mask_set['endtime'] + end_adjust_time
                    change['endframe'] = mask_set['endframe'] + end_adjust_count
                    change['frames'] = change['endframe'] - change['startframe'] + 1
                    change['rate'] = rate
                    change['error'] = getValue(mask_set, 'error', 0)
                    change['type'] = mask_set['type']
                    if 'videosegment' in mask_set:
                        writer = reader.create_writer()
                        transfer(reader, writer, end_adjust_time, end_adjust_count, change['frames'])
                        change['videosegment'] = writer.filename
                        writer.close()
                    new_mask_set.append(change)
            elif end_adjust_count >= 0:
                change = dict()
                change['starttime'] = mask_set['starttime'] +  end_adjust_time
                change['startframe'] = mask_set['startframe'] + end_adjust_count
                change['endtime'] = mask_set['endtime'] + end_adjust_time
                change['endframe'] = mask_set['endframe'] + end_adjust_count
                change['error'] = getValue(mask_set, 'error', 0)
                change['frames'] = change['endframe'] - change['startframe'] + 1
                change['rate'] = rate
                change['type'] = mask_set['type']
                if 'videosegment' in mask_set:
                    reader = tool_set.GrayBlockReader(mask_set['videosegment'])
                    writer = reader.create_writer()
                    transfer(reader, writer, end_adjust_time, end_adjust_count, change['frames'])
                    change['videosegment'] = writer.filename
                    writer.close()
                new_mask_set.append(change)
            if reader is not None:
                reader.close()
        return new_mask_set

    new_mask_set = video_masks
    if bounds is None:
        return new_mask_set
    for bound in bounds:
        new_mask_set = insertFramesWithoutMaskForBound(bound, new_mask_set, expectedType=expectedType)
    return new_mask_set

def pullFrameNumber(video_file, frame_number):
    """

    :param video_file:
    :param frame_number:
    :return:
    """

    video_capture = cv2api_delegate.videoCapture(video_file)
    while (video_capture.isOpened() and frame_number > 0):
        ret = video_capture.grab()
        if not ret:
            break
        frame_number-=1
    ret, frame = video_capture.retrieve()
    elapsed_time = video_capture.get(cv2api_delegate.prop_pos_msec)
    video_capture.release()
    ImageWrapper(frame).save(os.path.splitext(video_file)[0] + '.png')
    return time.strftime("%H:%M:%S", time.gmtime(elapsed_time / 1000)) + '.%03d' % (elapsed_time % 1000)


class DummyMemory:
    def __init__(self,default=None):
        self.default = default
        pass
    def __call__(self, *args, **kwargs):
        return self.default
    def forget(self, *args, **kwargs):
        return self.default
    def __getitem__(self, item):
        return self.default
    def __setitem__(self, key, item):
        pass
