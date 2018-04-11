import numpy as np
import logging
from maskgen.cv2api import cv2api_delegate
import maskgen
from maskgen import video_tools

def createOutput(in_file, out_file):
    cap = cv2api_delegate.videoCapture(in_file)
    out_file = out_file
    fourcc = 0
    fps = cap.get(cv2api_delegate.prop_fps)
    height = int(np.rint(cap.get(cv2api_delegate.prop_frame_height)))
    width = int(np.rint(cap.get(cv2api_delegate.prop_frame_width)))
    out_video = cv2api_delegate.videoWriter(out_file, fourcc, fps, (width,height))
    if not out_video.isOpened():
        err = ("Error opening video" + in_file + " fourcc: " + str(fourcc) +" FPS: "+ str(fps)+
               " H: "+str(height)+" W: "+ str(width) )
        raise ValueError(err)
    return out_video, cap

def dropDupFrames(in_file,out_file, thresh):
    logger = logging.getLogger('maskgen')
    debug = logger.isEnabledFor(logging.DEBUG)
    out, cap =createOutput(in_file,out_file)
    more_frames, frame = cap.read()
    if not(more_frames):
        raise ValueError("Error Reading Frames From {}".format(in_file))
    past=np.mean(frame, axis=2)
    out.write(frame)
    more_frames, frame = cap.read()
    if debug:
        i=0
        j=0
    while (more_frames):
        if debug:
            i+=1
        future = np.mean(frame, axis=2)
        a=int(round(np.std((past - future))))
        if a>int(thresh):
            out.write(frame)
            if debug:
                logger.debug("Keeping Frame {} with difference of {}".format(i, a))
        elif debug:
            j+=1
            logger.debug('dropping frame {} with difference of {}'.format( i, a))
        past=future
        more_frames, frame = cap.read()
    if debug:
        logger.debug('Dropped a total of {} Frames'.format(j))
    cap.release()
    out.release()

def transform(img,source,target, **kwargs):
    dropDupFrames(source,target,kwargs['Threshold'] if 'Threshold' in kwargs else 3)
    return {'Start Time':1},None

def operation():
    return {'name':'DuplicateFrameDrop',
            'category':'PostProcessing',
            'description':'Remove any duplicate frames from a video with a certain threshold',
            'software':'maskgen',
            'version':maskgen.__version__[0:3],
            'arguments':{
                'Threshold':{
                    'type':'int[0:100]',
                    'defaultvalue':3,
                    'description':'Threshold to determine how alike the frames have to be lower threshold more alike'
                }
            },
            'transitions': [
                'video.video'
            ]
            }

def suffix():
    return '.avi'

