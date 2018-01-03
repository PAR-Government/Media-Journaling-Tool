from maskgen.tool_set import getMilliSecondsAndFrameCount
import cv2
from maskgen.algorithms.optical_flow import  smartSmoothFrames
from maskgen.tool_set import  getDurationStringFromMilliseconds

def transform(img,source,target,**kwargs):
    start_time = getMilliSecondsAndFrameCount(kwargs['Start Time']) if 'Start Time' in kwargs else (0,1)
    codec = (kwargs['codec']) if 'codec' in kwargs else 'XVID'
    add_frames, end_time_millis = smartSmoothFrames(source,
                                                  target,
                                              start_time,
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
