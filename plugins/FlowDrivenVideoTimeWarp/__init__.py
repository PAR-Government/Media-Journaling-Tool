from maskgen.tool_set import getMilliSecondsAndFrameCount
import cv2
from maskgen.algorithms.optical_flow import  smartAddFrames
from maskgen.tool_set import  getDurationStringFromMilliseconds


"""
Returns the start and end time of the frames added
"""

def transform(img,source,target,**kwargs):
    start_time = getMilliSecondsAndFrameCount(kwargs['Start Time']) if 'Start Time' in kwargs else (0,1)
    end_time = getMilliSecondsAndFrameCount(kwargs['End Time']) if 'End Time' in kwargs else None
    frames_add = int(kwargs['Frames to Add']) if 'Frames to Add' in kwargs else None
    if frames_add is not None:
        end_time = (start_time[0],start_time[1] + frames_add - 1)
    codec = (kwargs['codec']) if 'codec' in kwargs else 'XVID'
    add_frames, end_time_millis = smartAddFrames(source, target,
                                              start_time,
                                              end_time,
                                              codec=codec,
                                              direction=kwargs['Direction'] if 'Direction' in kwargs else 'forward')


    if start_time[0] > 0:
        et = getDurationStringFromMilliseconds(end_time_millis)
    else:
        et = str(int(start_time[1]) + int(add_frames))

    return {'Start Time':str(kwargs['Start Time']), 'End Time': et, 'Frames to Add': int(add_frames)},None

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
              'Direction': {
                  'type': 'list',
                  'values':['forward','backward'],
                  'defaultvalue': 'forward',
                  'description': 'Direction of flow.'
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
