# =============================================================================
# Authors: PAR Government
# Organization: DARPA
#
# Copyright (c) 2016 PAR Government
# All rights reserved.
# ==============================================================================

import shutil
import os
import maskgen

"""
Convenience plugin to combine donation and splice connecting in one operation.
"""


def transform(img, source, target, **kwargs):
    if 'Final Media' in kwargs:
        shutil.copy(kwargs['Final Media'], target)
        mask_set = maskgen.video_tools.getMaskSetForEntireVideo(kwargs['donor'],media_types=['audio'])
        return {'rename_target': os.path.split(kwargs['Final Media'])[1],
                'startframe':mask_set[0]['startframe'],
                'endframe':mask_set[0]['endframe']}, None
    else:
        return None, None

def operation():
    return {'name': 'AddAudioSample',
            'category': 'Audio',
            'software': 'maskgen',
            'version': maskgen.__version__[0:3],
            'arguments': {
                'donor': {
                    "type": "donor",
                    "description": "Image to paste."
                },
                'Final Media': {
                    "type": "file:image",
                    "description": "Final Result of the manipulation."
                }
            },
            'description': 'Audio Add Sample Convenience Filter to combine paste splice and donation connections in one step.',
            'transitions': [
                'video.audio',
                'audio.audio'
            ]
            }


def suffix():
    return None
