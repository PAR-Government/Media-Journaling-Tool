# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from maskgen.tool_set import getMilliSecondsAndFrameCount, addFrame
import cv2
from maskgen.algorithms.optical_flow import copyFrames

"""
Returns the start and end time of the frames inserted
"""



def transform(img, source, target, **kwargs):
    start_time = getMilliSecondsAndFrameCount(kwargs['Select Start Time']) if 'Select Start Time' in kwargs else (0, 1)
    end_time = addFrame(start_time, int(kwargs['Number of Frames'])-1)
    paste_time = getMilliSecondsAndFrameCount(kwargs['Dest Paste Time'])
    codec = (kwargs['codec']) if 'codec' in kwargs else 'XVID'
    start_frame = copyFrames(source, target,
                             start_time,
                             end_time,
                             paste_time,
                             codec=codec) + 1
    return {'Start Time': str(start_frame),
            'End Time': str(start_frame + int(kwargs['Number of Frames']) - 1),
            'add type': 'insert'}, None


def suffix():
    return '.avi'


def operation():
    return {'name': 'CopyPaste',
            'category': 'CopyPaste',
            'description': 'Copy frames starting point to a destination point.',
            'software': 'OpenCV',
            'version': cv2.__version__,
            'arguments': {
                'codec': {
                    'type': 'list',
                    'values': ['MPEG', 'XVID', 'AVC1', 'HFYU'],
                    'defaultvalue': 'XVID',
                    'description': 'Codec of output video.'
                }
            },
            'transitions': [
                'video.video'
            ]
            }
