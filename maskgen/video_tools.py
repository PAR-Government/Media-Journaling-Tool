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

import cv2
import numpy as np
from cachetools import LRUCache
from cachetools import cached
from cachetools.keys import hashkey

import ffmpeg_api
import tool_set
from cv2api import cv2api_delegate
from image_wrap import ImageWrapper
from maskgen import exif
from maskgen_loader import  MaskGenLoader
from support import getValue

global meta_cache
global count_cache
meta_lock = RLock()
count_lock = RLock()
meta_cache = LRUCache(maxsize=124)
count_cache = LRUCache(maxsize=124)

def create_segment(starttime=None,
                   startframe=None,
                   endtime=None,
                   endframe=None,
                   type=None,
                   frames=None,
                   videosegment=None,
                   mask=None,
                   rate=None,
                   error=0):
    """
    TODO: Eventually replace the dictionary with a real class/structure
    :param starttime:
    :param startframe:
    :param endtime:
    :param endframe:
    :param type:
    :param frames:
    :param videosegment:
    :param mask:
    :param rate:
    :return:
    """
    def to_dict(**kwargs):
        return {k:v for k,v in kwargs.iteritems() if v is not None}
    segment = to_dict(starttime=starttime,
                   startframe=startframe,
                   endtime=endtime,
                   endframe=endframe,
                   type=type,
                   frames=frames,
                   videosegment=videosegment,
                   mask=mask,
                   rate=rate,
                   error=error)
    if frames is None:
        update_segment(segment,
                       frames=get_end_frame_from_segment(segment,1) - get_start_frame_from_segment(segment,1) + 1)
    return segment

def drop_file_from_segment(segment):
    if 'videosegment' in segment:
        segment.pop('videosegment')

def drop_mask_from_segment(segment):
    if 'mask' in segment:
        segment.pop('mask')

def update_segment(segment,
                   starttime=None,
                   startframe=None,
                   endtime=None,
                   endframe=None,
                   type=None,
                   frames=None,
                   videosegment=None,
                   mask=None,
                   rate=None,
                   error=None):
    def to_dict(**kwargs):
        return {k:v for k,v in kwargs.iteritems() if v is not None}
    segment.update(to_dict(starttime=starttime,
                   startframe=startframe,
                   endtime=endtime,
                   endframe=endframe,
                   type=type,
                   frames=frames,
                   videosegment=videosegment,
                   mask=mask,
                   rate=rate,
                   error=error))
    if frames is None:
        update_segment(segment,
                       frames=get_end_frame_from_segment(segment,1) - get_start_frame_from_segment(segment,1) + 1)
    return segment

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

def get_error_from_segment(segment):
    return getValue(segment, 'error',0)

def get_type_of_segment(segment,default_value='video'):
    return getValue(segment,'type',defaultValue=default_value)

def get_file_from_segment(segment,default_value=None):
    return getValue(segment,'videosegment',defaultValue=default_value)

def get_frames_from_segment(segment, default_value=None):
    if 'frames' not in segment:
        if 'rate' in segment or ('startframe' in segment and 'endframe' in segment):
            return get_end_frame_from_segment(segment) - get_start_frame_from_segment(segment)
        if default_value is not None:
            return default_value
        return 1
    return segment['frames']

def get_mask_from_segment(segment, default_value=None):
    if 'mask' not in segment:
        return default_value
    return segment['mask']

def get_start_frame_from_segment(segment, default_value=None):
    from math import floor
    if 'startframe' not in segment:
        if default_value is not None:
            return default_value
        rate = get_rate_from_segment(segment)
        segment['startframe'] = int(floor(getValue(segment,'starttime',0)*rate/1000.0)) + 1
    return segment['startframe']

def get_end_frame_from_segment(segment, default_value=None):
    from math import floor
    if 'endframe' not in segment:
        if default_value is not None:
            return default_value
        rate = get_rate_from_segment(segment)
        segment['endframe'] = int(floor(getValue(segment,'endtime',0)*rate/1000.0))
    return segment['endframe']

def get_start_time_from_segment(segment, default_value=None):
    if 'starttime' not in segment:
        if default_value is not None:
            return default_value
        segment['starttime'] = (getValue(segment,'startframe',1)-1)*1000.0/segment['rate']
    return segment['starttime']

def get_end_time_from_segment(segment, default_value=None):
    if 'endtime' not in segment:
        if default_value is not None:
            return default_value
        segment['endtime'] = getValue(segment,'endframe',1)*1000.0/segment['rate']
    return segment['endtime']

def get_rate_from_segment(segment, default_value=None):
    if 'rate' not in segment:
        if 'endtime' not in segment and 'starttime' not in segment:
            return default_value
        segment['rate'] = (segment['endtime'] - segment['starttime'])/float(segment['frames'])
    return segment['rate']

def transfer_masks(video_masks, new_mask_set,
                   frame_time_function=lambda x,y: x,
                   frame_count_function=lambda x,y: x):
    pos = 0
    reader_manager = tool_set.GrayBlockReaderManager()
    writer_manager = tool_set.GrayBlockWriterManager()
    try:
        for mask_set in video_masks:
            change = new_mask_set[pos]
            pos += 1
            if get_file_from_segment(mask_set):
                reader = reader_manager.create_reader(get_file_from_segment(mask_set),
                                                 start_frame=get_start_frame_from_segment(mask_set),
                                                 start_time=get_start_time_from_segment(mask_set),
                                                 end_frame=get_end_frame_from_segment(mask_set))
                writer = writer_manager.create_writer(reader)
                try:
                    frame_time = get_start_time_from_segment(change)
                    frame_count = get_start_frame_from_segment(change)
                    while True:
                        mask = reader.read()
                        if mask is not None:
                            writer.write(mask, frame_time, frame_count)
                        else:
                            break
                        frame_count = frame_count_function(reader.current_frame(), frame_count)
                        frame_time = frame_time_function(reader.current_frame_time(), frame_time)
                    update_segment(change, videosegment=writer.filename)
                except Exception as e:
                    logging.getLogger('maskgen').error(
                        'Failed to transform time for {}'.format(get_file_from_segment(mask_set)))
                    logging.getLogger('maskgen').error(e)
    finally:
        reader_manager.close()
        writer_manager.close()

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
                capOut.write(result, last_time, amountRead)
            else:
                if startTime is not None:
                    ranges.append(create_segment(starttime=startTime,
                                                 endtime=last_time,
                                                 startframe=startFrame,
                                                 endframe=time_manager.frameSinceBeginning-1,
                                                 frames=count,
                                                 rate=capIn.get(cv2api_delegate.prop_fps),
                                                 mask=sample,
                                                 type='video',
                                                 videosegment=os.path.split(capOut.filename)[1]))
                    count = 0
                startTime = None
            last_time = elapsed_time
        if startTime is not None:
            ranges.append(create_segment(starttime= startTime,
                                         endtime=last_time,
                                         startframe=startFrame,
                                         endframe=time_manager.frameSinceBeginning-1,
                                         rate=capIn.get(cv2api_delegate.prop_fps),
                                         mask=sample,
                                         type='video',
                                         videosegment=os.path.split(capOut.filename)[1]))
    finally:
        capIn.release()
        capOut.close()
    if amountRead == 0:
        raise ValueError('Mask Computation Failed to a read videos.  FFMPEG and OPENCV may not be installed correctly or the videos maybe empty.')
    return ranges


def invertVideoMasks(videomasks, start, end):
    """
    Invert black/white for the video masks.
    Save to a new files for the given start and end node names.
    """
    if videomasks is None:
        return
    result = []

    def __invert_mask_from_segment(capIn, capOut):
        """
         Invert a single video file (gray scale)
         """
        while True:
            frame_time = capIn.current_frame_time()
            frame_count = capIn.current_frame()
            frame = capIn.read()
            if frame is not None:
                frame = abs(frame - np.ones(frame.shape) * 255)
                capOut.write(frame, frame_time, frame_count)
            else:
                break
        return capOut.filename

    writer_manager = tool_set.GrayBlockWriterManager()
    reader_manager = tool_set.GrayBlockReaderManager()
    try:
        for segment in videomasks:
            segment = segment.copy()
            capIn = reader_manager.create_reader(get_file_from_segment(segment),
                                             start_frame=get_start_frame_from_segment(segment),
                                             start_time=get_start_time_from_segment(segment),
                                             end_frame=get_end_frame_from_segment(segment))
            capOut = writer_manager.create_writer(capIn)
            update_segment(segment,videosegment=__invert_mask_from_segment(capIn, capOut))
            result.append(segment)
    finally:
        writer_manager.close()
        reader_manager.close()
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
    if width == 0 or height == 0:
        im = tool_set.openImage(video_file)
        width, height = im.size
    return width,height

def estimate_duration(meta=[], frame_count=0):
    """
    A fast estimate using the frame count and the average framerate.
    :param meta:
    :param frame_count:
    :return:
    """
    framerate = getValue(meta, 'avg_frame_rate', '30/1').split('/')
    framerate = float(framerate[0]) / float(framerate[1])
    duration = (float(frame_count) / framerate) if frame_count > 0 else 0
    return duration

def get_frame_time(video_frame, last_time, rate):
    try:
        return float(video_frame['pkt_pts_time']) * 1000
    except:
        try:
            return float(video_frame['pkt_dts_time']) * 1000
        except:
            if rate is not None:
                return last_time + rate
            return None

@cached(count_cache,lock=count_lock)
def get_frame_count(video_file, start_time_tuple=(0, 1), end_time_tuple=None):
    """
    Provie a meta set with frame count givn the constraints.

    :param video_file:
    :param start_time_tuple:
    :param end_time_tuple:
    :return:
    """
    frmcnt = 0
    startcomplete = False
    segment = create_segment(starttime=0,startframe=1,endtime=0,endframe=1,frames=0,rate=0)
    # first assume FFR.
    meta, frames = ffmpeg_api.get_meta_from_video(video_file, show_streams=True, with_frames=False, media_types=['video'])
    indices = ffmpeg_api.get_stream_indices_of_type(meta, 'video')
    if not indices:
        return None
    index= indices[0]
    open_ended = end_time_tuple in [None, (0, 0), (0,1)]
    open_started = start_time_tuple in [(0, 1),None]
    missing_frame_count = getValue(meta[index],'nb_frames','n').lower()[0] in ['0','n']
    end_time = None
    def to_time(x):
        return '%d:%d' % (x/60,x%60)
    frame_count = int(meta[indices[0]]['nb_frames']) if not missing_frame_count else None
    is_vfr = ffmpeg_api.is_vfr(meta[index],frames)
    # Not FFR, then need to pull more data from frames
    if missing_frame_count or is_vfr:
        # do not incur this cost unless vfr or open started and missing frame count
        # ffr missing frame count is an odd case, but lets trap it here
        if open_ended and (open_started or not is_vfr) and missing_frame_count:
            meta, frames = ffmpeg_api.get_meta_from_video(video_file, show_streams=True, with_frames=False,
                                                          media_types=['video'],
                                                          count_frames=True)
            index = ffmpeg_api.get_stream_indices_of_type(meta, 'video')[0]

            # would be odd that this did not work
            if frame_count is None and getValue(meta[index],'nb_read_frames','n').lower()[0] not in ['0','n']:
                frame_count = int(meta[index]['nb_read_frames'])

        if not (open_ended and open_started) or frame_count is None:
            # need to pull the frame info to find the start and end frames.
            meta, frames = ffmpeg_api.get_meta_from_video(video_file, show_streams=True, with_frames=True,
                                                          media_types=['video'], frame_meta=['pkt_pts_time','pkt_dts_time','pkt_duration_time'])
            index = ffmpeg_api.get_stream_indices_of_type(meta, 'video')[0]
            frame_count = len(frames[index])
        else:
            # get the last frames, as we have the count and it is not open ended or open started
            duration = getValue(meta[index],'duration', 'N/A')
            if duration[0].lower() == 'n':
                duration = estimate_duration(meta[index], frame_count)
            meta, frames = ffmpeg_api.get_meta_from_video(video_file,
                                                       show_streams=True,
                                                       with_frames=True,
                                                       media_types=['video'],
                                                       frame_meta=['pkt_pts_time', 'pkt_dts_time'],
                                                       frame_start=to_time(float(duration)-2))
            index = ffmpeg_api.get_stream_indices_of_type(meta, 'video')[0]
            end_time = get_frame_time(frames[index][-1], None, None)
            try:
                if duration[0].lower() != 'n':
                    end_time = min(end_time, float(duration)*1000.0)
            except:
                pass

    if end_time_tuple in [None, (0, 0)]:
        end_time_tuple = (0, frame_count)

    if start_time_tuple in [None, (0, 0)]:
        start_time_tuple = (0, 1)

    rate = ffmpeg_api.get_video_frame_rate_from_meta(meta, frames)
    if not is_vfr:
        update_segment(segment,**maskSetFromConstraints(rate, start_time_tuple, end_time_tuple))
        return segment

    if open_ended and open_started and end_time is not None:
        update_segment(segment,
                       rate=rate,
                       startframe=1,
                       starttime=0,
                       endframe=frame_count,
                       endtime=end_time
                       )
        return segment

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
                update_segment(segment,
                               starttime=lasttime,
                               startframe=time_manager.frameCountWhenStarted,
                               endtime=lasttime,
                               endframe=time_manager.frameCountWhenStarted,
                               rate=rate)
        elif time_manager.isEnd():
                break
        lasttime = aptime
    if not time_manager.isEnd():
        update_segment(segment, endtime=aptime, endframe=len(video_frames))
    else:
        update_segment(segment, endtime=lasttime, endframe=frmcnt)

    if not startcomplete and aptime > 0:
        update_segment(segment, starttime=lasttime, startframe=frmcnt,rate=rate)

    return segment

def get_frame_count_only(video_file):
    return get_frames_from_segment(get_frame_count(video_file))

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
    return create_segment(starttime=(startframe - 1) * 1000.0 / rate,
                          startframe=int(startframe),
                          endtime=(endframe-1)*1000/rate,
                          endframe=int(endframe),
                          rate=rate)

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
        frames= get_frames_from_segment(maskset[0])
        rate = get_rate_from_segment(maskset[0])
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
            if item['codec_type'] == 'video':
                rate = ffmpeg_api.get_video_frame_rate_from_meta(meta, frames)
            else:
                rate = float(item['sample_rate'])
            segment = create_segment(rate=rate,type=item['codec_type'])
            if item['codec_type'] == 'video':
                maskupdate = get_frame_count(video_file,
                                                 start_time_tuple=start_time_tuple,
                                                 end_time_tuple=end_time_tuple)
                update_segment(segment,**maskupdate)
                update_segment(segment,mask= np.zeros((int(item['height']),int(item['width'])),dtype = np.uint8))
            else:
                starttime = start_time_tuple[0] + (start_time_tuple[1]-1)/rate*1000.0
                startframe = int(starttime*rate/1000.0) + 1
                if end_time_tuple is not None:
                    endtime = end_time_tuple[0] + end_time_tuple[1] / rate * 1000.0
                else:
                    endtime = float(item['duration']) * 1000 if ('duration' in item and item['duration'][0] != 'N') else 1000 * int(item['nb_frames']) / rate
                endframe = int(endtime*rate/1000.0)
                update_segment(segment,
                               type=item['codec_type'],
                               startframe=startframe,
                               starttime=starttime,
                               endframe=endframe,
                               rate=rate,
                               endtime=endtime)
            if start_time_tuple == end_time_tuple:
                update_segment(segment,
                               endtime=get_start_time_from_segment(segment),
                               endframe=get_start_frame_from_segment(segment))
            results.append(segment)
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

def compare_meta_set(oneMeta, twoMeta, skipMeta=None,  meta_diff=None, summary=dict()):
    diff = {}
    for k, v in oneMeta.iteritems():
        if skipMeta is not None and k in skipMeta:
            continue
        meta_key = k
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
            meta_key =  k
            if meta_diff is not None and meta_key not in meta_diff:
                diff[k] = ('add', v)
                meta_diff[meta_key] = ('add', v)
            elif meta_diff is None:
                diff[k] = ('add', v)
    return diff

def compare_meta_from_streams(oneMeta, twoMeta):
    meta_diff = {}
    for id,item in oneMeta.iteritems():
        meta_diff[id] = {}
        compare_meta_set(item,
                    twoMeta[id] if id in twoMeta else {},
                    meta_diff=meta_diff[id])
    for id,item in twoMeta.iteritems():
        if id not in oneMeta:
            compare_meta_set({},
                        item,
                        meta_diff=getValue(meta_diff,id,{}))
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

def __update_summary(summary,  apos, bpos, aptime):
    diff = {}
    for k, v in summary.iteritems():
        diff[ k + '.total'] = ('change',0,v[0])
        diff[k + '.frames'] = ('change',0,v[1])
        diff[k + '.average'] = ('change',0,v[0]/v[1])
    return ('change', apos, bpos, aptime, diff)

# video_tools.compareStream([{'i':0,'h':1},{'i':1,'h':1},{'i':2,'h':1},{'i':3,'h':1},{'i':5,'h':2},{'i':6,'k':3}],[{'i':0,'h':1},{'i':3,'h':1},{'i':4,'h':9},{'i':4,'h':2}], orderAttr='i')
# [('delete', 1.0, 2.0, 2), ('add', 4.0, 4.0, 2), ('delete', 5.0, 6.0, 2)]
def compare_video_stream_meta(a, b, orderAttr='pkt_pts_time', meta_diff=dict(), skipMeta=None, counters={}):
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
            metaDiff = compare_meta_set(apacket, bpacket, skipMeta=skipMeta, meta_diff=meta_diff, summary=summary)
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
            diff.append(__update_summary(summary, summary_start, summary_end, summary_start_time))
            summary_start_time = None
            summary_start = None
            summary_end = None
            summary.clear()

    diff.append(__update_summary(summary, summary_start, summary_end, summary_start_time))
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
                              compare_video_stream_meta(packets, two_frames[streamId], meta_diff=getValue(meta_diff,streamId,{}), skipMeta=skip_meta, counters=counters))
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
                aligned_frames[id] = frames[pos] if pos < len(frames) else []

    return aligned_meta, aligned_frames

def form_meta_data_diff(file_one, file_two, frames=False, media_types=['audio', 'video']):
    """
    Obtaining frame and video meta-data, compare the two videos, identify changes, frame additions and frame removals
    """
    one_meta, one_frames = _align_streams_meta(ffmpeg_api.get_meta_from_video(file_one, show_streams=True, with_frames=frames, media_types=media_types, frame_limit=30), excludeAudio= not 'audio' in media_types)
    two_meta, two_frames = _align_streams_meta(ffmpeg_api.get_meta_from_video(file_two, show_streams=True, with_frames=frames, media_types=media_types, frame_limit=30), excludeAudio= not 'audio' in media_types)
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
        return meta_diff, frame_diff
    else:
        return meta_diff


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
    args = ['-loglevel','error', '-c:v', 'libx264', '-preset', 'medium',  '-crf', str(crf)]
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

def is_raw_or_lossy_compressed(media_file):
    """
    TODO: Need to figure this one out more efficiently and accurately
    :param media_file:
    :return:
    """
    import exif
    from ffmpeg_api import  get_meta_from_video, is_vfr

    data = exif.getexif(media_file)
    exif_file_type = getValue(data, 'File Type')
    media_file_type = tool_set.fileType(media_file)

    if exif_file_type in ['WAV','PNG'] or media_file_type in ['audio','zip']:
        return True

    # all other images are compressed
    if tool_set.fileType(media_file) == 'image':
        return False

    one_meta, one_frames = get_meta_from_video(media_file, show_streams=True, with_frames=False)
    if one_meta is None:
        return None
    indices = ffmpeg_api.get_stream_indices_of_type(one_meta, 'video')
    if not indices:
        "no video, so must be ok"
        return True

    # file has video, determine the codec of the video
    index = indices[0]
    codec = getValue(one_meta[index], 'codec_long_name', getValue(one_meta[index], 'codec_name', 'raw')).lower()
    profile = getValue(one_meta[index], 'profile', 'na').lower()
    return  'raw' in codec or (('h264' in codec or 'h.264' in codec) and \
                               profile == 'high 4:4:4 predictive' and \
                               not is_vfr(one_meta[index]))

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
    if not indices:
        return input_filename
    # file has video, determine the codec of the video
    index = indices[0]
    codec = getValue(one_meta[index],'codec_long_name',getValue(one_meta[index],'codec_name', 'raw'))
    # is compressed?
    execute_compress = 'raw' in codec and '_compressed' not in input_filename

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
    ffmpegcommand = ffmpeg_api.get_ffmpeg_tool()
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

    def write(self, mask, frame_time, frame):
        m = 255-mask
        self.writer.write(m, frame_time, frame)
        return m

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

def default_compare(x,y,args):
    return np.abs(x - y)

def cutDetect(vidAnalysisComponents, ranges=list(),arguments={},compare_function=default_compare):
    """
    Find a region of cut frames given the current starting point
    :param vidAnalysisComponents: VidAnalysisComponents
    :param ranges: collection of meta-data describing then range of cut frames
    :return:
    """
    orig_vid = getMaskSetForEntireVideo(FileMetaDataLocator(vidAnalysisComponents.file_one))
    cut_vid = getMaskSetForEntireVideo(FileMetaDataLocator(vidAnalysisComponents.file_two))
    diff_in_frames = get_frames_from_segment(orig_vid[0]) - get_frames_from_segment(cut_vid[0])
    vidAnalysisComponents.time_manager.setStopFrame (vidAnalysisComponents.time_manager.frameSinceBeginning + diff_in_frames - 1)
    if __changeCount(vidAnalysisComponents.mask) > 0 or not vidAnalysisComponents.vid_two.isOpened():
        end_time = vidAnalysisComponents.time_manager.milliNow
        cut = create_segment(starttime=vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one,
                             startframe=vidAnalysisComponents.time_manager.frameSinceBeginning,
                             rate=vidAnalysisComponents.fps_one,
                             type='video',
                             mask=  vidAnalysisComponents.frame_one_mask if type(vidAnalysisComponents.mask) == int else vidAnalysisComponents.mask)
        while (vidAnalysisComponents.vid_one.isOpened()):
            ret_one, frame_one = vidAnalysisComponents.vid_one.read()
            if not ret_one:
                vidAnalysisComponents.vid_one.release()
                break
            diff = 0 if vidAnalysisComponents.frame_two is None else compare_function(frame_one, vidAnalysisComponents.frame_two,arguments)
            if __changeCount(diff) == 0 and vidAnalysisComponents.vid_two.isOpened():
                break
            vidAnalysisComponents.time_manager.updateToNow(
                vidAnalysisComponents.vid_one.get(cv2api_delegate.prop_pos_msec))
            end_time = vidAnalysisComponents.time_manager.milliNow
            if vidAnalysisComponents.time_manager.isPastTime():
                break
        update_segment(cut,
                      endtime=end_time,
                      endframe=vidAnalysisComponents.time_manager.getEndFrame())
        ranges.append(cut)
        return False
    return True

def addDetect(vidAnalysisComponents, ranges=list(),arguments={},compare_function=default_compare):
    """
    Find a region of added frames given the current starting point
    :param vidAnalysisComponents:
    :param ranges: collection of meta-data describing then range of add frames
    :return:
    """
    frame_count_diff = int(vidAnalysisComponents.vid_two.get(cv2api_delegate.prop_frame_count) - \
       vidAnalysisComponents.vid_one.get(cv2api_delegate.prop_frame_count))

    if __changeCount(vidAnalysisComponents.mask) > 0 or not vidAnalysisComponents.vid_one.isOpened():
        end_time = vidAnalysisComponents.time_manager.milliNow
        addition = create_segment(starttime=vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one,
                             startframe=vidAnalysisComponents.time_manager.frameSinceBeginning,
                             rate=vidAnalysisComponents.fps_one,
                             type='video',
                             mask=vidAnalysisComponents.frame_two_mask if type(
                                 vidAnalysisComponents.mask) == int else vidAnalysisComponents.mask)
        while (vidAnalysisComponents.vid_two.isOpened() and frame_count_diff > 0):
            ret_two, frame_two = vidAnalysisComponents.vid_two.read()
            if not ret_two:
                vidAnalysisComponents.vid_two.release()
                break
            diff = 0 if vidAnalysisComponents.frame_one is None else compare_function(vidAnalysisComponents.frame_one, frame_two,arguments)
            if __changeCount(diff) == 0 and vidAnalysisComponents.vid_one.isOpened():
                break
            frame_count_diff-=1
            if frame_count_diff == 0:
                break
            vidAnalysisComponents.time_manager.updateToNow(vidAnalysisComponents.vid_two.get(cv2api_delegate.prop_pos_msec))

            end_time = vidAnalysisComponents.time_manager.milliNow
        update_segment(addition,
                       endtime=end_time,
                       endframe=vidAnalysisComponents.time_manager.frameSinceBeginning)
        ranges.append(addition)
        return False
    return True

def __changeCount(mask):
    return np.sum(mask)

def detectChange(vidAnalysisComponents, ranges=list(), arguments={},compare_function=default_compare):
    """
       Find a region of changed frames given the current starting point
       :param vidAnalysisComponents:
       :param ranges: collection of meta-data describing then range of changed frames
       :return:
       """
    if np.sum(vidAnalysisComponents.mask) > 0:
        # Using end elapsed time.  Pick one.  time_one favors donor, time_two favors composite.
        # If the frame rate change occurs, then they will not match...!!!!
        mask = vidAnalysisComponents.write(vidAnalysisComponents.mask,
                                           vidAnalysisComponents.elapsed_time_two - vidAnalysisComponents.rate_two,
                                           vidAnalysisComponents.time_manager.frameSinceBeginning)
        if len(ranges) == 0 or get_end_time_from_segment(ranges[-1],-1)>=0:
            change = create_segment(mask=mask,
                                    starttime=vidAnalysisComponents.elapsed_time_two - vidAnalysisComponents.rate_two,
                                    rate= vidAnalysisComponents.fps_two,
                                    startframe=vidAnalysisComponents.time_manager.frameSinceBeginning,
                                    endframe=vidAnalysisComponents.time_manager.frameSinceBeginning,
                                    endtime=-1,
                                    frames =1,
                                    type ='video')
            ranges.append(change)
        else:
            update_segment(ranges[-1], frames=get_frames_from_segment(ranges[-1]) + 1)
    elif len(ranges) > 0 and get_end_time_from_segment(ranges[-1], -1) < 0:
        change = ranges[-1]
        update_segment(change,
                        videosegment = os.path.split(vidAnalysisComponents.writer.filename)[1],
                        endtime = vidAnalysisComponents.elapsed_time_two - vidAnalysisComponents.rate_two * 2,
                        rate = vidAnalysisComponents.fps,
                        type = 'video',
                        endframe =get_start_frame_from_segment(change) + get_frames_from_segment(change) - 1)
        vidAnalysisComponents.writer.release()

    return True

def compareChange(vidAnalysisComponents, ranges=list(), arguments={},compare_function=default_compare):
    if len(ranges) == 0:
        change = create_segment(mask=vidAnalysisComponents.mask,
                                starttime=vidAnalysisComponents.elapsed_time_one - vidAnalysisComponents.rate_one,
                                rate=vidAnalysisComponents.fps_one,
                                startframe=vidAnalysisComponents.time_manager.frameSinceBeginning,
                                endframe=vidAnalysisComponents.time_manager.frameSinceBeginning,
                                endtime=-1,
                                frames=1,
                                type='video')
        ranges.append(change)
    else:
        update_segment(ranges[-1], frames=get_frames_from_segment(ranges[-1]) + 1)


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
    change = create_segment(starttime=0,
                            startframe=1,
                            type='video',
                            rate=analysis_components.fps_one,
                            mask=compare_result,
                            endtime=get_end_time_from_segment(entireVideoMaskSet[0]),
                            endframe=get_end_frame_from_segment(entireVideoMaskSet[0]),
                            frames=get_frames_from_segment(entireVideoMaskSet[0]))
    return [change],[]

def cutCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None, analysis={}):
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
        if get_frames_from_segment(audioMaskSetOne[0]) != get_frames_from_segment(audioMaskSetTwo[0]):
            startframe = (get_start_frame_from_segment(maskSet[0])-1)/get_rate_from_segment(maskSet[0])*get_rate_from_segment(audioMaskSetOne[0])
            #int(get_start_time_from_segment(maskSet[0])*get_rate_from_segment(audioMaskSetOne[0])/1000.0)
            realframediff = get_frames_from_segment(audioMaskSetOne[0]) - get_frames_from_segment(audioMaskSetTwo[0])
            realtimediff = get_end_time_from_segment(audioMaskSetOne[0]) - get_end_time_from_segment(audioMaskSetTwo[0])
            endtime=get_start_time_from_segment(maskSet[0])+ realframediff*1000.0/get_rate_from_segment(audioMaskSetOne[0])
            maskSet.append(
                create_segment(
                    starttime=get_start_time_from_segment(maskSet[0]),
                    startframe=startframe,
                    endtime=endtime,
                    endframe=startframe + realframediff - 1,
                    type='audio',
                    rate=get_rate_from_segment(audioMaskSetOne[0])))
        else:
            errors.append('Audio must also be cut if the audio and video are in source and target files')
    return maskSet, errors

def pasteCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None, analysis={}):
    if arguments['add type'] == 'replace':
        return __runDiff(fileOne, fileTwo, name_prefix, time_manager, detectChange,
                         arguments=arguments,
                         compare_function=tool_set.mediatedCompare,
                         convert_function=tool_set.convert16bitcolor
                         )
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager, addDetect,
                     arguments=arguments,
                     compare_function=tool_set.morphologyCompare,
                     convert_function=tool_set.convert16bitcolor)


def maskCompare(fileOne, fileTwo, name_prefix, time_manager, arguments={}, analysis={}):
    import copy
    args = copy.copy(arguments)
    args['distribute_difference'] = True
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager,
                       compareChange,
                       arguments=args,
                       compare_function=tool_set.morphologyCompare,
                       convert_function=tool_set.convert16bitcolor)

def warpCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None,analysis={}):
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager, addDetect, arguments=arguments)


def mediatedDetectedCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=None, analysis={}):
    return __runDiff(fileOne, fileTwo, name_prefix, time_manager, detectChange,
                     compare_function=tool_set.mediatedCompare,
                     convert_function = tool_set.convert16bitcolor,
                     arguments = arguments)

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
    real_segments = getMaskSetForEntireVideo(FileMetaDataLocator(filename),
                             media_types=[media_type])
    if sets_tuple is None:
        return real_segments

    for segment in sets_tuple[0]:
        real_segment = [real_seg for real_seg in real_segments if get_type_of_segment(real_seg) == get_type_of_segment(segment)][0]
        if get_end_frame_from_segment(real_segment) < get_end_frame_from_segment(segment):
            update_segment(segment,
                        endframe=get_end_frame_from_segment(real_segment),
                        endtime=get_end_time_from_segment(real_segment))
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
            drop_mask_from_segment(item)
        edge['masks count'] = len(video_masks)
        edge['videomasks'] = video_masks


def formMaskForSource(source_file_name, mask_file_name, name, startTimeandFrame=(0, 1), stopTimeandFrame=None):
    """
    BUild a mask from file from a source video file.
    Non-Zero values = selected.
    :param source_file_name:
    :param mask_file_name:
    :param name:
    :param startTimeandFrame:
    :param stopTimeandFrame:
    :return:
    """
    source_file_tuples = getMaskSetForEntireVideoForTuples(
        FileMetaDataLocator(source_file_name),
        start_time_tuple=startTimeandFrame,
        end_time_tuple=stopTimeandFrame)
    mask_file_tuples = getMaskSetForEntireVideoForTuples(FileMetaDataLocator(mask_file_name))
    if get_frames_from_segment(source_file_tuples[0]) != get_frames_from_segment(mask_file_tuples[0]):
        return None
    subs = videoMasksFromVid(mask_file_name,
                             name,
                              offset=startTimeandFrame[1]-1)
    if get_frames_from_segment(subs[0]) != get_frames_from_segment(mask_file_tuples[0]):
        return None
    if get_start_frame_from_segment(subs[0]) != get_start_frame_from_segment(
            source_file_tuples[0]):
        return None
    return subs

def videoMasksFromVid(vidFile, name, startTimeandFrame=(0,1), stopTimeandFrame=None, offset=0, writerFactory=tool_set.GrayBlockFactory()):
    """
    Convert video file to mask
    :param vidFile:
    :param name:
    :param startTimeandFrame:
    :param stopTimeandFrame:
    :return:
    """
    time_manager = tool_set.VidTimeManager(startTimeandFrame=startTimeandFrame, stopTimeandFrame=stopTimeandFrame)
    vid_cap = buildCaptureTool(vidFile)
    fps = vid_cap.get(cv2api_delegate.prop_fps)
    writer = writerFactory(os.path.join(os.path.dirname(vidFile), name), fps)
    segment = create_segment(rate=fps, type='video', startframe=offset+1, starttime=offset*(1000.0/fps), frames=0)
    last_time = 0
    while vid_cap.isOpened():
        ret_one = vid_cap.grab()
        elapsed_time = vid_cap.get(cv2api_delegate.prop_pos_msec)
        if not ret_one:
            break
        time_manager.updateToNow(elapsed_time)
        if time_manager.isBeforeTime():
            update_segment(segment,
                           startframe=time_manager.frameSinceBeginning+ offset,
                           starttime=offset*(1000.0/fps) + elapsed_time - 1000.0/fps)
            continue
        if time_manager.isPastTime():
            break
        ret, frame = vid_cap.retrieve()
        mask = ImageWrapper(frame, to_mask=True).invert()
        if 'mask' not in segment:
            segment['mask'] = mask.to_array()
        writer.write(mask.to_array(), last_time, time_manager.frameSinceBeginning+ offset)
        last_time = offset*(1000.0/fps) + elapsed_time - 1000.0/fps
    update_segment(segment,
                   endframe=time_manager.frameSinceBeginning + offset,
                   endtime=last_time,
                   videosegment=os.path.split(writer.get_file_name())[1])
    return [segment]

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
        result = __runDiff(fileOne, fileTwo, name_prefix,time_manager,
                           detectChange,
                           arguments=arguments,
                           compare_function=tool_set.morphologyCompare,
                           convert_function=tool_set.convert16bitcolor)
    if analysis is not None:
        analysis['startframe'] = time_manager.getStartFrame()
        analysis['stopframe'] = time_manager.getEndFrame()
    return result

def audioWrite(fileOne, amount, channels=2, block=8192):
    import wave, struct
    wf = wave.open(fileOne,'wb')
    try:
        wf.setparams((channels, 2, 44100, 0, 'NONE', 'not compressed'))
        while amount > 0:
            value = np.random.randint(-32767, 32767,min(amount,block),dtype=np.int16)
            packed_value = value.tobytes()
            wf.writeframesraw(packed_value)
            amount-=block
    finally:
        wf.close()
    return amount

def twos_comp_np(vals, bits):
    """compute the 2's compliment of array of int values vals"""
    vals[vals &  (1<<(bits-1)) != 0] -= (1<<bits)
    return vals

def buf_to_int(buffer, width):
    if width == 1:
        return np.fromstring(buffer, 'Int8')
    elif width == 2:
        return np.fromstring(buffer, 'Int16')
    elif width == 3:
        ub_t = np.fromstring(buffer, 'UInt8').astype(np.uint64)
        lsb = ub_t[2::3]
        range_shape = lsb.shape[0] * 3
        ub_t = ((ub_t[0:range_shape:3] << 16) + (ub_t[1:range_shape:3] << 8) + lsb)
        return twos_comp_np(ub_t.astype(np.int64),24)
    return np.fromstring(buffer,'Int32')


class AudioReader:


    """
    Tool to assist reading and comparing audio streams.
    The audio streams may be mixed mono/stereo and streams could be swapped, comparing
    left from to right on the other.
    """

    def __init__(self,filename, channel, block=524288):
        """

        :param filename:
        :param channel: left,right,both,all,stereo (the last three mean the same thing!)
        :param block: how much to read and compare at one time in terms of samples!
        """
        import wave
        self.handle = wave.open(filename, 'rb')
        self.count = self.handle.getnframes()
        self.channels = self.handle.getnchannels()
        self.width = self.handle.getsampwidth()
        self.skipchannel = self.channels if channel.lower() in ['left','right'] and self.channels > 1 else 1
        self.startchannel = 1 if channel == 'right' and self.channels > 1 else 0
        self.channel = channel
        self.framesize = self.width * self.channels
        self.block = block
        self.buffer = self.handle.readframes(min(self.count,block))
        self.block_pos = 0
        self.pos = 0
        self.framerate = self.handle.getframerate()

    def setskipchannel(self, skipchannel):
        """
        Set based on other reader.
        If other reader is 'mono'  and this is sterio left, for example,
        then skip a channel.
        :param skipchannel:
        :return:
        """
        self.skipchannel = self.channels if skipchannel else 1
        self.startchannel = 1 if self.channel == 'right' and self.skipchannel > 1 else 0

    def read(self):
        """
        Advance sample pointer, read if necessary
        :return:
        """
        if self.pos >= self.count:
            return False
        if self.pos == self.block_pos + self.block:
            self.buffer = self.handle.readframes(min(self.count-self.block_pos, self.block))
            self.block_pos += self.block
        self.pos += 1
        return True

    def nextBlock(self):
        """
        Read entire next block
        :return:
        """
        self.pos = self.block_pos = self.block_pos + self.block
        if self.pos > self.count:
            self.pos = self.count
            return False
        self.buffer = self.handle.readframes( min(self.count - self.block_pos, self.block))
        return True

    def getBlock(self, starting_frame, frames):
        """
        Get a block of frames.  Cannot go backwards. The block read must be at or ahead of the current starting_frame
        :param starting_frame: starting frame
        :param frames: number of frames in block
        :return: a sub block of the current buffer given its offset to starting_frame
        """
        if starting_frame - self.block_pos < 0:
            raise ValueError('Referenced starting_frame prior to current block')
        while starting_frame > (self.block_pos + self.block):
            self.nextBlock()
        start = starting_frame - self.block_pos
        #in buffer terms, each channel is separate position
        end = (start+frames) * self.channels
        buffer = buf_to_int(self.buffer, self.width)
        while end > buffer.shape[0]:
            if self.nextBlock():
                buffer = np.append (buffer,buf_to_int(self.buffer, self.width))
            else:
                break
        return buffer[self.startchannel+start*self.channels:end:self.skipchannel]

    def plot(self, a, b, pos, channel=0, sample=1000):
        import matplotlib.pyplot as plt
        a = a[pos + channel:pos + channel + sample:self.channels]
        b = b[pos + channel:pos + channel + sample:self.channels]
        Time = np.linspace(0, sample, num=sample / self.channels)
        plt.figure(1)
        plt.title('Signal Wave...')
        plt.plot(Time, a, color="red")
        plt.figure(2)
        plt.plot(Time, b, color="green")
        plt.show()

    def compareToOtherReader(self, anotherReader, min_threshold=3, smooth=32):
        """
        Compare buffer to buffer.
        :param anotherReader:
        :param min_threshold:
        :return: start frame in self that does not match the other
        """
        a = buf_to_int(self.buffer, self.width)
        b = buf_to_int(anotherReader.buffer, anotherReader.width)
        # consider a is stereo, b is mono, so a.skipchannel = 2
        # a is 16, b is 8 in length
        # 8*2  = 16, so a length is the 16 with skip of 2.
        # b is 8 (smaller than a*1=16), with a skipchannel of 1
        diff_size = len(a)/self.skipchannel - len(b)/anotherReader.skipchannel
        if diff_size > 0:
            default_mismatch = self.block_pos + len(b)/anotherReader.skipchannel,self.block_pos + len(a)/self.skipchannel
        else:
            default_mismatch = None
        a = a[self.startchannel:min(len(a),len(b)*self.skipchannel/anotherReader.skipchannel):self.skipchannel]
        b = b[anotherReader.startchannel:min(len(a)*anotherReader.skipchannel,len(b)):anotherReader.skipchannel]
        diffs = a - b
        if np.all(diffs==0):
            return default_mismatch
        bychannel_sum = sum(
            [diffs[i::self.channels] for i in range(self.channels)]) if self.skipchannel == 1 else diffs
        bychannel_avg = tool_set.moving_average(bychannel_sum/self.channels,smooth)
        positions = np.where(abs(bychannel_avg) > min_threshold)
        if len(positions) == 0 or len(positions[0]) == 0:
            return default_mismatch
        base_start = max(positions[0][0]-smooth,0)
        base_end = positions[0][-1]+smooth
        positions = np.where(abs(bychannel_sum[base_start:base_end])> min_threshold)
        new_base_start = base_start + positions[0][0]
        new_base_end = base_start+ positions[0][-1]
        return self.block_pos+new_base_start,self.block_pos+new_base_end

    def syncToFrame(self, frame):
        """
        Advance to position.
        Read blocks when needed.
        Do not go backwards behind the current block.
        :param position:
        :return:
        """
        if frame < self.block_pos:
            self.pos = self.block_pos
        else:
            while frame>(self.block_pos+self.block):
                self.nextBlock()
            self.pos = frame

    def compareBlock(self, position, block, smooth=8):
        """
        Compare the provided block to a bloack at position.
        :param position:
        :param block:
        :param smooth:
        :return:
        """
        # if skipchannel > 1, then mono to mono
        # if skipchannel == 1 and channels > 1, then stereo to stereo
        l = len(block) / (self.channels/self.skipchannel)
        my_block = self.getBlock(position, l)
        if len(my_block) < len(block):
            return -1
        diffs = my_block - block
        bychannel_sum = sum(
            [diffs[i::self.channels] for i in range(self.channels)]) if self.skipchannel == 1 else diffs
        bychannel_avg = tool_set.moving_average(bychannel_sum / self.channels, smooth)
        return np.sum(abs(bychannel_avg))

    def findBlock(self, block, start_frame,
                  min_threshold=99999999,
                  residual=None):
        """

        :param block:
        :param position:
        :param min_threshold:
        :return: the sample # of the begining of the where the block is found in self
        """
        self.syncToFrame(start_frame)
        a = buf_to_int(self.buffer, self.width)
        if residual is not None:
            a = np.append(residual,a)
        #change to channel positions
        position = (start_frame-self.block_pos) * self.channels + (len(residual) if residual is not None else 0)
        start_frame_difference = self.block_pos - (len(residual) if residual is not None else 0)/self.channels

        best = min_threshold
        best_p = 0
        # The block is from getBlock, which takes into account
        # the skip and channel properties of the other stream.
        # If the other is stereo and this is mono, then block is length mono
        # self.channels / self.skipchannel = 1
        # if this block is stereo and other mono, then block is length mono
        # self.channels / self.skipchannel = 1
        # if both are stereo, then block length is double the frames and then self.channels / self.skipchannel = 2
        factor = self.channels / self.skipchannel
        l = len(block)*self.skipchannel
        # if skip channel, then need more data
        end_len = len(a)
        while (position + l) <= end_len:
            diffs = a[self.startchannel+position:position+l:self.skipchannel] - block
            if np.all(diffs==0):
                return start_frame_difference + position/self.channels, 0
            s = sum(abs(diffs))
            if s < best:
                best = s
                best_p = start_frame_difference + position/self.channels
            position+=self.channels
        if self.hasMore():
            if self.nextBlock():
                # residual is what we need to continue searching a step at a time
                # skipchannel != 1 in the case where this block is stereo and the other is mono
                # which means we need double the length to fulfill the obligation of matching
                other_best_p, other_best = self.findBlock(block,self.pos-(len(block)/factor),best,
                                      residual=a[-l:])
                best_p, best = (other_best_p, other_best) if other_best < best else (best_p, best)
        return best_p, best

    def getData(self):
        """

        :return: raw buffer string for one frame/smample
        """
        position = self.pos - self.block_pos - 1
        return self.buffer[position * self.framesize + self.startchannel*self.width:position * self.framesize + self.framesize + self.startchannel*self.width:self.skipchannel]

    def getOrd(self):
        """

        :return: Ordinal for one frame/smample
        """
        position = self.pos - self.block_pos - 1
        return sum([ord(c) for c in self.buffer[
                                        position * self.framesize + self.startchannel*self.width:position * self.framesize + self.framesize + self.startchannel*self.width:self.skipchannel]])

    def hasMore(self):
        return self.pos < self.count

    def close(self):
        self.handle.close()

class AudioCompare:

    def __init__(self, fileOne, fileTwo, name_prefix, time_manager,arguments={},
                 analysis={}):
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
        self.fileOne = fileOne
        self.fileTwo = fileTwo
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
        segment = None
        end = None
        while self.fone.hasMore() and self.ftwo.hasMore():
            position = self.fone.compareToOtherReader(self.ftwo)
            self.fone.nextBlock()
            self.ftwo.nextBlock()
            if position is not None:
                self.time_manager.updateToNow(position[1] / float(framerateone))
                if segment is not None and end is not None and position[0] - end >= framerateone:
                    update_segment(segment,
                                   endframe=end,
                                   endtime= float(end) / float(framerateone) * 1000.0)
                    sections.append(segment)
                    segment = None
                end = position[1]
                if segment is None:
                    start = position[0]
                    segment = create_segment(startframe=start+1,
                               starttime= max(0,float(start) / float(framerateone) * 1000.0),
                               endframe= end,
                               endtime= float(end-1) / float(framerateone) * 1000.0,
                               rate=framerateone,
                               type= 'audio',
                               frames= 1)
                    if self.time_manager.spansToEnd():
                        update_segment(segment,
                                       endframe = self.ftwo.count -1,
                                       rate=frameratetwo,
                                       endtime=(self.ftwo.count -1 )/ float(frameratetwo) * 1000.0)
                        return [segment], []
                elif self.maxdiff is not None and end - start > self.maxdiff:
                    break
        if segment is not None:
            update_segment(segment,
                           endframe=end,
                           endtime=float(end) / float(framerateone) * 1000.0)
            sections.append(segment)
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
            sections = [create_segment(
                         startframe=startframe,
                         starttime=starttime,
                         rate=framerateone,
                         endframe=stopframe,
                         type='audio',
                         endtime=float(stopframe) / float(framerateone) * 1000.0)
                        ]
        return sections, errors

    def __findMatch(self,position):
        dataone = self.fone.getBlock(position, min(self.ftwo.framerate*4,self.fone.count-position))
        return self.ftwo.findBlock(dataone, position)[0]

    def __insert(self):
        framerateone = self.fone.framerate
        section = None
        while self.fone.hasMore() and self.ftwo.hasMore() > 0 and section is None:
            position = self.fone.compareToOtherReader(self.ftwo)
            # position is where the two streams begin to differ
            if position is not None:
                self.time_manager.updateToNow(position[0] / float(framerateone))
                start = position[0]
                end = start + (self.ftwo.count - self.fone.count)
                section = create_segment(startframe=start+1,
                                         starttime=max(0,float(start) / float(framerateone)),
                                         endframe=end,
                                         endtime=float(end-1) / float(framerateone),
                                         rate=framerateone,
                                         type='audio')
                break
            self.fone.nextBlock()
            self.ftwo.nextBlock()
        if section is not None:
            return [section], []
        elif self.ftwo.count > self.fone.count:
            return [create_segment(startframe=self.fone.count,
                                         starttime=max(0,float(self.fone.count) / float(framerateone)),
                                         endframe=self.fone.count,
                                         endtime=float(self.fone.count) / float(framerateone),
                                         rate=framerateone,
                                         type='audio')],[]
        else:
            return [],['Warning: Could not find insertion point in target media']

    def __delete(self):
        framerateone = self.fone.framerate
        frameratetwo = self.ftwo.framerate
        errors = [
            'Channel selection is all however only one channel is provided.'] if self.channel == 'all' and self.fone.channels > self.ftwo.channels else []
        segment = None
        if (self.fone.count - self.ftwo.count) == 0:
            if self.fone.channels != self.ftwo.channels:
                return [create_segment(startframe=1,
                                             starttime=0,
                                             endframe=self.ftwo.count-1,
                                             endtime=float(self.ftwo.count - 1) / float(framerateone) * 1000.0,
                                             rate=framerateone,
                                             type='audio',
                                             frames=1)],[]
            return [],[]
        while self.fone.hasMore() and self.ftwo.hasMore():
            position = self.fone.compareToOtherReader(self.ftwo)
            if position is not None:
                self.time_manager.updateToNow(position[1] / float(framerateone))
                if segment is None:
                    start = position[0]
                    end = start + (self.fone.count - self.ftwo.count)
                    segment = create_segment(startframe=start + 1,
                                             starttime=max(0, float(start) / float(framerateone) * 1000.0),
                                             endframe=end,
                                             endtime=float(end - 1) / float(framerateone) * 1000.0,
                                             rate=framerateone,
                                             type='audio',
                                             frames=1)
                    return  [segment], errors
            elif segment is None:
                self.fone.nextBlock()
                self.ftwo.nextBlock()
            else:
                break
        return [], ['Warning: Could not find deletion point in target media']


    def __initiateCompare(self,compareFunc):
        import wave
        if len(self.errorsone) > 0 and len(self.errorstwo) == 0:
            try:
                ftwo = wave.open(self.fileTwoAudio, 'rb')
                counttwo = ftwo.getnframes()
                startframe = self.time_manager.getExpectedStartFrameGiveRate(ftwo.getframerate(), defaultValue=1)
                endframe = startframe + counttwo  - 1
                return [create_segment(startframe=startframe,
                         starttime=float(startframe) / float(ftwo.getframerate()) * 1000.0,
                         rate= ftwo.getframerate(),
                         endframe= endframe,
                         endtime=float(endframe) / float(ftwo.getframerate()) * 1000.0,
                         type= 'audio',
                         frames=counttwo)], []
            finally:
                ftwo.close()
        if len(self.errorstwo) > 0:
            return list(), self.errorstwo
        self.fone = AudioReader(self.fileOneAudio, self.channel, 524288)
        try:
            self.ftwo = AudioReader(self.fileTwoAudio,self.channel, 524288)
            self.fone.setskipchannel ( self.fone.channels > self.ftwo.channels )
            self.ftwo.setskipchannel ( self.fone.channels < self.ftwo.channels )
            if self.fone.framerate != self.ftwo.framerate or self.fone.width != self.ftwo.width:
                self.time_manager.updateToNow(float(self.fone.count) / float(self.fone.framerate))
                startframe = self.time_manager.getExpectedStartFrameGiveRate(self.ftwo.framerate, defaultValue=1)
                endframe = self.time_manager.getExpectedEndFrameGiveRate(self.ftwo.framerate, defaultValue=self.ftwo.count)
                return [create_segment(startframe= startframe,
                         starttime= float(startframe) / float(self.ftwo.framerate) * 1000.0,
                         rate= self.ftwo.framerate,
                         endframe= endframe,
                         endtime= float(endframe) / float(self.ftwo.framerate) * 1000.0,
                         type= 'audio',
                         frames= self.ftwo.count)], []
            return compareFunc()
        finally:
            self.ftwo.close()
            self.fone.close()

    def deleteCompare(self):
        return clampToEnd(self.fileTwo, self.__initiateCompare(self.__delete), 'audio')

    def audioCompare(self):
        return clampToEnd(self.fileTwo, self.__initiateCompare(self.__compare), 'audio')

    def audioInsert(self):
        return clampToEnd(self.fileTwo, self.__initiateCompare(self.__insert), 'audio')


def audioInsert(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    ac = AudioCompare(fileOne,fileTwo,name_prefix,time_manager,arguments=arguments,analysis=analysis)
    return ac.audioInsert()

def audioCompare(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    ac = AudioCompare(fileOne,fileTwo,name_prefix,time_manager,arguments=arguments,analysis=analysis)
    return ac.audioCompare()

def audioDeleteCompare(fileOne, fileTwo,name_prefix, time_manager,arguments={},analysis={}):
    ac = AudioCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=arguments, analysis=analysis)
    return ac.deleteCompare()

def audioAddCompare(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    if 'add type' in arguments and arguments['add type'] == 'insert':
        return audioInsert(fileOne,fileTwo,name_prefix,time_manager, arguments=arguments,analysis=analysis)
    else:
        return audioCompare(fileOne, fileTwo, name_prefix, time_manager, arguments=arguments, analysis=analysis)

def audioSample(fileOne, fileTwo, name_prefix, time_manager,arguments={},analysis={}):
    """
    Confirm fileTwo is sampled from fileOne
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
        fone.setskipchannel( fone.channels > ftwo.channels)
        ftwo.setskipchannel( fone.channels < ftwo.channels)
        try:
            if fone.framerate != ftwo.framerate or fone.width != ftwo.width:
                time_manager.updateToNow(float(ftwo.count) / float(ftwo.framerate))
                return [create_segment(startframe=1,
                         starttime= 0,
                         rate=ftwo.framerate,
                         endframe= ftwo.count,
                         type='audio',
                         endtime= float(ftwo.count) / float(ftwo.framerate)*1000.0,
                         frames=ftwo.count)], []
            startframe = int(time_manager.getExpectedStartFrameGiveRate(fone.framerate, defaultValue=1))
            block_two = ftwo.getBlock(0, min(ftwo.count,ftwo.framerate*4))
            errors = []
            # try from the beginning of the block
            position, diff = fone.findBlock(block_two, fone.block_pos)
            if diff != 0:
                    errors = ['Could not find sample in source media']
            else:
                    startframe= position + 1
            endframe = startframe + ftwo.count - 1
            starttime = (startframe-1) / float(fone.framerate)*1000.0
            return [create_segment(
                     startframe= startframe,
                     starttime= starttime,
                     rate= fone.framerate,
                     endframe= endframe,
                     type= 'audio',
                     endtime= float(endframe) / float(fone.framerate)*1000.0,
                     frames= ftwo.count)], errors
        finally:
            ftwo.close()
    finally:
        fone.close()
    return [],['Unable to open one of the audio streams']


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
    segment = create_segment(rate= fps, type='video', startframe=1, starttime=0, frames=0)
    exifdiff = None
    compare_args = {'tolerance': getValue(arguments, 'tolerance', 0.0001)}
    compare_args.update(arguments)
    try:
        last_time = 0
        while vid_cap.isOpened():
            ret_one = vid_cap.grab()
            elapsed_time = vid_cap.get(cv2api_delegate.prop_pos_msec)
            if not ret_one:
                break
            time_manager.updateToNow(elapsed_time)
            if time_manager.isBeforeTime():
                update_segment(segment,
                               startframe = time_manager.frameSinceBeginning,
                               starttime = elapsed_time - 1000.0/fps)
                continue
            if time_manager.isPastTime():
                break
            ret, frame =vid_cap.retrieve()
            if exifdiff is None:
                exifforvid = vid_cap.get_exif()
                exifdiff = exif.comparexif_dict(exifforvid, img_wrapper.get_exif())
            mask,analysis,error = tool_set.createMask(ImageWrapper(frame),img_wrapper,
                                invert=False,
                                arguments=compare_args,
                                alternativeFunction=tool_set.convertCompare)
            if 'mask' not in segment:
                segment['mask'] = mask.to_array()
            writer.write(mask.to_array(),last_time,time_manager.frameSinceBeginning)
            last_time = elapsed_time
        update_segment(segment,
                       endframe=time_manager.frameSinceBeginning,
                       endtime=elapsed_time - 1000.0/fps,
                       videosegment=writer.get_file_name())
        return [segment], analysis, exifdiff
    finally:
        vid_cap.release()
        writer.close()
    return [], analysis, exif.comparexif_dict(exif,img_wrapper.get_exif())

def __runDiff(fileOne, fileTwo, name_prefix, time_manager, opFunc,
              compare_function=tool_set.morphologyCompare,
              convert_function=tool_set.convert16bitcolor,
              arguments={}):
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
    def compare_func(x,
                     y,
                     arguments=None):
        return tool_set.createMask(ImageWrapper(x),
                                   ImageWrapper(y),
                                   False,
                                   convertFunction=convert_function,
                                   alternativeFunction=compare_function,
                                   arguments=arguments)[0].to_array()

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
    compare_args = arguments if arguments is not None else {}
    dump_dir =  getValue(arguments,'dump directory',False)
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
            if dump_dir:
                from cv2 import imwrite
                imwrite(os.path.join(dump_dir,'one_{}.png'.format(time_manager.frameSinceBeginning)), frame_one)
                imwrite(os.path.join(dump_dir,'two_{}.png'.format(time_manager.frameSinceBeginning)), frame_two)
            if frame_one.shape != frame_two.shape:
                return getMaskSetForEntireVideo(FileMetaDataLocator(fileOne)),[]
            analysis_components.mask = tool_set.createMask(ImageWrapper(frame_one),
                                                           ImageWrapper(frame_two),
                                                           False,
                                                           convertFunction=convert_function,
                                                           alternativeFunction=compare_function,
                                                           arguments=compare_args)[0].to_array()
            if not opFunc(analysis_components,ranges,compare_args,compare_function=compare_func):
                done = True
                break

        analysis_components.mask = 0
        if analysis_components.grabbed_one and analysis_components.frame_one is None:
            analysis_components.retrieveOne()
        if analysis_components.grabbed_two and analysis_components.frame_two is None:
            analysis_components.retrieveTwo()
        if not done:
            opFunc(analysis_components,ranges,arguments)
    finally:
        analysis_components.vid_one.release()
        analysis_components.vid_two.release()
        analysis_components.writer.close()
    if analysis_components.one_count == 0:
        if os.path.exists(fileOne):
            raise ValueError(
                'Mask Computation Failed to a read video {}.  FFMPEG and OPENCV may not be installed correctly or the videos maybe empty.'.format(fileOne))
        else:
            raise ValueError(
                'Mask Computation Failed to a read video {}.  File Missing'.format(
                    fileOne))
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
    reader_manager = tool_set.GrayBlockReaderManager()
    writer_manager = tool_set.GrayBlockWriterManager()
    if tool_set.fileType(start_file_name) == 'image':
        image = tool_set.openImage(start_file_name)
        new_mask_set = []
        destination_video = cv2api_delegate.videoCapture(dest_file_name)
        try:
            for mask_set in video_masks:
                rate = reader.fps
                change = create_segment(start_frame=get_start_frame_from_segment(mask_set, 1),
                                        end_frame=get_end_frame_from_segment(mask_set, 1),
                                        type=get_type_of_segment(mask_set))
                reader = reader_manager.create_reader(os.path.join(directory, get_file_from_segment(mask_set)),
                                                      start_frame=get_start_frame_from_segment(mask_set),
                                                      start_time=get_start_time_from_segment(mask_set),
                                                      end_frame=get_end_frame_from_segment(mask_set))
                writer = writer_manager.create_writer(reader)
                first_mask = None
                count = 0
                vid_frame_time = 0
                max_analysis = 0
                while True:
                    frame_time = reader.current_frame_time()
                    frame_no = reader.current_frame()
                    mask = reader.read()
                    if mask is None:
                        break
                    if frame_time < vid_frame_time:
                        continue
                    frame, vid_frame_time = __get_video_frame(destination_video, frame_time)
                    if frame is None:
                        new_mask = np.ones(mask.shape) * 255
                    else:
                        new_mask, analysis = tool_set.interpolateMask(ImageWrapper(mask), image,
                                                                      ImageWrapper(frame))
                        if new_mask is None:
                            new_mask = np.asarray(tool_set.convertToMask(image))
                            max_analysis += 1
                        if first_mask is None:
                            update_segment(change,
                                           mask=new_mask,
                                           starttime=frame_time,
                                           rate=rate,
                                           type='video',
                                           startframe=frame_no)
                            first_mask = new_mask
                    count += 1
                    writer.write(new_mask, vid_frame_time, frame_no)
                    if max_analysis > 10:
                        break
                update_segment(change,
                               endtime=vid_frame_time,
                               frames=count,
                               rate=rate,
                               videosegment=os.path.split(writer.filename)[1],
                               type='video')
                if first_mask is not None:
                    new_mask_set.append(change)
        finally:
            reader_manager.close()
            writer_manager.close()
            destination_video.release()
        return new_mask_set, []
    # Masks cannot be generated for video to video....yet
    return [], []


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
        drop_sf = get_start_frame_from_segment(bound,1)
        drop_ef = get_end_frame_from_segment(bound,-1)
        if drop_ef < 0:
            drop_ef = None
        new_mask_set = []
        reader_manager = tool_set.GrayBlockReaderManager()
        writer_manager = tool_set.GrayBlockWriterManager()
        try:
            for mask_set in video_masks:
                if get_type_of_segment(mask_set) != expectedType:
                    new_mask_set.append(mask_set)
                    continue
                mask_sf = get_start_frame_from_segment(mask_set)
                mask_ef = get_end_frame_from_segment(mask_set,-1)
                if mask_ef < 0:
                    mask_ef = None
                rate = get_rate_from_segment(mask_set)
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
                if get_file_from_segment(mask_set) is None:
                    new_mask_set.extend(dropFramesWithoutMask([bound],[mask_set],keepTime=keepTime))
                    continue
                reader = reader_manager.create_reader(get_file_from_segment(mask_set),
                                                  start_frame=get_start_frame_from_segment(mask_set),
                                                  start_time=get_start_time_from_segment(mask_set),
                                                  end_frame=get_end_frame_from_segment(mask_set))
                writer = writer_manager.create_writer(reader)
                if keepTime:
                    elapsed_count = 0
                    elapsed_time = 0
                else:
                    if drop_ef is not None:
                        elapsed_time = get_end_frame_from_segment(bound) - get_start_time_from_segment(bound)
                        elapsed_count = drop_ef - drop_sf
                    else:
                        elapsed_time = 0
                        elapsed_count = 0
                startcount = get_start_frame_from_segment(mask_set)
                starttime = get_start_time_from_segment(mask_set)
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
                        writer.write(mask, last_time, frame_count)
                        written_count += 1
                    if written_count > 0:
                        change = create_segment(
                            starttime=starttime,
                            type=get_type_of_segment(mask_set),
                            startframe=startcount,
                            endtime=last_time,
                            endframe=frame_count - 1,
                            rate=rate,
                            error=get_error_from_segment(mask_set),
                            videosegment=writer.filename)
                        new_mask_set.append(change)
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
                    change = create_segment(
                        starttime=starttime,
                        type=get_type_of_segment(mask_set),
                        startframe=get_end_frame_from_segment(mask_set) - elapsed_count - written_count + 1,
                        endtime=last_time - elapsed_time,
                        endframe=get_end_frame_from_segment(mask_set) - elapsed_count,
                        rate=rate,
                        frames=written_count,
                        error=get_error_from_segment(mask_set),
                        videosegment=writer.filename)
                    new_mask_set.append(change)
        finally:
            writer_manager.close()
            reader_manager.close()
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
        drop_sf = get_start_frame_from_segment(bound,1)
        drop_ef = get_end_frame_from_segment(bound,0)
        if drop_ef < drop_sf:
            drop_ef = None
        drop_st = get_start_time_from_segment(bound, 0)
        drop_et = get_end_time_from_segment(bound,0)
        if drop_et < drop_st or drop_et < 0.00001:
            drop_et = None
        new_mask_set = []
        for segment in video_masks:
            if get_type_of_segment(segment) != expectedType:
                new_mask_set.append(segment)
                continue
            mask_sf = get_start_frame_from_segment(segment,1)
            mask_st = get_start_time_from_segment(segment,0)
            mask_ef = get_end_frame_from_segment(segment)
            if mask_ef < mask_sf:
                mask_ef = None
            elif drop_sf - mask_ef > 0:
                new_mask_set.append(segment)
                continue
            rate = get_rate_from_segment(segment)
            # before remove region
            # at the end and time is not change
            if keepTime and drop_ef is not None and (drop_ef - mask_sf) < 0:
                new_mask_set.append(segment)
                continue
            if (drop_ef is None or (mask_ef is not None and drop_ef - mask_ef >= 0)) and \
                    (drop_sf - mask_sf <= 0):
                # started after drop and subsummed by drop
                continue
            #occurs after drop region
            start_diff_frame = drop_sf - mask_sf
            start_diff_time = drop_st - mask_st
            if start_diff_frame > 0:
                change = create_segment(starttime=get_start_time_from_segment(segment),
                                        type=get_type_of_segment(segment),
                                        startframe=get_start_frame_from_segment(segment),
                                        endtime=get_start_time_from_segment(segment) + start_diff_time - 1000.0/rate,
                                        endframe=get_start_frame_from_segment(segment)+start_diff_frame - 1,
                                        rate =get_rate_from_segment(segment),
                                        error= get_error_from_segment(segment)
                                        )
                new_mask_set.append(change)
            if drop_ef is not None:
                 end_diff_frame = drop_ef  - mask_ef
                 if end_diff_frame < 0:
                    end_adjust_frame = drop_ef - drop_sf + 1
                    end_adjust_time = drop_et - drop_st + 1000.0/rate
                    change = create_segment(starttime=get_end_time_from_segment(bound) + 1000.0/rate,
                                        type=get_type_of_segment(segment),
                                        startframe=drop_ef + 1,
                                        endtime=get_end_time_from_segment(segment),
                                        endframe=get_end_frame_from_segment(segment),
                                        rate =rate,
                                        error= get_error_from_segment(segment)
                                        )
                    if not keepTime:
                        if drop_ef - mask_sf < 0:
                            update_segment(change,
                                           startframe=get_start_frame_from_segment(segment) - end_adjust_frame,
                                           starttime=get_start_time_from_segment(segment) - end_adjust_time,
                                           endframe=get_end_frame_from_segment(segment) - end_adjust_frame,
                                           endtime=get_end_time_from_segment(segment)-  end_adjust_time)
                        else:
                            update_segment(change,
                                           startframe=get_start_frame_from_segment(bound),
                                           starttime=get_start_time_from_segment(bound),
                                           endframe=get_end_frame_from_segment(segment) - end_adjust_frame,
                                           endtime=get_end_time_from_segment(segment) - end_adjust_time
                                           )
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
    if get_start_frame_from_segment(composite_mask_set) < get_start_frame_from_segment(edge_video_mask):
        if get_end_frame_from_segment(composite_mask_set) >= get_end_frame_from_segment(edge_video_mask):
            return [composite_mask_set]
        diff_time = get_end_time_from_segment(composite_mask_set) - get_start_time_from_segment(composite_mask_set)
        change = create_segment(starttime=get_start_time_from_segment(composite_mask_set),
                                startframe= get_start_frame_from_segment(composite_mask_set),
                                rate= get_rate_from_segment(composite_mask_set),
                                error=  get_error_from_segment(composite_mask_set),
                                type=get_type_of_segment(composite_mask_set),
                                endtime=get_start_time_from_segment(edge_video_mask) - 1000.0/get_rate_from_segment(composite_mask_set),
                                endframe= get_start_frame_from_segment(edge_video_mask) -1)
        frames_left_over = get_frames_from_segment(composite_mask_set) - get_frames_from_segment(change)
        time_left_over = diff_time - (get_end_time_from_segment(change) - get_start_time_from_segment(change))
        new_mask_set.append(change)
        change = create_segment(starttime=get_end_time_from_segment(edge_video_mask) - time_left_over + 1000.0/get_rate_from_segment(composite_mask_set),
                                startframe= get_end_frame_from_segment(edge_video_mask) - frames_left_over + 1,
                                rate= get_rate_from_segment(composite_mask_set),
                                type=get_type_of_segment(composite_mask_set),
                                error=  get_error_from_segment(composite_mask_set),
                                endtime=get_end_time_from_segment(edge_video_mask),
                                endframe=get_end_frame_from_segment(edge_video_mask))
        new_mask_set.append(change)
    else:
        if get_end_frame_from_segment(composite_mask_set) <= get_end_frame_from_segment(edge_video_mask):
            return [composite_mask_set]
        diff_frame = get_end_frame_from_segment(edge_video_mask) - get_start_frame_from_segment(composite_mask_set)
        diff_time = get_end_time_from_segment(edge_video_mask) - get_start_time_from_segment(composite_mask_set)
        change = create_segment(starttime=get_start_time_from_segment(edge_video_mask),
                                startframe= get_start_frame_from_segment(edge_video_mask),
                                rate= get_rate_from_segment(composite_mask_set),
                                error=  get_error_from_segment(composite_mask_set),
                                type=get_type_of_segment(composite_mask_set),
                                endtime= get_start_time_from_segment(edge_video_mask) + diff_time,
                                endframe=get_start_frame_from_segment(edge_video_mask) + diff_frame)

        new_mask_set.append(change)
        change = create_segment(starttime=get_end_time_from_segment(edge_video_mask) + 1000.0/get_rate_from_segment(composite_mask_set),
                                startframe= get_end_frame_from_segment(edge_video_mask) + 1,
                                rate= get_rate_from_segment(composite_mask_set),
                                type=get_type_of_segment(composite_mask_set),
                                error=  get_error_from_segment(composite_mask_set),
                                endtime= get_end_time_from_segment(composite_mask_set),
                                endframe= get_end_frame_from_segment(composite_mask_set))
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
    new_mask_set = []
    mask_types = set([get_type_of_segment(composite_video_mask) for composite_video_mask in composite_video_masks])
    reader_manager = tool_set.GrayBlockReaderManager()
    writer_manager = tool_set.GrayBlockWriterManager()
    try:
        for mask_type in mask_types:
            for mask_set in composite_video_masks:
                if get_type_of_segment(mask_set) != mask_type:
                    continue
                for edge_video_mask in edge_video_masks:
                    if get_type_of_segment(edge_video_mask) != get_type_of_segment(mask_set):
                        continue
                    if get_end_frame_from_segment(edge_video_mask) < get_start_frame_from_segment(mask_set) or \
                       get_start_frame_from_segment(edge_video_mask) > get_end_frame_from_segment(mask_set):
                        new_mask_set.append(mask_set)
                        continue
                    if  get_file_from_segment(mask_set) is None:
                        new_mask_set.extend(reverseNonVideoMasks(mask_set,edge_video_mask))
                        continue
                    reader = reader_manager.create_reader(get_file_from_segment(mask_set),
                                                      start_frame=get_start_frame_from_segment(mask_set),
                                                      start_time=get_start_time_from_segment(mask_set),
                                                      end_frame=get_end_frame_from_segment(mask_set))
                    writer = writer_manager.create_writer(reader)
                    frame_count = get_start_frame_from_segment(mask_set)
                    if frame_count < get_start_frame_from_segment(edge_video_mask):
                        frame_count = get_start_frame_from_segment(mask_set)
                        for i in range(get_start_frame_from_segment(edge_video_mask) - frame_count):
                            frame_time = reader.current_frame_time()
                            frame_count = reader.current_frame()
                            mask = reader.read()
                            if mask is None:
                                break
                            writer.write(mask, frame_time, frame_count)
                        change = create_segment(
                            starttime=get_start_time_from_segment(mask_set),
                            startframe=get_start_frame_from_segment(mask_set),
                            rate=get_rate_from_segment(mask_set),
                            error=get_error_from_segment(mask_set),
                            type=get_type_of_segment(mask_set),
                            endtime=frame_time,
                            endframe=frame_count,
                            videosegment=writer.filename)
                        new_mask_set.append(change)

                    if frame_count <= get_end_frame_from_segment(edge_video_mask):
                        masks = []
                        start_time = frame_time
                        for i in range(get_end_frame_from_segment(edge_video_mask) - frame_count):
                            frame_time = reader.current_frame_time()
                            mask = reader.read()
                            if mask is None:
                                break
                            masks.insert(0, mask)
                        if get_end_frame_from_segment(edge_video_mask) >= get_end_frame_from_segment(mask_set):
                            change = create_segment(starttime=get_end_time_from_segment(edge_video_mask) - (
                            frame_time - start_time) + 1000.0 / get_rate_from_segment(mask_set),
                                                    startframe=get_end_frame_from_segment(edge_video_mask) - len(
                                                        masks) + 1,
                                                    endtime=get_end_time_from_segment(edge_video_mask),
                                                    endframe=get_end_frame_from_segment(edge_video_mask),
                                                    type=get_type_of_segment(mask_set),
                                                    error=get_error_from_segment(mask_set),
                                                    rate=get_rate_from_segment(mask_set))
                        else:
                            change = create_segment(starttime=get_start_time_from_segment(edge_video_mask),
                                                    startframe=get_start_frame_from_segment(edge_video_mask),
                                                    endtime=get_start_time_from_segment(edge_video_mask) + (
                                                    frame_time - start_time),
                                                    endframe=get_start_frame_from_segment(edge_video_mask) + len(masks),
                                                    type=get_type_of_segment(mask_set),
                                                    error=get_error_from_segment(mask_set),
                                                    rate=get_rate_from_segment(mask_set))
                        frame_time = get_start_time_from_segment(change)
                        frame_count = get_start_frame_from_segment(change)
                        diff_time = (get_end_time_from_segment(change) - get_start_time_from_segment(change)) / (
                        get_frames_from_segment(change) - 1)
                        for mask in masks:
                            writer.write(mask, frame_time, frame_count)
                            frame_count += 1
                            frame_time += diff_time
                        update_segment(change, videosegment=writer.filename)
                        new_mask_set.append(change)

                    if get_end_frame_from_segment(edge_video_mask) < get_end_frame_from_segment(mask_set):
                        while True:
                            frame_time = reader.current_frame_time()
                            frame_count = reader.current_frame()
                            mask = reader.read()
                            if mask is None:
                                break
                            writer.write(mask, frame_time, frame_count)
                        change = create_segment(
                            starttime=get_start_time_from_segment(edge_video_mask) + 1000 / get_rate_from_segment(
                                mask_set),
                            startframe=get_end_frame_from_segment(edge_video_mask) + 1,
                            endtime=get_end_time_from_segment(mask_set),
                            endframe=get_end_frame_from_segment(mask_set),
                            type=get_type_of_segment(mask_set),
                            error=get_error_from_segment(mask_set),
                            rate=get_rate_from_segment(mask_set),
                            videosegment=writer.filename)
                        new_mask_set.append(change)
    except Exception as e:
        logging.getLogger('maskgen').error(e)
    finally:
        reader_manager.close()
        writer_manager.close()
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
    reader_manager = tool_set.GrayBlockReaderManager()
    writer_manager = tool_set.GrayBlockWriterManager()
    try:
        for mask_set in video_masks:
            if get_type_of_segment(mask_set) != expectedType or \
                get_file_from_segment(mask_set) is None:
                new_mask_set.append(mask_set)
                continue
            change = create_segment(starttime=get_start_time_from_segment(mask_set),
                                    startframe=get_start_frame_from_segment(mask_set),
                                    endtime=get_end_time_from_segment(mask_set),
                                    endframe=get_end_frame_from_segment(mask_set),
                                    type=get_type_of_segment(mask_set),
                                    error=get_error_from_segment(mask_set),
                                    rate=get_rate_from_segment(mask_set),
                                    videosegment=get_file_from_segment(mask_set))
            mask_file_name = get_file_from_segment(mask_set)
            reader = reader_manager.create_reader(mask_file_name,
                                                  start_time=get_start_time_from_segment(mask_set),
                                                  start_frame=get_start_frame_from_segment(mask_set),
                                                  end_frame=get_end_frame_from_segment(mask_set))
            writer = writer_manager.create_writer(reader)
            try:
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
                update_segment(change, videosegment=writer.filename)
                new_mask_set.append(change)
            except Exception as e:
                logging.getLogger('maskgen').error('Failed to transform {} using {}'.format(get_file_from_segment(mask_set),
                                                                                            str(func)))
                logging.getLogger('maskgen').error(e)
    finally:
        reader_manager.close()
        writer_manager.close()
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
    writer_manager = tool_set.GrayBlockWriterManager()
    reader_manager = tool_set.GrayBlockReaderManager()
    try:
        for mask_set in video_masks:
            change = copy.copy(mask_set)
            if get_file_from_segment(mask_set) is not None:
                mask_file_name = get_file_from_segment(mask_set)
                reader = reader_manager.create_reader(mask_file_name,
                                                  start_frame=get_start_frame_from_segment(mask_set),
                                                  start_time=get_start_time_from_segment(mask_set),
                                                  end_frame=get_end_frame_from_segment(mask_set)
                                                  )
                writer = writer_manager.create_writer(reader)
                while True:
                    frame_time = reader.current_frame_time()
                    frame_count = reader.current_frame()
                    frame = reader.read()
                    if frame is not None:
                        # ony those pixels that are unchanged from the original
                        # TODO Handle orientation change
                        if frame.shape != mask.shape:
                            frame = cv2.resize(frame, (mask.shape[1],mask.shape[0]))
                        # frame  is black = NOT match, white = MATCH
                        # TO RESULTING IMAGE
                        # we want pixels in the MATCH REGION
                        # mask is white = is donated pixels (from images)
                        m = mask>0
                        # invert to black since video masks are inverted!
                        writer.write(255 - (m * frame), frame_time, frame_count)
                    else:
                        break
                update_segment(change,videosegment=writer.get_file_name())
            new_mask_set.append(change)
    finally:
        reader_manager.close()
        writer_manager.close()
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
    reader_manager = tool_set.GrayBlockReaderManager()
    for mask_set in video_masks:
        timeManager.updateToNow(get_end_time_from_segment(mask_set),get_end_frame_from_segment(mask_set)-frames)
        frames = get_end_frame_from_segment(mask_set)
        if timeManager.isPastStartTime():
            if get_file_from_segment(mask_set) is not None:
                timeManager = tool_set.VidTimeManager(extract_time_tuple)
                timeManager.updateToNow(get_start_time_from_segment(mask_set), get_start_frame_from_segment(mask_set))
                reader = reader_manager.create_reader(get_file_from_segment(mask_set),
                                              start_frame=get_start_frame_from_segment(mask_set),
                                              start_time=get_start_time_from_segment(mask_set))
                while True:
                    frame_time = reader.current_frame_time()
                    frame_count = reader.current_frame()
                    mask = reader.read()
                    if mask is None:
                        break
                    timeManager.updateToNow(frame_time,frame_count-timeManager.frameSinceBeginning + 1)
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
        # white = unchanged
        newRes = np.ones(size).astype('uint8')*255
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
         return cv2.resize(mask, (size[1],size[0]))
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
            if get_start_frame_from_segment(video_mask) <= frame_count and get_end_frame_from_segment(video_mask) > frame_count:
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

def intersectionOfMaskSets(setOne, setTwo):
    """
    from set two from set one
    :param setOne:
    :param setTwo:
    :return:
    @type setOne: list of dict
    @type setOne: list of dict
    """
    result = []
    for itemOne in setOne:
        for posTwo in range(len(setTwo)):
            itemTwo = setTwo[posTwo]
            if get_end_frame_from_segment(itemTwo) < get_start_frame_from_segment(itemOne) or \
                get_start_frame_from_segment(itemTwo) > get_end_frame_from_segment(itemOne) or \
                            get_type_of_segment(itemOne) != get_type_of_segment(itemTwo):
                continue
            diff_sf = get_start_frame_from_segment(itemTwo) - get_start_frame_from_segment(itemOne)
            diff_ef = get_end_frame_from_segment(itemTwo) - get_end_frame_from_segment(itemOne)
            start_frame = get_start_frame_from_segment(itemOne) if diff_sf < 0 else get_start_frame_from_segment(
                itemTwo)
            end_frame = get_end_frame_from_segment(itemTwo) if diff_ef < 0 else get_end_frame_from_segment(itemOne)
            start_time = get_start_time_from_segment(itemOne) if diff_sf < 0 else get_start_time_from_segment(itemTwo)
            end_time = get_end_time_from_segment(itemTwo) if diff_ef < 0 else get_end_time_from_segment(itemOne)
            result.append(create_segment(
                starttime=start_time,
                endtime=end_time,
                startframe=start_frame,
                endframe=end_frame,
                rate=get_rate_from_segment(itemOne),
                type=get_type_of_segment(itemTwo)))
    return sorted(result, key=lambda meta: get_start_frame_from_segment(meta))


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
            if get_end_frame_from_segment(itemTwo) < get_start_frame_from_segment(itemOne) or \
                get_start_frame_from_segment(itemTwo) > get_end_frame_from_segment(itemOne) or \
                            get_type_of_segment(itemOne) != get_type_of_segment(itemTwo):
                continue
            processedTwo.append(posTwo)
            diff_sf = get_start_frame_from_segment(itemTwo) - get_start_frame_from_segment(itemOne)
            diff_ef = get_end_frame_from_segment(itemTwo) - get_end_frame_from_segment(itemOne)
            if diff_sf < 0:
                result.append(create_segment(starttime=get_start_time_from_segment(itemTwo),
                                             endtime=get_start_time_from_segment(
                                                 itemOne) - 1000.0 / get_rate_from_segment(itemOne),
                                             startframe=get_start_frame_from_segment(itemTwo),
                                             endframe=get_start_frame_from_segment(itemOne) - 1,
                                             rate=get_rate_from_segment(itemOne),
                                             type=get_type_of_segment(itemTwo)))

            if diff_ef > 0:
                if get_start_frame_from_segment(itemTwo) > get_start_frame_from_segment(itemOne):
                    continue
                result.append(create_segment(
                    starttime=get_start_time_from_segment(itemOne) + 1000.0 / get_rate_from_segment(itemOne),
                    endtime=get_end_time_from_segment(itemTwo),
                    startframe=get_start_frame_from_segment(itemOne) + 1,
                    endframe=get_end_frame_from_segment(itemTwo),
                    rate=get_rate_from_segment(itemOne),
                    type=get_type_of_segment(itemTwo)
                ))
        for posTwo in range(len(nextrun)):
            if posTwo not in processedTwo:
                result.append(nextrun[posTwo])
        processedTwo = []
    result.extend(setOne)
    return sorted(result, key=lambda meta: get_start_frame_from_segment(meta))

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
        add_sf = get_start_frame_from_segment(bound,0)
        add_ef = get_end_frame_from_segment(bound,0)
        add_st = get_start_time_from_segment(bound,0)
        add_et = get_end_time_from_segment(bound,0)
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

        reader_manager = tool_set.GrayBlockReaderManager()
        writer_manager = tool_set.GrayBlockWriterManager()
        try:
            for mask_set in video_masks:
                if get_type_of_segment(mask_set) != expectedType:
                    new_mask_set.append(mask_set)
                    continue
                mask_sf = get_start_frame_from_segment(mask_set,1)
                mask_ef = get_end_frame_from_segment(mask_set,1)
                rate = get_rate_from_segment(mask_set)
                #before addition
                if add_sf - mask_ef > 0:
                    new_mask_set.append(mask_set)
                    continue
                start_diff_count= add_sf - mask_sf
                start_diff_time = add_st - get_start_time_from_segment(mask_set,0)
                end_adjust_count = add_ef - add_sf + 1
                end_adjust_time = add_et - add_st + 1000.0/rate
                if start_diff_count > 0:
                    change = create_segment(starttime=get_start_time_from_segment(mask_set),
                                            startframe=get_start_frame_from_segment(mask_set),
                                            endtime = get_start_time_from_segment(mask_set) + start_diff_time - 1000.0/get_rate_from_segment(mask_set),
                                            endframe=get_start_frame_from_segment(mask_set) + start_diff_count - 1,
                                            type= get_type_of_segment(mask_set),
                                            error= get_error_from_segment(mask_set),
                                            rate=rate)
                    amount_to_transfer=get_frames_from_segment(change)
                    if get_file_from_segment(mask_set) is not None:
                        reader = reader_manager.create_reader(get_file_from_segment(mask_set),
                                                  start_frame=get_start_frame_from_segment(mask_set),
                                                  start_time=get_start_time_from_segment(mask_set),
                                                  end_frame=get_end_frame_from_segment(mask_set))
                        writer = writer_manager.create_writer(reader)
                        transfer(reader, writer, 0, 0, amount_to_transfer)
                        update_segment(change,videosegment=writer.filename)
                    new_mask_set.append(change)
                    if end_adjust_count >= 0:
                        # split in the middle
                        change = create_segment(starttime=add_et + 1000.0/rate,
                                            startframe=add_ef + 1,
                                            endtime = get_end_time_from_segment(mask_set) + end_adjust_time,
                                            endframe= get_end_frame_from_segment(mask_set) + end_adjust_count,
                                            type= get_type_of_segment(mask_set),
                                            error= get_error_from_segment(mask_set),
                                            rate=rate)
                        if get_file_from_segment(mask_set) is not None:
                            # Already open from above
                            if reader is None:
                                reader = reader_manager.create_reader(get_file_from_segment(mask_set),
                                                                      start_frame=get_start_frame_from_segment(
                                                                          mask_set) + amount_to_transfer,
                                                                      start_time=get_start_time_from_segment(
                                                                          mask_set) + amount_to_transfer,
                                                                      end_frame=get_end_frame_from_segment(mask_set))
                            writer = writer_manager.create_writer(reader)
                            transfer(reader, writer, end_adjust_time, end_adjust_count, get_frames_from_segment(change))
                            update_segment(change, videosegment=writer.filename)
                        new_mask_set.append(change)
                elif end_adjust_count >= 0:
                    change = create_segment(starttime=get_start_time_from_segment(mask_set) +  end_adjust_time,
                                            startframe=get_start_frame_from_segment(mask_set) + end_adjust_count,
                                            endtime=get_end_time_from_segment(mask_set) + end_adjust_time,
                                            endframe=get_end_frame_from_segment(mask_set) + end_adjust_count,
                                            type=get_type_of_segment(mask_set),
                                            error=get_error_from_segment(mask_set),
                                            rate=rate)
                    if get_file_from_segment(mask_set) is not None:
                        reader = reader_manager.create_reader(mask_set['videosegment'],
                                                  start_frame=get_start_frame_from_segment(mask_set),
                                                  start_time=get_start_time_from_segment(mask_set),
                                                  end_frame=get_end_frame_from_segment(mask_set))
                        writer = writer_manager.create_writer(reader)
                        transfer(reader, writer, end_adjust_time, end_adjust_count, get_frames_from_segment(change))
                        update_segment(change, videosegment=writer.filename)
                    new_mask_set.append(change)
        finally:
            writer_manager.close()
            reader_manager.close()
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


def getSingleFrameFromMask(video_masks, directory=None):
    """
    Read a single frame
    :param start_time: insertion start time.
    :param end_time:insertion end time.
    :param directory:
    :param video_masks:
    :return: new set of video masks
    """
    mask = None
    if video_masks is None:
        return None
    for mask_set in video_masks:
        if get_file_from_segment(mask_set) is None:
            continue
        reader = tool_set.GrayBlockReader(os.path.join(directory,
                                                       get_file_from_segment(mask_set))
                                 if directory is not None else get_file_from_segment(mask_set),
                                 start_frame=get_start_frame_from_segment(mask_set,1),
                                 start_time=get_start_time_from_segment(mask_set,0))
        try:
            mask = reader.read()
        finally:
            reader.close()
        if mask is not None:
            break
    return ImageWrapper(mask) if mask is not None else None

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
