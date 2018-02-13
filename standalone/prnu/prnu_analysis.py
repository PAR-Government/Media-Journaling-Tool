"""
Plugin for the journaling tool removes PNU from every from of the video
@author Mike Hurlbutt
"""

import sys
import subprocess
import os

import numpy as np
import cv2
from maskgen.cv2api import cv2api_delegate
from maskgen.plugins import findPlugin

def transform(img, source, target, **kwargs):
    """
    i = intensity of a pixel in source
    p = PRNU value
    io = original pixel intensity (io + p = i)
    n = corresponding pixel value from PNG noise image
    :param img:
    :param source:
    :param target:
    :param kwargs:
    :return:
    """
    codec = (kwargs['codec']) if 'codec' in kwargs else 'RAW'

    sourceImg = averageFrame(source)

    if sys.platform.startswith('win'):
        subprocess.call([os.path.join(findPlugin('PRNURemoveFromVid'), 'ExtractNoise.exe'), sourceImg])
    else:
        subprocess.call([os.path.join(findPlugin('PRNURemoveFromVid'), 'ExtractImageNoise'), sourceImg])
    ext = os.path.splitext(sourceImg)[1]
    trace = sourceImg.replace(ext, '_noise.png')
    cap = cv2api_delegate.videoCapture(source)
    width = int(cap.get(cv2api_delegate.prop_frame_width))
    height = int(cap.get(cv2api_delegate.prop_frame_height))
    fourcc = cv2api_delegate.get_fourcc(codec) if codec != 'RAW' else 0
    rit = cv2.VideoWriter(target, fourcc, (cap.get(cv2api_delegate.prop_fps)), (width, height), int(1))
    try:
        im_trace = cv2.imread(trace).astype('float64')
        while True:
            more, im = cap.read()
            if not more:
                break
            im_source = im.astype('float64')
            io_im = np.round(np.multiply(im_source*255, 1.0/(im_trace+127)))
            io_im_trunc = np.clip(io_im, 0.0, 255.0).astype('uint8')
            rit.write(io_im_trunc)
    finally:
        cap.release()
        rit.release()
        os.remove(trace)
    return None, None

"""
Acquire every frame depending on the number of desired frames
and the gap between selections and the capture
"""
def getFrameList(videoCapture, gap, frames):
    f = None
    count = 0.0
    while count < frames:
        for x in range(0, gap):
            t = videoCapture.grab()  # only decode necessary frames
            if not t:
                break
        more_frames, frame = videoCapture.retrieve()
        if not more_frames:
            break
        if count == 0:
            f = np.array(frame).astype('float64')
        else:
            f += np.array(frame).astype('float64')
        count += 1
    return (f / (count))


"""
Calculates average image from 3600 evenly distributed frames of a video
or if less than 3600 then all frames are used
"""
def averageFrame(donor):
    frames = 100.0
    cap = cv2api_delegate.videoCapture(donor)
    try:
        total = cap.get(cv2api_delegate.prop_frame_count)
        if total == 0:
            raise ValueError("Video Could not be Accessed")
        if frames > total:
            frames = total
        gap = int(total / frames)
        f = getFrameList(cap, gap, frames)
        ext = os.path.splitext(donor)[1]
        trace = donor.replace(ext, '_avg.png')
        cv2.imwrite(trace, f)
        return trace
    finally:
        cap.release()


def operation():
    return {'name':'RemoveCamFingerprintPRNU',
            'category':'AntiForensic',
            'description':'Remove the estimated PRNU from a Video.',
            'software':'OpenCV',
            'version':cv2.__version__,
            'arguments':{
                'codec': {
                    'type': 'list',
                    'values': ['MPEG', 'XVID', 'AVC1', 'RAW'],
                    'defaultvalue': 'RAW',
                    'description': 'Codec of output video.'
                }
            },
            'transitions':[
                'video.video'
                ]
            }

def suffix():
    return '.avi'
