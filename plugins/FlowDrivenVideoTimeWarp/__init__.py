from maskgen.tool_set import getMilliSecondsAndFrameCount
import numpy as np
import cv2
import time
import logging
import os
from maskgen.cv2api import cv2api_delegate
from maskgen.tool_set import  VidTimeManager,differenceInFramesBetweenMillisecondsAndFrame,getDurationStringFromMilliseconds


class OpticalFlow:
    def __init__(self, prvs_frame, next_frame, flow):
        self.prvs_frame = prvs_frame
        self.next_frame = next_frame
        self.flow = flow
        self.hight = flow.shape[0]
        self.width = flow.shape[1]

    def setFrames(self, prvs_frame, next_frame, flow):
        self.prvs_frame = prvs_frame
        self.next_frame = next_frame
        self.flow = flow

    def warpFlow(self, img, flow):
        h, w = flow.shape[:2]
        flow = -flow
        flow[:, :, 0] += np.arange(w)
        flow[:, :, 1] += np.arange(h)[:, np.newaxis]
        res = cv2.remap(img, flow, None, cv2.INTER_LINEAR)
        return res

    def setTime(self, frame_time):
        forward_flow = np.multiply(self.flow, frame_time)
        backward_flow = np.multiply(self.flow, -(1 - frame_time))
        from_prev = self.warpFlow(self.prvs_frame, forward_flow)
        from_next = self.warpFlow(self.next_frame, backward_flow)
        from_prev = np.multiply(from_prev, (1 - frame_time))
        from_next = np.multiply(from_next, frame_time)
        frame = (np.add(from_prev, from_next)).astype(np.uint8)

        return frame

    # return the average sigma(optical flow)
def getNormalFlow(frames):
        flow_list = np.zeros(len(frames) - 1)
        future = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)
        for i in range(1, len(frames)):
            past = future
            future = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)
            flow = cv2.calcOpticalFlowFarneback(past, future, None,
                                                0.8, 7, 15, 3, 7, 1.5, 0)
            flow_list[i - 1] = np.std(flow)
        print flow_list
        return np.mean(flow_list)

def smartAddFrames(in_file,
                    out_file,
                    start_time,
                    end_time,
                    codec='MPEG'):
    """
    :param in_file: is the full path of the video file from which to drop frames
    :param out_file: resulting video file
    :param start_time: (milli,frame no) to start to fill
    :param end_time: (milli,frame no) end fil
    :param codec:
    :return:
    """
    cap = cv2api_delegate.videoCapture(in_file)
    fourcc = cv2api_delegate.fourcc(codec)
    fps = cap.get(cv2api_delegate.prop_fps)
    height = int(np.rint(cap.get(cv2api_delegate.prop_frame_height)))
    width = int(np.rint(cap.get(cv2api_delegate.prop_frame_width)))
    out_video = cv2.VideoWriter(out_file, fourcc, fps, (width, height))
    time_manager = VidTimeManager(startTimeandFrame=start_time, stopTimeandFrame=end_time)
    frames_to_add =differenceInFramesBetweenMillisecondsAndFrame(end_time,start_time,fps)-1
    if not out_video.isOpened():
        err = out_video + " fourcc: " + str(fourcc) + " FPS: " + str(fps) + \
              " H: " + str(height) + " W: " + str(width)
        raise ValueError('Unable to create video ' + err)
    try:
        last_frame = None
        while (cap.grab()):
            ret, frame = cap.retrieve()
            elapsed_time = float(cap.get(cv2api_delegate.prop_pos_msec))
            time_manager.updateToNow(elapsed_time)
            if not time_manager.isBeforeTime():
                break
            out_video.write(frame)
            last_frame  = frame
        next_frame= frame
        prev_frame_gray = cv2.cvtColor(last_frame, cv2.COLOR_BGR2GRAY)
        next_frame_gray = cv2.cvtColor(next_frame, cv2.COLOR_BGR2GRAY)
        jump_flow = cv2.calcOpticalFlowFarneback(prev_frame_gray, next_frame_gray, None,
                                                     0.8, 7, 15, 3, 7, 1.5, 2)

        opticalFlow = OpticalFlow(last_frame, next_frame, jump_flow)
        i =0
        while i<frames_to_add:
            frame_scale = i / (1.0 * frames_to_add)
            frame = opticalFlow.setTime(frame_scale)
            out_video.write(frame)
            i+=1
        out_video.write(next_frame)
        while (cap.grab()):
            ret, frame = cap.retrieve()
            out_video.write(frame)

    finally:
        cap.release()
        out_video.release()
    return frames_to_add,frames_to_add*(1000.0/fps)


def transform(img,source,target,**kwargs):
    start_time = getMilliSecondsAndFrameCount(kwargs['Start Time']) if 'Start Time' in kwargs else (0,1)
    end_time = getMilliSecondsAndFrameCount(kwargs['End Time']) if 'End Time' in kwargs else None
    frames_add = int(kwargs['Frames to Add']) if 'Frames to Add' in kwargs else None
    if frames_add is not None:
        end_time = (start_time[0],start_time[1] + frames_add+1)
    codec = (kwargs['codec']) if 'codec' in kwargs else 'XVID'
    add_frames, end_time_millis = smartAddFrames(source, target,
                                              start_time,
                                              end_time,
                                              codec=codec)


    if start_time[0] > 0:
        et = getDurationStringFromMilliseconds(end_time_millis)
    else:
        et = str(int(start_time[1]) + int(add_frames)+1)

    return {'Start Time':str(kwargs['Start Time']), 'End Time': et},None

def suffix():
    return '.avi'


def operation():
  return {'name':'TimeAlterationWarp',
          'category':'TimeAlteration',
          'description':'Insert frames using optical flow given a starting point and desired end time.',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments':  {
              'Frames to Add': {
                  'type': 'int[0:100000000]',
                  'defaultvalue': 1,
                  'description':'Number of frames since Start Time. overrides or in lieu of an End Time.'
              },
              'codec': {
                  'type': 'list',
                  'values': ['MPEG','XVID','AVC1','HFYU'],
                  'defaultvalue': 'XVID',
                  'description': 'Codec of output video.'
              }
          },
          'transitions': [
              'video.video'
          ]
          }
