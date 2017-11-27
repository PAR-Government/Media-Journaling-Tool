from maskgen.tool_set import getMilliSecondsAndFrameCount
import numpy as np
import cv2
import time
import logging
import os
from maskgen.cv2api import cv2api_delegate
from maskgen.tool_set import  VidTimeManager

def readFrames(in_file, start_time, end_time):
    """
     Function to read in video frames and store them in an array for later use.
     This limits the size of the video to just few minutes at most.
     Build a concatenated histogram of the GBR of each frame.
    :param in_file:
    :param offset_seconds: number of seconds to start search
    :return:
    @type offset_seconds: float
    """
    if not os.path.exists(in_file):
        raise ValueError(in_file + ' not found')
    cap = cv2api_delegate.videoCapture(in_file)
    frames = list()
    histograms = list()
    fps = 0.0
    startFrame = 0
    time_manager = VidTimeManager(startTimeandFrame=start_time, stopTimeandFrame=end_time)
    try:
        while (cap.grab()):
            fps = cap.get(cv2api_delegate.prop_fps)
            elapsed_time = float(cap.get(cv2api_delegate.prop_pos_msec))
            ts = elapsed_time / 1000.0
            time_manager.updateToNow(elapsed_time)
            if not time_manager.isBeforeTime() and not time_manager.isPastTime():
                ret, frame = cap.retrieve()
                frames.append(frame)
                hist = np.asarray(np.histogram(frame[:, :, 0], 256, (0, 255)))[0]
                hist = np.append(hist, np.asarray(np.histogram(frame[:, :, 1], 256, (0, 255)))[0])
                hist = np.append(hist, np.asarray(np.histogram(frame[:, :, 2], 256, (0, 255)))[0])
                histograms.append(hist)
            else:
                startFrame += 1
            if time_manager.isPastTime():
                break
    finally:
        cap.release()
    if len(frames) == 0:
        raise ValueError(in_file + ' unreadable')
    return [frames, histograms, fps, startFrame]


def createOutput(in_file, out_file, start, stop, codec='MPEG'):
    cap = cv2api_delegate.videoCapture(in_file)
    fourcc = cv2api_delegate.fourcc(codec)
    fps = cap.get(cv2api_delegate.prop_fps)
    height = int(np.rint(cap.get(cv2api_delegate.prop_frame_height)))
    width = int(np.rint(cap.get(cv2api_delegate.prop_frame_width)))
    out_video = cv2.VideoWriter(out_file, fourcc, fps, (width, height))
    if not out_video.isOpened():
        err = out_video + " fourcc: " + str(fourcc) + " FPS: " + str(fps) + \
              " H: " + str(height) + " W: " + str(width)
        raise ValueError('Unable to create video ' + err)
    try:
        count = 0
        while (cap.grab()):
            ret, frame = cap.retrieve()
            count += 1
            if count >= start and count <= stop:
                continue
            out_video.write(frame)
    finally:
        cap.release()
        out_video.release()


def scanHistList(histograms, distance, offset, saveHistFile=None):
    """
        Function to compare frame image histograms and produce an array of the
        standard deviation of the differences.
    :param histograms:  an array of concatenated GBR histograms
    :param distance:  minimum number of frames apart to start the comparison
    :param offset:  Number of frames to skip at the start of the list
    :return: Nx4 matrix where each column in start,end,length and std_flow.
    """
    import math
    history = np.zeros(((len(histograms) - (offset + distance)) * (len(histograms) - (offset + distance) +1 )//2,
                        4), np.int)
    h_count = 0
    # front frame to compare. skip the first 30
    for i in range(offset, len(histograms) - distance):
        for j in range(i + distance, len(histograms)):
            std_flow = np.std(histograms[i] - histograms[j])
            history[h_count, :] = [i, j, j - i, std_flow]
            h_count += 1

    if saveHistFile is not None:
        np.savetxt(saveHistFile, history, delimiter=",", fmt='%2.3f')
    return history


def computeNormalDiffs(histograms, num_frames, logger=None):
    """
    Return the average and standard deviation for the first number of frame
    histogram differences
    :param histograms:
    :param num_frames:
    :return:
    """
    flow_list = np.zeros(num_frames)
    for i in range(1, num_frames):
        flow_list[i] = np.std(histograms[i] - histograms[i + 1])

    avg_flow = np.mean(flow_list)
    sigma_flow = np.std(flow_list)
    if logger is not None:
        logger.debug("mean flow {} with {} sigma".format(avg_flow, sigma_flow))
    return [avg_flow, sigma_flow]

def selectBestMatches(differences, selection=10):
    """
     return the 'selection' best results. Needs to be updated to try to find the longest
     rop that should work
    :param differences: histogram difference matrix
    :param selection: how manny to return
    :return: selectionX4 matrix of the best (least different)
    """
    sort = differences[:, 3].argsort(axis=None)
    return differences[sort[:selection]]


# best flow defined as the lowest sigam of the optical flow between frames
def selectBestFlow(frames, best_matches):
    flow_list = np.zeros(best_matches.shape[0])
    for i in range(best_matches.shape[0]):
        past = cv2.cvtColor(frames[best_matches[i, 0]], cv2.COLOR_BGR2GRAY)
        future = cv2.cvtColor(frames[best_matches[i, 1]], cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(past, future, None,
                                            0.8, 7, 15, 3, 7, 1.5, 0)
        flow_list[i] = np.std(flow)

    return np.argmin(flow_list)

def getNormalFlow (frames):
    flow_list=np.zeros(len(frames)-1)
    future = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
    for i in range(1, len(frames)):
        past = future
        future = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(past,future, None,
                                            0.8, 7,  15, 3, 7, 1.5, 0)
        flow_list[i-1]=np.std(flow)
    return np.mean(flow_list)

def calculateOptimalFrameReplacement(frames,start,stop):
    avg_flow = getNormalFlow(frames[start:stop])
    prev_frame = cv2.cvtColor(frames[start], cv2.COLOR_BGR2GRAY)
    next_frame = cv2.cvtColor(frames[stop], cv2.COLOR_BGR2GRAY)
    jump_flow = cv2.calcOpticalFlowFarneback(prev_frame, next_frame, None,
                                             0.8, 7, 15, 3, 7, 1.5, 2)

    std_jump_flow = np.std(jump_flow)
    frames_to_add = int(np.rint(std_jump_flow / avg_flow))
    #print "jump, avg, frames:", std_jump_flow, avg_flow, frames_to_add
    return frames_to_add

def smartDropFrames(in_file, out_file,
                    start_time,
                    end_time,
                    seconds_to_drop, savehistograms=False, codec='MPEG'):
    """
    :param in_file: is the full path of the video file from which to drop frames
    :param out_file: resulting video file
    :param start_time: (milli,frame no) for search space
    :param end_time: (milli,frame no) for search space
    :param seconds_to_drop:
    :param savehistograms: save histograms differences to file
    :param codec:
    :return:
    """
    logger = logging.getLogger('maskgen')
    logger.info('Read {} frames into memory'.format(in_file))
    frames, histograms, fps, start = readFrames(in_file, start_time, end_time)
    distance = int(round(fps * seconds_to_drop))
    #avg_diffs, sigma_diffs = computeNormalDiffs(histograms, 60)
    logger.info('starting histogram computational')
    differences = scanHistList(histograms, distance, 0,
                               saveHistFile=in_file[0:in_file.rfind('.')] + '-hist.csv' if savehistograms else None)
    logger.info('Finding best matches')
    best_matches = selectBestMatches(differences, selection=10)
    logger.info('Starting optical flow search')
    if best_matches is not None:
        best_flow = selectBestFlow(frames, best_matches)
        logger.info('best pair: {}'.format(str(best_matches[best_flow])))
        frames_to_add = calculateOptimalFrameReplacement(frames,best_matches[best_flow][0],
                     best_matches[best_flow][1])
        # add 2: one to advance to frame no and one to advance to first dropped frame
        firstFrametoDrop = best_matches[best_flow][0]+start+2
        lastFrametoDrop= best_matches[best_flow][1]+start
        createOutput(in_file, out_file, firstFrametoDrop,
                     lastFrametoDrop, codec=codec)
        return firstFrametoDrop, lastFrametoDrop+1,frames_to_add

def transform(img,source,target,**kwargs):
    start_time = getMilliSecondsAndFrameCount(str(kwargs['Start Time'])) if 'Start Time' in kwargs else (0,1)
    end_time = getMilliSecondsAndFrameCount(str(kwargs['End Time'])) if 'End Time' in kwargs else None
    seconds_to_drop = float(kwargs['seconds to drop']) if 'seconds to drop' in kwargs else 1.0
    save_histograms = (kwargs['save histograms'] == 'yes') if 'save histograms' in kwargs else False
    codec = (kwargs['codec']) if 'codec' in kwargs else 'XVID'
    start,stop,frames_to_add = smartDropFrames(source, target,
                                              start_time,
                                              end_time,
                                              seconds_to_drop,
                                              savehistograms=save_histograms,
                                              codec=codec)

    return {'Start Time': str(start),
            'End Time': str(stop),
            'Frames to Add':frames_to_add},None

def suffix():
    return '.avi'

# the actual link name to be used.
# the category to be shown
def operation():
  return {'name':'SelectCutFrames',
          'category':'Select',
          'description':'Drop desired number of frames with least variation in optical flow',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments':  {
              'seconds to drop': {
                  'type': 'float[0:100000000.0]',
                  'defaultvalue': 1.0,
                  'description':'Desired number of seconds to drop.'
              },
              'save histograms': {
                  'type': 'yesno',
                  'defaultvalue': 'no',
                  'description': 'Place frame histograms differences to in a CSV file.'
              },
              'codec': {
                  'type': 'list',
                  'values': ['MPEG','XVID','AVC1'],
                  'defaultvalue': 'XVID',
                  'description': 'Codec of output video.'
              }
          },
          'transitions': [
              'video.video'
          ]
          }
