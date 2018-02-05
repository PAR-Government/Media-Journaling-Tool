from maskgen.tool_set import getMilliSecondsAndFrameCount
import numpy as np
import cv2
from maskgen.algorithms.optical_flow import smartDropFrames

"""
Returns the start and end time of the frames to drop and the optimal number of frames to replace the dropped frames
"""

def transform(img,source,target,**kwargs):
    start_time = getMilliSecondsAndFrameCount(str(kwargs['Start Time'])) if 'Start Time' in kwargs else (0,1)
    end_time = getMilliSecondsAndFrameCount(str(kwargs['End Time'])) if 'End Time' in kwargs else None
    seconds_to_drop = float(kwargs['seconds to drop']) if 'seconds to drop' in kwargs else 1.0
    save_histograms = (kwargs['save histograms'] == 'yes') if 'save histograms' in kwargs else False
    drop = (kwargs['drop'] == 'yes') if 'drop at start time' in kwargs else True
    codec = (kwargs['codec']) if 'codec' in kwargs else 'XVID'
    start,stop,frames_to_add = smartDropFrames(source, target,
                                              start_time,
                                              end_time,
                                              seconds_to_drop,
                                              savehistograms=save_histograms,
                                              codec=codec,
                      drop = drop)
    #start = 1235
    #stop = 1245
    #frames_to_add=7
    return {'Start Time': str(start),
            'End Time': str(stop),
            'Frames Dropped' : stop-start + 1,
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
              },
              'drop ': {
                  'type': 'yesno',
                  'defaultvalue': 'yes',
                  'description': 'If yes, then do not search for optimal drop, use the start and times precisely'
              }
          },
          'transitions': [
              'video.video'
          ]
          }
