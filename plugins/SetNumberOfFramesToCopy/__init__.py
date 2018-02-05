# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

from maskgen.tool_set import getMilliSecondsAndFrameCount
import cv2


"""
A useful tool for batch processing to augment copy paste parameters, augmenting the copy start time the copy end time.
"""

def transform(img,source,target,**kwargs):
    end_time = getMilliSecondsAndFrameCount(kwargs['Select Start Time']) if 'Select Start Time' in kwargs else (0, 1)
    return {'Select Start Time':str(end_time[1]- int(kwargs['Number of Frames'])),
            'Number of Frames': kwargs['Number of Frames'],
            'Dest Paste Time':kwargs['Dest Paste Time']},None


def suffix():
    return '.avi'

def operation():
    return {'name': 'CopyPaste',
            'category': 'CopyPaste',
            'type': 'selector',
            'description': 'Set the start time for copy to the number frames prior to the given start point, making the the given start point the end point.',
            'software': 'OpenCV',
            'version': cv2.__version__,
            'arguments': {
            },
            'transitions': [
                'video.video'
            ]
            }
