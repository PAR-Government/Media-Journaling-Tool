# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import cv2
from maskgen.algorithms.optical_flow import dropFrames
from maskgen.tool_set import getMilliSecondsAndFrameCount

"""
Returns the start and end time of the frames to drop and the number of frames droppped
"""


def transform(img, source, target, **kwargs):
    start_time = getMilliSecondsAndFrameCount(str(kwargs['Start Time'])) if 'Start Time' in kwargs else (0, 1)
    end_time = getMilliSecondsAndFrameCount(str(kwargs['End Time'])) if 'End Time' in kwargs else None
    codec = (kwargs['codec']) if 'codec' in kwargs else 'XVID'
    start, stop, frames_dropped = dropFrames(source,
                                             target,
                                             start_time,
                                             end_time,
                                             codec=codec)
    return {'Start Time': str(start),
            'End Time': str(stop),
            'Frames Dropped': frames_dropped}, None

def suffix():
    return '.avi'

# the actual link name to be used.
# the category to be shown
def operation():
  return {'name':'SelectCutFrames',
          'category':'Select',
          'description':'Drop Frames',
          'software':'OpenCV',
          'version':cv2.__version__,
          'arguments':  {
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
