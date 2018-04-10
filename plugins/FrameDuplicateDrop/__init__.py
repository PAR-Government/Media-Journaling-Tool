import numpy as np
import cv2
from maskgen.cv2api import cv2api_delegate
from maskgen import cv2api
import matplotlib.pyplot as plt
import maskgen
from maskgen import video_tools

def createOutput(in_file, out_file):
    cap = cv2api_delegate.videoCapture(in_file)
    out_file = out_file
#    fourcc=cv2.VideoWriter_fourcc(*'HFYU') # Huffman Lossless Codec (HFYU)
#    fourcc=cv2.VideoWriter_fourcc(*'MP4V')
    fourcc = 0
    fps    = cap.get(cv2api_delegate.prop_fps)
    height = int(np.rint(cap.get(cv2api_delegate.prop_frame_height)))
    width  = int(np.rint(cap.get(cv2api_delegate.prop_frame_width)))
    out_video = cv2api_delegate.videoWriter(out_file, fourcc, fps, (width,height))
    if not out_video.isOpened():
        print "Error opening output"
        err = (out_video + " fourcc: " + str(fourcc) +" FPS: "+ str(fps)+
               " H: "+str(height)+" W: "+ str(width) )
        raise ValueError(err)
    cap.release()
    return out_video

def dropDupFrames(in_file,out_file, thresh):
    out=createOutput(in_file,out_file)
    cap = cv2api_delegate.videoCapture(in_file)
    more_frames, frame = cap.read()
    if not(more_frames):
        print "Error reading input"
        raise ValueError(in_file)
    past=np.mean(frame, axis=2)
    more_frames, frame = cap.read()
    i=0
    j=0
    out.write(frame)
    hist = np.zeros(256)
    while (more_frames):
        i+=1
        future = np.mean(frame, axis=2)
        a=int(round(np.std((past - future))))
        hist[a]+=1
        if a>int(thresh):
            out.write(frame)
#            print i, a
        else:
            j+=1
            print 'dropping frame', i, a
        past=future
        more_frames, frame = cap.read()

    #plt.bar(range(256), hist)
    #plt.show()
    out.release()

def transform(img,source,target, **kwargs):
    dropDupFrames(source,target,kwargs['Threshold'] if 'Threshold' in kwargs else 3)
    return None,None

def operation():
    return {'name':'DuplicateFrameDrop',
            'category':'PostProcessing',
            'description':'Remove any duplicate frames from a video with a certain threshold',
            'software':'ffmpeg',
            'version':maskgen.video_tools.get_ffmpeg_version(),
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

